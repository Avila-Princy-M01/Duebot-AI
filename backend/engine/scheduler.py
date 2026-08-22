"""When the next agent action is due.

Never schedules a send if ``can_contact`` is blocked. Timing is
deterministic — not LLM-chosen. See ARCHITECTURE.md §6.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol

from backend.engine.policy import PolicyDecision, can_contact
from backend.engine.states import TERMINAL_STATES, InvoiceState

__all__ = [
    "NUDGE_INTERVAL_DAYS",
    "PROMISE_BREAK_GRACE_DAYS",
    "HasScheduleInvoice",
    "HasScheduleTouch",
    "next_action_at",
]


NUDGE_INTERVAL_DAYS = 3
PROMISE_BREAK_GRACE_DAYS = 3


class HasScheduleInvoice(Protocol):
    """Invoice fields the scheduler reads."""

    invoice_id: str
    state: InvoiceState
    opted_out: bool
    due_date: date | None


class HasScheduleTouch(Protocol):
    """Last outbound contact timestamp."""

    direction: str
    sent_at: datetime


def next_action_at(
    invoice: HasScheduleInvoice,
    history: Sequence[HasScheduleTouch],
    *,
    as_of: datetime,
    policy: PolicyDecision | None = None,
    promised_date: datetime | None = None,
) -> datetime | None:
    """Return the next time DueBot should act, or None if it should not.

    Args:
        invoice: Current invoice.
        history: Interaction history (outbound contacts).
        as_of: Clock.
        policy: Optional precomputed ``can_contact`` result. If omitted,
            this function calls ``can_contact`` itself (except for
            non-contact actions such as aging or promise-date checks).
        promised_date: Active promise date when state is PROMISED/REMINDED.

    Returns:
        A timezone-aware datetime, or None if no agent action is scheduled.
    """
    state = invoice.state
    if state in TERMINAL_STATES:
        return None

    if state is InvoiceState.CREATED:
        if invoice.due_date is None:
            return None
        due_dt = datetime.combine(invoice.due_date, time.min, tzinfo=UTC)
        return due_dt if due_dt > as_of else as_of

    if state is InvoiceState.HUMAN_REVIEW:
        return None
    if state is InvoiceState.DISPUTED:
        return as_of
    if state is InvoiceState.ESCALATED:
        return as_of
    if state is InvoiceState.OPTED_OUT:
        return as_of

    if state is InvoiceState.PROMISED:
        if promised_date is None:
            return None
        return promised_date

    if state is InvoiceState.REMINDED:
        if promised_date is None:
            return as_of
        return promised_date + timedelta(days=PROMISE_BREAK_GRACE_DAYS)

    decision = policy if policy is not None else can_contact(invoice, history, as_of=as_of)
    if not decision.allowed:
        if decision.contacts_this_week >= 0 and "contact cap" in decision.reason:
            return as_of
        return None

    if state in (InvoiceState.OVERDUE,):
        return as_of

    last_outbound = _last_outbound(history)
    if state in (InvoiceState.NUDGED, InvoiceState.REPLIED) or last_outbound is not None:
        if last_outbound is None:
            return as_of
        return last_outbound + timedelta(days=NUDGE_INTERVAL_DAYS)

    return as_of


def _last_outbound(history: Sequence[HasScheduleTouch]) -> datetime | None:
    outbound = [item.sent_at for item in history if item.direction == "outbound"]
    if not outbound:
        return None
    return max(outbound)
