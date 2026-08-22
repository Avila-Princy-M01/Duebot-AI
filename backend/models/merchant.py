"""Merchant ORM model."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.buyer import Buyer
    from backend.models.invoice import Invoice


class Merchant(Base):
    """SME seller onboarded to DueBot."""

    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    onboarded_date: Mapped[dt.date] = mapped_column(Date, nullable=False)

    buyers: Mapped[list[Buyer]] = relationship(back_populates="merchant")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="merchant")
