"""Scheduler: no send when policy blocks; promise dates drive reminded/escalated."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from backend.engine.policy import PolicyDecision
from backend.engine.scheduler import next_action_at
from backend.engine.states import InvoiceState


@dataclass
class Inv:
    invoice_id: str
    state: InvoiceState
    opted_out: bool
    due_date: date | None


NOW = datetime(2026, 8, 21, tzinfo=UTC)


def test_terminal_has_no_next_action() -> None:
    """Recovered invoices are not scheduled."""
    nxt = next_action_at(
        Inv("INV-1", InvoiceState.RECOVERED, False, date(2026, 8, 1)),
        [],
        as_of=NOW,
    )
    assert nxt is None


def test_blocked_opt_out_not_scheduled_for_nudge() -> None:
    """Opt-out uses a routing action (now) then terminates — not a nudge slot."""
    nxt = next_action_at(
        Inv("INV-1", InvoiceState.OPTED_OUT, True, date(2026, 8, 1)),
        [],
        as_of=NOW,
    )
    assert nxt == NOW


def test_overdue_schedules_immediately_when_allowed() -> None:
    """Overdue + allowed policy → act now."""
    nxt = next_action_at(
        Inv("INV-1", InvoiceState.OVERDUE, False, date(2026, 8, 1)),
        [],
        as_of=NOW,
        policy=PolicyDecision.allow(reason="ok", contacts_this_week=0),
    )
    assert nxt == NOW


def test_human_review_is_a_sink() -> None:
    """Agent does not schedule further nudges from HUMAN_REVIEW."""
    nxt = next_action_at(
        Inv("INV-1", InvoiceState.HUMAN_REVIEW, False, date(2026, 8, 1)),
        [],
        as_of=NOW,
    )
    assert nxt is None
