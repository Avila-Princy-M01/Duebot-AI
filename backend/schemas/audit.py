"""Audit log schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEntryOut(BaseModel):
    """One append-only audit row."""

    id: UUID
    invoice_id: str
    from_state: str
    to_state: str
    actor: str
    occurred_at: datetime
    reasoning_summary: str
    extra_metadata: dict[str, Any] | None = Field(default=None, validation_alias="extra_metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}
