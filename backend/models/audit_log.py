"""Append-only audit log ORM model.

Application code must never UPDATE or DELETE rows on this table.
Immutability is mathematically guaranteed by the SHA-256 hash chain (GET /api/audit/verify).
Database-level REVOKE is documented for production PostgreSQL multi-tenant hardening.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.invoice import Invoice


class AuditLog(Base):
    """One immutable state-transition row."""

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("actor IN ('agent', 'human', 'system')", name="ck_audit_actor"),
        Index("idx_audit_invoice", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[str] = mapped_column(
        String(25), ForeignKey("invoices.invoice_id"), nullable=False
    )
    from_state: Mapped[str] = mapped_column(String(20), nullable=False)
    to_state: Mapped[str] = mapped_column(String(20), nullable=False)
    actor: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="0" * 64)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="0" * 64)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    invoice: Mapped[Invoice] = relationship(back_populates="audit_entries")
