"""Merchant schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class MerchantCreate(BaseModel):
    """POST /api/merchants body."""

    business_name: str
    business_type: str
    gstin: str = Field(min_length=15, max_length=15)
    city: str
    state_code: str = Field(min_length=2, max_length=2)
    onboarded_date: date | None = None


class MerchantOut(BaseModel):
    """Merchant list/detail row."""

    merchant_id: str
    business_name: str
    business_type: str
    gstin: str
    city: str
    state_code: str
    onboarded_date: date

    model_config = {"from_attributes": True}


class MerchantDetail(MerchantOut):
    """Merchant plus rollups."""

    buyer_count: int
    invoice_count: int
    overdue_count: int
