"""Buyer ORM model."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.invoice import Invoice
    from backend.models.merchant import Merchant


class Buyer(Base):
    """Business that owes a merchant."""

    __tablename__ = "buyers"
    __table_args__ = (
        CheckConstraint(
            "reliability_tier IN ('reliable', 'occasional_late', 'chronic_late')",
            name="ck_buyers_reliability_tier",
        ),
        CheckConstraint(
            "on_time_payment_rate >= 0.0 AND on_time_payment_rate <= 1.0",
            name="ck_buyers_on_time_rate",
        ),
        Index("idx_buyers_merchant", "merchant_id"),
    )

    buyer_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("merchants.merchant_id"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    reliability_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    on_time_payment_rate: Mapped[float] = mapped_column(Float, nullable=False)
    relationship_since: Mapped[dt.date] = mapped_column(Date, nullable=False)

    merchant: Mapped[Merchant] = relationship(back_populates="buyers")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="buyer")
