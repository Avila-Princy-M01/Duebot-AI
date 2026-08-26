"""Deterministic invoice lifecycle state machine.

This module is the spine of DueBot's engine layer (see ARCHITECTURE.md §4).
It defines every legal state, every legal transition between states, and the
single `transition()` function that enforces the graph.

Hard rules that make this module trustworthy under review:

  * Zero I/O. No database session, no HTTP client, no LLM call appears
    anywhere in this file. `transition()` is a pure function: given a current
    state and an event, it either returns the next state plus an audit-log
    entry to be persisted by the caller, or raises `InvalidTransitionError`.
    Persistence is the caller's job (typically a task in `backend/tasks/`
    wrapping this call in a single DB transaction with the audit write).

  * The LLM never appears as an input to this module beyond an already-
    classified `TransitionEvent`. By the time code reaches `transition()`,
    any judgment call about *what a buyer's reply meant* has already been
    made in `backend/llm/reply_parser.py` and reduced to one of the events
    below (e.g. `PROMISE_LOGGED` vs `NEEDS_HUMAN`). This module only ever
    asks "is this move legal from here," never "was that judgment correct."

  * `VALID_TRANSITIONS` is the single source of truth for the graph. Do not
    special-case a transition anywhere else in the codebase — if a new edge
    is needed, it is added here, reviewed here, and tested here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Protocol

__all__ = [
    "InvoiceState",
    "TransitionEvent",
    "Actor",
    "VALID_TRANSITIONS",
    "TERMINAL_STATES",
    "InvalidTransitionError",
    "AuditLogEntry",
    "Transition",
    "HasInvoiceState",
    "allowed_events",
    "is_valid_transition",
    "can_transition",
    "transition",
]


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------


class InvoiceState(StrEnum):
    """Every state an invoice can be in. See ARCHITECTURE.md §4 for the diagram."""

    CREATED = "created"
    OVERDUE = "overdue"
    NUDGED = "nudged"
    REPLIED = "replied"
    PROMISED = "promised"
    REMINDED = "reminded"
    RECOVERED = "recovered"
    DISPUTED = "disputed"
    ESCALATED = "escalated"
    HUMAN_REVIEW = "human_review"
    OPTED_OUT = "opted_out"
    TERMINATED = "terminated"


TERMINAL_STATES: frozenset[InvoiceState] = frozenset(
    {InvoiceState.RECOVERED, InvoiceState.TERMINATED}
)
"""States with no outgoing edges. Once reached, an invoice's lifecycle is over."""


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class TransitionEvent(StrEnum):
    """Every deterministic trigger that can move an invoice between states.

    Every member here corresponds to a fact the caller has already
    established (elapsed time, a webhook-confirmed payment, a policy
    decision, or an already-classified LLM intent) — never to raw LLM text.
    """

    # Aging (engine/aging.py)
    AGED = "aged"

    # Outbound nudge lifecycle (engine/scheduler.py, tasks/nudge_executor.py)
    NUDGE_SENT = "nudge_sent"
    CONTACT_CAP_REACHED = "contact_cap_reached"

    # Inbound reply lifecycle (tasks/reply_processor.py)
    REPLY_RECEIVED = "reply_received"

    # Classified reply intent, produced by llm/reply_parser.py + the
    # confidence-threshold check that wraps it — never the raw LLM output.
    PROMISE_LOGGED = "promise_logged"
    OBJECTION_RECEIVED = "objection_received"
    DISPUTE_RAISED = "dispute_raised"
    OPT_OUT_RECEIVED = "opt_out_received"
    NEEDS_HUMAN = "needs_human"  # ambiguous intent OR confidence < threshold

    # Promise lifecycle (tasks/promise_checker.py)
    PAYMENT_CONFIRMED = "payment_confirmed"
    PROMISE_DATE_PASSED = "promise_date_passed"
    PROMISE_BROKEN = "promise_broken"

    # Routing anything uncertain or risky into the single human queue
    ROUTED_TO_HUMAN = "routed_to_human"

    # Opt-out is terminal and irreversible once acknowledged
    OPT_OUT_FINALIZED = "opt_out_finalized"

    # Resolutions a human makes from the review queue
    HUMAN_RESOLVED_RECOVERED = "human_resolved_recovered"
    HUMAN_RESOLVED_CLOSED = "human_resolved_closed"


# ---------------------------------------------------------------------------
# The graph
# ---------------------------------------------------------------------------


VALID_TRANSITIONS: Mapping[InvoiceState, Mapping[TransitionEvent, InvoiceState]] = {
    InvoiceState.CREATED: {
        TransitionEvent.AGED: InvoiceState.OVERDUE,
        # Early or on-time payment confirmed before invoice passes due date
        TransitionEvent.PAYMENT_CONFIRMED: InvoiceState.RECOVERED,
    },
    InvoiceState.OVERDUE: {
        TransitionEvent.NUDGE_SENT: InvoiceState.NUDGED,
        # Payment webhook can arrive before any nudge was sent
        TransitionEvent.PAYMENT_CONFIRMED: InvoiceState.RECOVERED,
    },
    InvoiceState.NUDGED: {
        TransitionEvent.REPLY_RECEIVED: InvoiceState.REPLIED,
        TransitionEvent.CONTACT_CAP_REACHED: InvoiceState.ESCALATED,
        # Payment webhook can arrive after nudge, before buyer replies
        TransitionEvent.PAYMENT_CONFIRMED: InvoiceState.RECOVERED,
    },
    InvoiceState.REPLIED: {
        # promise, confidence >= CONFIDENCE_THRESHOLD (llm/reply_parser.py)
        TransitionEvent.PROMISE_LOGGED: InvoiceState.PROMISED,
        # objection ("give us two more weeks") re-enters the nudge cycle
        TransitionEvent.OBJECTION_RECEIVED: InvoiceState.NUDGED,
        # ambiguous intent, or confidence < CONFIDENCE_THRESHOLD — never guess
        TransitionEvent.NEEDS_HUMAN: InvoiceState.HUMAN_REVIEW,
        # buyer disputes the invoice — never nudge a disputed invoice again
        TransitionEvent.DISPUTE_RAISED: InvoiceState.DISPUTED,
        # buyer opts out — irreversible from the system's side
        TransitionEvent.OPT_OUT_RECEIVED: InvoiceState.OPTED_OUT,
    },
    InvoiceState.PROMISED: {
        TransitionEvent.PAYMENT_CONFIRMED: InvoiceState.RECOVERED,
        TransitionEvent.PROMISE_DATE_PASSED: InvoiceState.REMINDED,
    },
    InvoiceState.REMINDED: {
        TransitionEvent.PAYMENT_CONFIRMED: InvoiceState.RECOVERED,
        TransitionEvent.PROMISE_BROKEN: InvoiceState.ESCALATED,
    },
    InvoiceState.DISPUTED: {
        TransitionEvent.ROUTED_TO_HUMAN: InvoiceState.HUMAN_REVIEW,
    },
    InvoiceState.ESCALATED: {
        TransitionEvent.ROUTED_TO_HUMAN: InvoiceState.HUMAN_REVIEW,
    },
    InvoiceState.HUMAN_REVIEW: {
        TransitionEvent.HUMAN_RESOLVED_RECOVERED: InvoiceState.RECOVERED,
        TransitionEvent.HUMAN_RESOLVED_CLOSED: InvoiceState.TERMINATED,
    },
    InvoiceState.OPTED_OUT: {
        TransitionEvent.OPT_OUT_FINALIZED: InvoiceState.TERMINATED,
    },
    # Terminal states: no outgoing edges.
    InvoiceState.RECOVERED: {},
    InvoiceState.TERMINATED: {},
}


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------


Actor = Literal["agent", "human", "system"]
"""Who caused a transition. `agent` = the deterministic engine acting on a
policy rule; `human` = a merchant action from the dashboard; `system` = an
external, verifiable fact such as a payment-confirmation webhook."""

DEFAULT_ACTOR: Actor = "agent"


class HasInvoiceState(Protocol):
    """Structural type for anything `transition()` can act on.

    Deliberately not the SQLAlchemy `Invoice` model — the engine layer must
    not import from `backend/models/`. Any object with an `invoice_id` and a
    `state` satisfies this, which keeps `transition()` testable with a plain
    dataclass and unusable as an excuse to smuggle I/O into this module.
    """

    invoice_id: str
    state: InvoiceState


class InvalidTransitionError(Exception):
    """Raised when an event is not a legal move from the invoice's current state.

    This should never be caught and silently ignored — an invalid transition
    means a caller has a bug (e.g. attempting to nudge an invoice that's
    already `TERMINATED`), not a recoverable runtime condition.
    """

    def __init__(self, invoice_id: str, from_state: InvoiceState, event: TransitionEvent) -> None:
        self.invoice_id = invoice_id
        self.from_state = from_state
        self.event = event
        allowed = sorted(e.value for e in allowed_events(from_state))
        super().__init__(
            f"invoice {invoice_id}: event {event.value!r} is not valid from "
            f"state {from_state.value!r} (allowed: {allowed or 'none — terminal state'})"
        )


@dataclass(frozen=True, slots=True)
class AuditLogEntry:
    """One immutable row destined for the `audit_log` table (ARCHITECTURE.md §5).

    This dataclass only *constructs* the row. Writing it to the database,
    atomically alongside the invoice's new state, is the caller's
    responsibility — `engine/` does not touch Postgres.
    """

    invoice_id: str
    from_state: InvoiceState
    to_state: InvoiceState
    event: TransitionEvent
    actor: Actor
    occurred_at: datetime
    reasoning_summary: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Transition:
    """The result of a successful `transition()` call: the new state plus
    the audit row the caller must persist before treating the move as final."""

    invoice_id: str
    new_state: InvoiceState
    audit_entry: AuditLogEntry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def allowed_events(state: InvoiceState) -> frozenset[TransitionEvent]:
    """Return every event that is legal from the given state.

    Useful for building the dashboard's available-actions UI and for
    property-based tests that assert `transition()` rejects everything not
    in this set.
    """
    return frozenset(VALID_TRANSITIONS[state].keys())


def is_valid_transition(from_state: InvoiceState, event: TransitionEvent) -> bool:
    """Check legality without mutating anything or raising.

    Args:
        from_state: The invoice's current state.
        event: The proposed trigger.

    Returns:
        True if `event` has a defined edge out of `from_state`.
    """
    return event in VALID_TRANSITIONS.get(from_state, {})


def can_transition(
    from_state: InvoiceState,
    event: TransitionEvent,
) -> tuple[bool, str]:
    """Check if a transition is legal and explain why or why not.

    Like `is_valid_transition()`, but returns a human-readable reason.
    Useful for the nudge preview endpoint, dry-run mode, and debugging.

    Args:
        from_state: The invoice's current state.
        event: The proposed trigger.

    Returns:
        (allowed, reason) — reason explains the decision.
    """
    targets = VALID_TRANSITIONS.get(from_state)
    if targets is None:
        return False, f"State {from_state.value!r} has no outgoing transitions"

    if event in targets:
        to_state = targets[event]
        return True, f"Transition {from_state.value} → {to_state.value} via {event.value} allowed"

    valid_events = sorted(e.value for e in targets)
    return (
        False,
        f"Event {event.value!r} not valid from {from_state.value!r}. "
        f"Allowed events: {valid_events or ['none — terminal state']}",
    )


def transition(
    invoice: HasInvoiceState,
    event: TransitionEvent,
    *,
    reasoning: str,
    actor: Actor = DEFAULT_ACTOR,
    metadata: Mapping[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> Transition:
    """Advance an invoice's state by exactly one legal edge.

    This function does not mutate `invoice` and does not write to any
    database — it is pure. The caller is expected to persist both the new
    state and the returned `audit_entry` in a single transaction, and to
    abort the whole operation (never send the message, never apply the new
    state) if that persistence fails — see ARCHITECTURE.md §10, invariant 6.

    Args:
        invoice: The invoice being transitioned. Only `invoice_id` and
            `state` are read.
        event: The deterministic trigger for this transition. Must already
            reflect any upstream judgment (e.g. LLM confidence-threshold
            check) — this function does not re-derive it.
        reasoning: A one-sentence, human-readable explanation of why this
            transition is happening now. This is what a merchant sees in
            the audit log viewer and what an auditor sees when asking "why did
            it do that" — never leave it empty or generic.
        actor: Who/what caused this transition. Defaults to `"agent"`.
        metadata: Optional structured detail for the audit row (e.g. the
            parsed confidence score, the policy rule that fired).
        occurred_at: Timestamp for the transition. Defaults to now (UTC).
            Exposed as a parameter so tests and backfills can be deterministic.

    Returns:
        A `Transition` bundling the new state and the audit-log entry to persist.

    Raises:
        InvalidTransitionError: If `event` has no defined edge out of the
            invoice's current state. This includes any attempt to transition
            out of a terminal state (`RECOVERED`, `TERMINATED`).
    """
    from_state = invoice.state

    if not is_valid_transition(from_state, event):
        raise InvalidTransitionError(invoice.invoice_id, from_state, event)

    to_state = VALID_TRANSITIONS[from_state][event]

    audit_entry = AuditLogEntry(
        invoice_id=invoice.invoice_id,
        from_state=from_state,
        to_state=to_state,
        event=event,
        actor=actor,
        occurred_at=occurred_at or datetime.now(UTC),
        reasoning_summary=reasoning,
        metadata=metadata or {},
    )

    return Transition(
        invoice_id=invoice.invoice_id,
        new_state=to_state,
        audit_entry=audit_entry,
    )
