"""Metrics schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class RecoveryMetricsOut(BaseModel):
    """GET /api/metrics/recovery payload."""

    eval_set_size: int
    recovered_count: int
    recovered_value: Decimal
    total_value: Decimal
    recovery_rate: float
    recovery_30d: float
    recovery_60d: float
    recovery_90d: float
    avg_days_to_recovery: float
    promise_kept_rate: float
    false_escalation_rate: float
    total_contacts_sent: int
    split: str


class BaselineRowOut(BaseModel):
    """One strategy in a comparison run."""

    id: UUID
    run_id: UUID
    strategy: str
    eval_set_size: int
    recovered_count: int
    recovered_value: Decimal
    total_value: Decimal
    avg_days_to_recovery: float
    recovery_30d: float
    recovery_60d: float
    recovery_90d: float
    total_contacts_sent: int
    created_at: datetime

    model_config = {"from_attributes": True}
