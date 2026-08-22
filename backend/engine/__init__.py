"""Deterministic engine — aging, risk, policy, scheduler, state machine, metrics.

This package makes zero network calls. See ARCHITECTURE.md §6.
"""

from backend.engine.aging import AgingBucket, aging_bucket, days_overdue
from backend.engine.policy import (
    CONFIDENCE_THRESHOLD,
    CONTACT_WINDOW_DAYS,
    MAX_CONTACTS_PER_WEEK,
    PolicyDecision,
    can_contact,
    event_for_parsed_intent,
    intent_needs_human,
)
from backend.engine.recovery_metrics import RecoveryReport, recovery_report
from backend.engine.risk_tier import ReliabilityTier, RiskTier, risk_tier
from backend.engine.scheduler import next_action_at
from backend.engine.states import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    Actor,
    AuditLogEntry,
    HasInvoiceState,
    InvalidTransitionError,
    InvoiceState,
    Transition,
    TransitionEvent,
    allowed_events,
    can_transition,
    is_valid_transition,
    transition,
)

__all__ = [
    "AgingBucket",
    "aging_bucket",
    "days_overdue",
    "CONFIDENCE_THRESHOLD",
    "CONTACT_WINDOW_DAYS",
    "MAX_CONTACTS_PER_WEEK",
    "PolicyDecision",
    "can_contact",
    "event_for_parsed_intent",
    "intent_needs_human",
    "RecoveryReport",
    "recovery_report",
    "ReliabilityTier",
    "RiskTier",
    "risk_tier",
    "next_action_at",
    "TERMINAL_STATES",
    "VALID_TRANSITIONS",
    "Actor",
    "AuditLogEntry",
    "HasInvoiceState",
    "InvalidTransitionError",
    "InvoiceState",
    "Transition",
    "TransitionEvent",
    "allowed_events",
    "can_transition",
    "is_valid_transition",
    "transition",
]
