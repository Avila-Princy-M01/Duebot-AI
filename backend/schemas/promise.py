"""Promise schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from backend.schemas.invoice import InteractionOut


class PromiseOut(BaseModel):
    """Promise list row."""

    id: UUID
    invoice_id: str
    source_interaction_id: UUID
    promised_date: date
    promised_amount: Decimal | None
    confidence: float
    status: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class PromiseDetail(PromiseOut):
    """Promise plus originating reply."""

    source_interaction: InteractionOut | None = None
