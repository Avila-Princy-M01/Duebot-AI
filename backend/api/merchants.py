"""Merchant routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.exceptions import NotFoundError
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.schemas.common import Meta, SuccessEnvelope
from backend.schemas.merchant import MerchantCreate, MerchantDetail, MerchantOut

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("")
async def list_merchants(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[MerchantOut]]:
    """List merchants."""
    total = await session.scalar(select(func.count()).select_from(Merchant))
    rows = await session.execute(select(Merchant).offset(offset).limit(limit))
    data = [MerchantOut.model_validate(m) for m in rows.scalars()]
    return SuccessEnvelope(data=data, meta=Meta(total_count=int(total or 0)))


@router.post("")
async def create_merchant(
    body: MerchantCreate,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[MerchantOut]:
    """Create a merchant."""
    count = await session.scalar(select(func.count()).select_from(Merchant))
    merchant_id = f"MER-{(int(count or 0) + 1):03d}"
    merchant = Merchant(
        merchant_id=merchant_id,
        business_name=body.business_name,
        business_type=body.business_type,
        gstin=body.gstin,
        city=body.city,
        state_code=body.state_code,
        onboarded_date=body.onboarded_date or date.today(),
    )
    session.add(merchant)
    await session.flush()
    return SuccessEnvelope(data=MerchantOut.model_validate(merchant))


@router.get("/{merchant_id}")
async def get_merchant(
    merchant_id: str,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[MerchantDetail]:
    """Single merchant plus counts."""
    merchant = await session.get(Merchant, merchant_id)
    if merchant is None:
        raise NotFoundError(f"merchant {merchant_id} not found")
    buyer_count = await session.scalar(
        select(func.count()).select_from(Buyer).where(Buyer.merchant_id == merchant_id)
    )
    invoice_count = await session.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.merchant_id == merchant_id)
    )
    overdue_count = await session.scalar(
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.merchant_id == merchant_id, Invoice.status == "overdue")
    )
    base = MerchantOut.model_validate(merchant)
    return SuccessEnvelope(
        data=MerchantDetail(
            **base.model_dump(),
            buyer_count=int(buyer_count or 0),
            invoice_count=int(invoice_count or 0),
            overdue_count=int(overdue_count or 0),
        )
    )
