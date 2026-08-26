"""Buyer schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class BuyerCreate(BaseModel):
    """Create-buyer payload (seed/internal)."""

    buyer_id: str | None = None
    merchant_id: str
    company_name: str
    contact_name: str
    phone: str
    email: str
    gstin: str
    reliability_tier: str
    on_time_payment_rate: float = Field(ge=0.0, le=1.0)
    relationship_since: date


class BuyerOut(BaseModel):
    """Buyer list row."""

    buyer_id: str
    merchant_id: str
    company_name: str
    contact_name: str
    reliability_tier: str
    on_time_payment_rate: float
    relationship_since: date

    model_config = {"from_attributes": True}


class BuyerInvoiceSummary(BaseModel):
    """Compact invoice on a buyer detail page."""

    invoice_id: str
    invoice_number: str
    total_amount: Decimal
    amount_paid: Decimal
    outstanding_amount: Decimal
    due_date: date
    status: str
    state: str
    days_overdue: int


class BuyerDetail(BuyerOut):
    """Buyer plus invoices. Phone and email are included on detail only."""

    phone: str
    email: str
    gstin: str
    invoices: list[BuyerInvoiceSummary]


class BuyerBriefOut(BaseModel):
    """AI Executive Briefing for a buyer."""

    buyer_id: str
    company_name: str
    contact_name: str
    summary: str
    spoken_summary: str
    risk_assessment: str
    recommended_action: str
    total_outstanding_inr: str
    open_invoices_count: int
    model: str
