"""Promise-to-pay ORM model."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.interaction import Interaction
    from backend.models.invoice import Invoice


class Promise(Base):
    """A high-confidence promise extracted from a buyer reply."""

    __tablename__ = "promises"
    __table_args__ = (
        CheckConstraint("confidence >= 0.7", name="ck_promises_confidence"),
        CheckConstraint("status IN ('pending', 'kept', 'broken')", name="ck_promises_status"),
        Index("idx_promises_invoice", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[str] = mapped_column(
        String(25), ForeignKey("invoices.invoice_id"), nullable=False
    )
    source_interaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interactions.id"), nullable=False
    )
    promised_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    promised_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invoice: Mapped[Invoice] = relationship(back_populates="promises")
    source_interaction: Mapped[Interaction] = relationship(back_populates="promises")
