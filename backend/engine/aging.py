"""Invoice aging — days overdue and bucket assignment.

Pure functions. No I/O. See ARCHITECTURE.md §6.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

__all__ = [
    "AgingBucket",
    "BUCKET_0_30_MAX_DAYS",
    "BUCKET_31_60_MAX_DAYS",
    "BUCKET_61_90_MAX_DAYS",
    "days_overdue",
    "aging_bucket",
]


BUCKET_0_30_MAX_DAYS = 30
BUCKET_31_60_MAX_DAYS = 60
BUCKET_61_90_MAX_DAYS = 90


class AgingBucket(StrEnum):
    """Standard collections aging buckets."""

    CURRENT = "current"
    DAYS_0_30 = "0-30"
    DAYS_31_60 = "31-60"
    DAYS_61_90 = "61-90"
    DAYS_90_PLUS = "90+"


def days_overdue(due_date: date, as_of: date) -> int:
    """Return calendar days past due, or 0 if not yet due.

    Args:
        due_date: Invoice due date.
        as_of: Reference date (typically today, or SIM_TODAY in eval).

    Returns:
        Non-negative integer days overdue.
    """
    delta = (as_of - due_date).days
    return max(delta, 0)


def aging_bucket(days: int) -> AgingBucket:
    """Map a days-overdue count onto a bucket.

    Args:
        days: Output of ``days_overdue``. Must be >= 0.

    Returns:
        The aging bucket. ``CURRENT`` is reserved for ``days == 0``.
    """
    if days <= 0:
        return AgingBucket.CURRENT
    if days <= BUCKET_0_30_MAX_DAYS:
        return AgingBucket.DAYS_0_30
    if days <= BUCKET_31_60_MAX_DAYS:
        return AgingBucket.DAYS_31_60
    if days <= BUCKET_61_90_MAX_DAYS:
        return AgingBucket.DAYS_61_90
    return AgingBucket.DAYS_90_PLUS
