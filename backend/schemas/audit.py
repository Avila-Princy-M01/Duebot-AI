"""Audit log schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class AuditEntryOut(BaseModel):
    """One append-only audit row."""

    id: UUID
    invoice_id: str
    from_state: str
    to_state: str
    actor: str
    occurred_at: datetime
    reasoning_summary: str
    prev_hash: str = Field(default="0" * 64)
    row_hash: str = Field(default="0" * 64)
    extra_metadata: dict[str, Any] | None = Field(default=None, validation_alias="extra_metadata")

    @field_serializer("occurred_at")
    def serialize_occurred_at(self, val: datetime) -> str:
        if val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val.isoformat()

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuditVerificationOut(BaseModel):
    """Cryptographic chain verification result."""

    valid: bool
    rows_verified: int
    genesis_hash: str
    latest_hash: str
    verified_at: datetime
    error: str | None = None

    @field_serializer("verified_at")
    def serialize_verified_at(self, val: datetime) -> str:
        if val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val.isoformat()
