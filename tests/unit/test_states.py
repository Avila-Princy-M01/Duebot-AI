"""State machine graph: every legal edge and every illegal refusal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from backend.engine.states import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    InvalidTransitionError,
    InvoiceState,
    TransitionEvent,
    allowed_events,
    can_transition,
    is_valid_transition,
    transition,
)


@dataclass
class Inv:
    invoice_id: str
    state: InvoiceState


def _inv(state: InvoiceState) -> Inv:
    return Inv(invoice_id="INV-test", state=state)


def test_every_valid_edge_succeeds() -> None:
    """Every entry in VALID_TRANSITIONS produces the mapped next state plus audit."""
    occurred = datetime(2026, 8, 21, tzinfo=UTC)
    for from_state, edges in VALID_TRANSITIONS.items():
        for event, to_state in edges.items():
            result = transition(
                _inv(from_state),
                event,
                reasoning="parametrized graph walk",
                actor="system",
                occurred_at=occurred,
            )
            assert result.new_state is to_state
            assert result.audit_entry.from_state is from_state
            assert result.audit_entry.to_state is to_state
            assert result.audit_entry.event is event
            assert result.audit_entry.invoice_id == "INV-test"


@pytest.mark.parametrize("state", list(InvoiceState))
def test_illegal_event_raises(state: InvoiceState) -> None:
    """Any event not on the state's outgoing edges raises InvalidTransitionError."""
    legal = allowed_events(state)
    for event in TransitionEvent:
        if event in legal:
            continue
        with pytest.raises(InvalidTransitionError):
            transition(_inv(state), event, reasoning="should fail")
        allowed, _reason = can_transition(state, event)
        assert allowed is False
        assert is_valid_transition(state, event) is False


def test_terminal_states_have_no_exits() -> None:
    """RECOVERED and TERMINATED cannot move."""
    for state in TERMINAL_STATES:
        assert allowed_events(state) == frozenset()
        with pytest.raises(InvalidTransitionError):
            transition(_inv(state), TransitionEvent.NUDGE_SENT, reasoning="no")


def test_transition_does_not_mutate_invoice() -> None:
    """Pure function: invoice.state is unchanged after the call."""
    invoice = _inv(InvoiceState.CREATED)
    transition(invoice, TransitionEvent.AGED, reasoning="aged")
    assert invoice.state is InvoiceState.CREATED


def test_can_transition_explains_success() -> None:
    """Happy-path reason string names both states."""
    ok, reason = can_transition(InvoiceState.CREATED, TransitionEvent.AGED)
    assert ok is True
    assert "overdue" in reason


def test_early_payment_from_created_to_recovered() -> None:
    """An invoice paid before or on due date transitions directly CREATED -> RECOVERED."""
    invoice = _inv(InvoiceState.CREATED)
    assert is_valid_transition(InvoiceState.CREATED, TransitionEvent.PAYMENT_CONFIRMED) is True
    result = transition(
        invoice,
        TransitionEvent.PAYMENT_CONFIRMED,
        reasoning="early payment settled",
    )
    assert result.new_state is InvoiceState.RECOVERED
    assert result.audit_entry.from_state is InvoiceState.CREATED
    assert result.audit_entry.to_state is InvoiceState.RECOVERED
