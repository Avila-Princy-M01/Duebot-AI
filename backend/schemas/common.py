"""Shared API envelope types (ARCHITECTURE.md §14)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Response metadata."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    total_count: int | None = None


class SuccessEnvelope(BaseModel, Generic[T]):
    """Successful JSON envelope."""

    data: T
    meta: Meta = Field(default_factory=Meta)


class ErrorBody(BaseModel):
    """Machine-readable error."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    """Error JSON envelope."""

    error: ErrorBody
