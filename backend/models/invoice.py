"""Invoice ORM model."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.audit_log import AuditLog
    from backend.models.buyer import Buyer
    from backend.models.interaction import Interaction
    from backend.models.merchant import Merchant
    from backend.models.promise import Promise


class Invoice(Base):
    """A single B2B receivable tracked by the state machine."""

    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("payment_terms_days IN (15, 30, 45, 60)", name="ck_invoices_terms"),
        CheckConstraint("subtotal_amount > 0", name="ck_invoices_subtotal"),
        CheckConstraint("gst_rate IN (0, 5, 12, 18, 28)", name="ck_invoices_gst_rate"),
        CheckConstraint(
            "status IN ('paid', 'partial', 'pending', 'overdue', 'disputed')",
            name="ck_invoices_status",
        ),
        CheckConstraint("days_overdue >= 0", name="ck_invoices_days_overdue"),
        CheckConstraint("risk_tier IN ('low', 'medium', 'high')", name="ck_invoices_risk"),
        CheckConstraint("split IN ('train', 'test')", name="ck_invoices_split"),
        CheckConstraint(
            "promise_outcome IN ('none', 'pending', 'kept', 'broken')",
            name="ck_invoices_promise_outcome",
        ),
        Index("idx_invoices_merchant", "merchant_id"),
        Index("idx_invoices_buyer", "buyer_id"),
        Index("idx_invoices_status", "status"),
        Index("idx_invoices_state", "state"),
    )

    invoice_id: Mapped[str] = mapped_column(String(25), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("merchants.merchant_id"), nullable=False
    )
    buyer_id: Mapped[str] = mapped_column(String(30), ForeignKey("buyers.buyer_id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    issue_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gst_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    paid_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    days_overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_tier: Mapped[str] = mapped_column(String(10), nullable=False)
    payment_link_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    edge_case: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    would_have_paid_without_intervention: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    promise_outcome: Mapped[str] = mapped_column(String(10), nullable=False, default="none")
    split: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    merchant: Mapped[Merchant] = relationship(back_populates="invoices")
    buyer: Mapped[Buyer] = relationship(back_populates="invoices")
    interactions: Mapped[list[Interaction]] = relationship(back_populates="invoice")
    promises: Mapped[list[Promise]] = relationship(back_populates="invoice")
    audit_entries: Mapped[list[AuditLog]] = relationship(back_populates="invoice")
