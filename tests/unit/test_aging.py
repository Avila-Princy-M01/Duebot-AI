"""Aging buckets."""

from __future__ import annotations

from datetime import date

import pytest
from backend.engine.aging import AgingBucket, aging_bucket, days_overdue


@pytest.mark.parametrize(
    ("due", "as_of", "expected"),
    [
        (date(2026, 8, 21), date(2026, 8, 21), 0),
        (date(2026, 8, 22), date(2026, 8, 21), 0),
        (date(2026, 8, 1), date(2026, 8, 21), 20),
    ],
)
def test_days_overdue(due: date, as_of: date, expected: int) -> None:
    """Not-yet-due invoices are 0, never negative."""
    assert days_overdue(due, as_of) == expected


@pytest.mark.parametrize(
    ("days", "bucket"),
    [
        (0, AgingBucket.CURRENT),
        (1, AgingBucket.DAYS_0_30),
        (30, AgingBucket.DAYS_0_30),
        (31, AgingBucket.DAYS_31_60),
        (60, AgingBucket.DAYS_31_60),
        (61, AgingBucket.DAYS_61_90),
        (90, AgingBucket.DAYS_61_90),
        (91, AgingBucket.DAYS_90_PLUS),
        (400, AgingBucket.DAYS_90_PLUS),
    ],
)
def test_aging_bucket(days: int, bucket: AgingBucket) -> None:
    """Bucket boundaries are inclusive on the upper end of each range."""
    assert aging_bucket(days) is bucket
