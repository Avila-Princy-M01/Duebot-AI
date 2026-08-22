"""Hard safety invariants for outbound contact.

``can_contact`` returns a ``PolicyDecision`` object, not a boolean, so
``integrations.whatsapp.send`` cannot be called without going through policy.
See ARCHITECTURE.md §6 and §10.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from backend.engine.states import InvoiceState, TransitionEvent

__all__ = [
    "MAX_CONTACTS_PER_WEEK",
    "CONTACT_WINDOW_DAYS",
    "CONFIDENCE_THRESHOLD",
    "CONTACT_CAP_WARNING_REMAINING",
    "ReplyIntent",
    "PolicyDecision",
    "HasPolicyInvoice",
    "HasOutboundTouch",
    "can_contact",
    "count_outbound_in_window",
    "intent_needs_human",
    "event_for_parsed_intent",
]


MAX_CONTACTS_PER_WEEK = 3
CONTACT_WINDOW_DAYS = 7
CONFIDENCE_THRESHOLD = 0.7
CONTACT_CAP_WARNING_REMAINING = 1


class ReplyIntent(StrEnum):
    """Structured intents produced by ``llm.reply_parser`` (function-calling)."""

    PROMISE = "promise"
    AMBIGUOUS = "ambiguous"
    DISPUTE = "dispute"
    OPT_OUT = "opt_out"
    OBJECTION = "objection"


class HasPolicyInvoice(Protocol):
    """Invoice fields policy needs — not the SQLAlchemy model."""

    invoice_id: str
    state: InvoiceState
    opted_out: bool


class HasOutboundTouch(Protocol):
    """An interaction row policy can count as a contact."""

    direction: str
    sent_at: datetime


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Outcome of ``can_contact``. Pass this into WhatsApp ``send()``."""

    allowed: bool
    reason: str
    contacts_this_week: int
    approaching_cap: bool = False

    @classmethod
    def allow(
        cls,
        *,
        reason: str,
        contacts_this_week: int,
        approaching_cap: bool = False,
    ) -> PolicyDecision:
        """Build an allowed decision."""
        return cls(
            allowed=True,
            reason=reason,
            contacts_this_week=contacts_this_week,
            approaching_cap=approaching_cap,
        )

    @classmethod
    def blocked(cls, reason: str, *, contacts_this_week: int = 0) -> PolicyDecision:
        """Build a blocked decision."""
        return cls(
            allowed=False,
            reason=reason,
            contacts_this_week=contacts_this_week,
            approaching_cap=False,
        )


def count_outbound_in_window(
    history: Sequence[HasOutboundTouch],
    *,
    as_of: datetime,
    window_days: int = CONTACT_WINDOW_DAYS,
) -> int:
    """Count outbound contacts in the trailing window."""
    cutoff = as_of - timedelta(days=window_days)

    def _to_utc(dt_val: datetime) -> datetime:
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=UTC)
        return dt_val.astimezone(UTC)

    utc_cutoff = _to_utc(cutoff)
    return sum(
        1
        for item in history
        if item.direction == "outbound" and _to_utc(item.sent_at) >= utc_cutoff
    )


def can_contact(
    invoice: HasPolicyInvoice,
    history: Sequence[HasOutboundTouch],
    *,
    as_of: datetime,
    max_contacts: int = MAX_CONTACTS_PER_WEEK,
) -> PolicyDecision:
    """Decide whether DueBot may send another outbound message.

    Args:
        invoice: Current invoice (state + opt-out flag).
        history: Prior interactions (outbound rows count as contacts).
        as_of: Clock used for the trailing window (injectable for tests).
        max_contacts: Cap, default ``MAX_CONTACTS_PER_WEEK``.

    Returns:
        A ``PolicyDecision``. Callers must not send if ``allowed`` is False.
    """
    if invoice.opted_out:
        return PolicyDecision.blocked("buyer opted out — irreversible")
    if invoice.state is InvoiceState.DISPUTED:
        return PolicyDecision.blocked("disputed invoices are never nudged")
    if invoice.state is InvoiceState.OPTED_OUT:
        return PolicyDecision.blocked("buyer opted out — irreversible")
    if invoice.state in (InvoiceState.RECOVERED, InvoiceState.TERMINATED):
        return PolicyDecision.blocked("invoice lifecycle is terminal — no further contact")
    if invoice.state is InvoiceState.HUMAN_REVIEW:
        return PolicyDecision.blocked("invoice is in human review — agent must not nudge")

    contacts = count_outbound_in_window(history, as_of=as_of)
    if contacts >= max_contacts:
        return PolicyDecision.blocked(
            f"contact cap reached ({max_contacts}/week)",
            contacts_this_week=contacts,
        )

    remaining = max_contacts - contacts
    approaching = remaining <= CONTACT_CAP_WARNING_REMAINING
    reason = "contact allowed"
    if approaching:
        reason = f"contact allowed — approaching cap ({contacts}/{max_contacts} this week)"
    return PolicyDecision.allow(
        reason=reason,
        contacts_this_week=contacts,
        approaching_cap=approaching,
    )


def intent_needs_human(intent: ReplyIntent | str, confidence: float) -> bool:
    """True when the parser result must not auto-advance into a promise/nudge."""
    label = intent.value if isinstance(intent, ReplyIntent) else intent
    if confidence < CONFIDENCE_THRESHOLD:
        return True
    return label == ReplyIntent.AMBIGUOUS.value


def event_for_parsed_intent(
    intent: ReplyIntent | str,
    confidence: float,
) -> TransitionEvent:
    """Map a structured parser result onto a ``TransitionEvent``.

    This is the only place confidence is turned into a state-machine event.
    The LLM never chooses the event; this function does.
    """
    label = intent.value if isinstance(intent, ReplyIntent) else intent
    if label == ReplyIntent.DISPUTE.value:
        return TransitionEvent.DISPUTE_RAISED
    if label == ReplyIntent.OPT_OUT.value:
        return TransitionEvent.OPT_OUT_RECEIVED
    if intent_needs_human(label, confidence):
        return TransitionEvent.NEEDS_HUMAN
    if label == ReplyIntent.PROMISE.value:
        return TransitionEvent.PROMISE_LOGGED
    if label == ReplyIntent.OBJECTION.value:
        return TransitionEvent.OBJECTION_RECEIVED
    return TransitionEvent.NEEDS_HUMAN
