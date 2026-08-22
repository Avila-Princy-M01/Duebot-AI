"""Buyer routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.exceptions import NotFoundError
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.schemas.buyer import BuyerDetail, BuyerInvoiceSummary, BuyerOut
from backend.schemas.common import Meta, SuccessEnvelope

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.get("")
async def list_buyers(
    reliability_tier: str | None = None,
    merchant_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[BuyerOut]]:
    """Filterable buyer list."""
    stmt = select(Buyer)
    count_stmt = select(func.count()).select_from(Buyer)
    if reliability_tier:
        stmt = stmt.where(Buyer.reliability_tier == reliability_tier)
        count_stmt = count_stmt.where(Buyer.reliability_tier == reliability_tier)
    if merchant_id:
        stmt = stmt.where(Buyer.merchant_id == merchant_id)
        count_stmt = count_stmt.where(Buyer.merchant_id == merchant_id)
    total = await session.scalar(count_stmt)
    rows = await session.execute(stmt.offset(offset).limit(limit))
    return SuccessEnvelope(
        data=[BuyerOut.model_validate(b) for b in rows.scalars()],
        meta=Meta(total_count=int(total or 0)),
    )


@router.get("/{buyer_id}")
async def get_buyer(
    buyer_id: str,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[BuyerDetail]:
    """Buyer plus invoices."""
    buyer = await session.get(Buyer, buyer_id)
    if buyer is None:
        raise NotFoundError(f"buyer {buyer_id} not found")
    inv_rows = await session.execute(select(Invoice).where(Invoice.buyer_id == buyer_id))
    invoices = [
        BuyerInvoiceSummary(
            invoice_id=inv.invoice_id,
            invoice_number=inv.invoice_number,
            total_amount=inv.total_amount,
            status=inv.status,
            state=inv.state,
            days_overdue=inv.days_overdue,
        )
        for inv in inv_rows.scalars()
    ]
    base = BuyerOut.model_validate(buyer)
    return SuccessEnvelope(
        data=BuyerDetail(
            **base.model_dump(),
            phone=buyer.phone,
            email=buyer.email,
            gstin=buyer.gstin,
            invoices=invoices,
        )
    )
