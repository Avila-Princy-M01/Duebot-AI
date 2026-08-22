"""Risk-tier alignment with the synthetic generator."""

from __future__ import annotations

import pytest
from backend.engine.risk_tier import ReliabilityTier, RiskTier, risk_tier


@pytest.mark.parametrize(
    ("tier", "days", "expected"),
    [
        (ReliabilityTier.RELIABLE, 0, RiskTier.LOW),
        (ReliabilityTier.RELIABLE, 10, RiskTier.LOW),
        (ReliabilityTier.RELIABLE, 22, RiskTier.MEDIUM),
        (ReliabilityTier.RELIABLE, 61, RiskTier.HIGH),
        (ReliabilityTier.OCCASIONAL_LATE, 5, RiskTier.MEDIUM),
        (ReliabilityTier.CHRONIC_LATE, 2, RiskTier.HIGH),
        ("chronic_late", 1, RiskTier.HIGH),
    ],
)
def test_risk_tier(tier: ReliabilityTier | str, days: int, expected: RiskTier) -> None:
    """Chronic or 60+ days is high; occasional or 21+ is at least medium."""
    assert risk_tier(tier, days) is expected
