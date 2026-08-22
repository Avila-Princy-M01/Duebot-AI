"""Deterministic buyer/invoice risk classification.

Aligned with ``backend.data.generator.DueBotDataGenerator._risk_tier`` so
seeded invoices and live scoring use the same rule.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ReliabilityTier",
    "RiskTier",
    "HIGH_RISK_OVERDUE_DAYS",
    "MEDIUM_RISK_OVERDUE_DAYS",
    "risk_tier",
]


HIGH_RISK_OVERDUE_DAYS = 60
MEDIUM_RISK_OVERDUE_DAYS = 21


class ReliabilityTier(StrEnum):
    """Buyer payment-history band from the synthetic generator / CRM."""

    RELIABLE = "reliable"
    OCCASIONAL_LATE = "occasional_late"
    CHRONIC_LATE = "chronic_late"


class RiskTier(StrEnum):
    """Invoice-level collections risk used by the scheduler."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def risk_tier(reliability: ReliabilityTier | str, overdue_days: int) -> RiskTier:
    """Classify risk from buyer reliability and days overdue.

    Args:
        reliability: Buyer reliability tier.
        overdue_days: ``days_overdue`` for this invoice (>= 0).

    Returns:
        ``low``, ``medium``, or ``high``.
    """
    tier = reliability if isinstance(reliability, ReliabilityTier) else ReliabilityTier(reliability)
    if overdue_days <= 0:
        return RiskTier.LOW
    if tier is ReliabilityTier.CHRONIC_LATE or overdue_days > HIGH_RISK_OVERDUE_DAYS:
        return RiskTier.HIGH
    if tier is ReliabilityTier.OCCASIONAL_LATE or overdue_days > MEDIUM_RISK_OVERDUE_DAYS:
        return RiskTier.MEDIUM
    return RiskTier.LOW
