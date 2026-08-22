"""Hard policy invariants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.engine.policy import (
    CONFIDENCE_THRESHOLD,
    MAX_CONTACTS_PER_WEEK,
    ReplyIntent,
    can_contact,
    event_for_parsed_intent,
    intent_needs_human,
)
from backend.engine.states import InvoiceState, TransitionEvent


@dataclass
class Inv:
    invoice_id: str
    state: InvoiceState
    opted_out: bool


@dataclass
class Touch:
    direction: str
    sent_at: datetime


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


def test_opt_out_blocks() -> None:
    """Opt-out is irreversible and blocks contact."""
    decision = can_contact(
        Inv("INV-1", InvoiceState.NUDGED, opted_out=True),
        [],
        as_of=NOW,
    )
    assert decision.allowed is False
    assert "opted out" in decision.reason


def test_disputed_never_nudged() -> None:
    """Disputed invoices are never contacted."""
    decision = can_contact(
        Inv("INV-1", InvoiceState.DISPUTED, opted_out=False),
        [],
        as_of=NOW,
    )
    assert decision.allowed is False
    assert "disputed" in decision.reason


def test_contact_cap() -> None:
    """Fourth outbound in 7 days is blocked."""
    history = [Touch("outbound", NOW - timedelta(days=i)) for i in range(MAX_CONTACTS_PER_WEEK)]
    decision = can_contact(
        Inv("INV-1", InvoiceState.NUDGED, opted_out=False),
        history,
        as_of=NOW,
    )
    assert decision.allowed is False
    assert "cap" in decision.reason


def test_approaching_cap_warning() -> None:
    """Two contacts this week still allow send but flag approaching cap."""
    history = [
        Touch("outbound", NOW - timedelta(days=1)),
        Touch("outbound", NOW - timedelta(days=2)),
    ]
    decision = can_contact(
        Inv("INV-1", InvoiceState.OVERDUE, opted_out=False),
        history,
        as_of=NOW,
    )
    assert decision.allowed is True
    assert decision.approaching_cap is True


def test_inbound_does_not_count() -> None:
    """Only outbound rows consume the weekly cap."""
    history = [Touch("inbound", NOW - timedelta(hours=1)) for _ in range(5)]
    decision = can_contact(
        Inv("INV-1", InvoiceState.NUDGED, opted_out=False),
        history,
        as_of=NOW,
    )
    assert decision.allowed is True
    assert decision.contacts_this_week == 0


def test_low_confidence_never_logs_promise() -> None:
    """Below 0.7, even intent=promise becomes NEEDS_HUMAN."""
    assert intent_needs_human(ReplyIntent.PROMISE, CONFIDENCE_THRESHOLD - 0.01)
    assert event_for_parsed_intent(ReplyIntent.PROMISE, 0.69) is TransitionEvent.NEEDS_HUMAN
    assert event_for_parsed_intent(ReplyIntent.PROMISE, 0.7) is TransitionEvent.PROMISE_LOGGED
    assert event_for_parsed_intent(ReplyIntent.AMBIGUOUS, 0.99) is TransitionEvent.NEEDS_HUMAN
    assert event_for_parsed_intent(ReplyIntent.DISPUTE, 0.4) is TransitionEvent.DISPUTE_RAISED
