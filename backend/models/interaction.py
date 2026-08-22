"""Interaction (message thread) ORM model."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.invoice import Invoice
    from backend.models.promise import Promise


class Interaction(Base):
    """One inbound or outbound message on an invoice thread."""

    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint("channel IN ('whatsapp', 'email')", name="ck_interactions_channel"),
        CheckConstraint("direction IN ('outbound', 'inbound')", name="ck_interactions_direction"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_interactions_confidence",
        ),
        CheckConstraint(
            "delivery_status IN ('pending', 'sent', 'delivered', 'failed')",
            name="ck_interactions_delivery",
        ),
        Index("idx_interactions_invoice", "invoice_id"),
        Index("idx_interactions_buyer", "buyer_id"),
        Index("idx_interactions_idempotency", "invoice_id", "attempt_number", unique=False),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[str] = mapped_column(
        String(25), ForeignKey("invoices.invoice_id"), nullable=False
    )
    buyer_id: Mapped[str] = mapped_column(String(30), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    sent_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_label: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice: Mapped[Invoice] = relationship(back_populates="interactions")
    promises: Mapped[list[Promise]] = relationship(back_populates="source_interaction")
