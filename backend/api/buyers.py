from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import buyer_briefer, get_db
from backend.exceptions import NotFoundError
from backend.llm.buyer_briefer import BuyerBriefer, BuyerBriefRequest
from backend.models.audit_log import AuditLog
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.promise import Promise
from backend.schemas.buyer import BuyerBriefOut, BuyerDetail, BuyerInvoiceSummary, BuyerOut
from backend.schemas.common import Meta, SuccessEnvelope

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.get("")
async def list_buyers(
    reliability_tier: str | None = None,
    merchant_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
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
            amount_paid=inv.amount_paid,
            outstanding_amount=max(Decimal("0"), inv.total_amount - inv.amount_paid),
            due_date=inv.due_date,
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


@router.get("/{buyer_id}/brief")
async def brief_buyer(
    buyer_id: str,
    session: AsyncSession = Depends(get_db),
    briefer: BuyerBriefer = Depends(buyer_briefer),
) -> SuccessEnvelope[BuyerBriefOut]:
    """Scoped read-only AI summary of a buyer's payment history and current status."""
    buyer = await session.get(Buyer, buyer_id)
    if buyer is None:
        raise NotFoundError(f"buyer {buyer_id} not found")

    # Invoices
    inv_result = await session.execute(select(Invoice).where(Invoice.buyer_id == buyer_id))
    invoices = list(inv_result.scalars().all())
    inv_ids = [inv.invoice_id for inv in invoices]

    open_invoices = [inv for inv in invoices if inv.status in ("overdue", "partial", "pending")]
    total_outstanding = sum(
        (inv.total_amount - inv.amount_paid for inv in open_invoices),
        Decimal("0"),
    )

    # Interactions
    int_result = await session.execute(
        select(Interaction)
        .where(Interaction.buyer_id == buyer_id)
        .order_by(Interaction.sent_at.desc())
        .limit(5)
    )
    interactions = [
        f"{i.direction.upper()} ({i.sent_at.strftime('%b %d')}): {i.message_text[:80]}"
        for i in int_result.scalars().all()
    ]

    # Promises
    promises: list[str] = []
    if inv_ids:
        prom_result = await session.execute(
            select(Promise)
            .where(Promise.invoice_id.in_(inv_ids))
            .order_by(Promise.promised_date.desc())
            .limit(3)
        )
        promises = [
            f"Promise on {p.invoice_id} for {p.promised_date} (Status: {p.status})"
            for p in prom_result.scalars().all()
        ]

    # Audits
    audits: list[str] = []
    if inv_ids:
        audit_result = await session.execute(
            select(AuditLog)
            .where(AuditLog.invoice_id.in_(inv_ids))
            .order_by(AuditLog.occurred_at.desc())
            .limit(5)
        )
        audits = [
            (
                f"{a.invoice_id} ({a.occurred_at.strftime('%b %d')}): "
                f"{a.from_state}->{a.to_state} ({a.reasoning_summary})"
            )
            for a in audit_result.scalars().all()
        ]

    days_rel = max((date.today() - buyer.relationship_since).days, 30)
    years_rel = days_rel / 365.25

    req = BuyerBriefRequest(
        buyer_id=buyer.buyer_id,
        company_name=buyer.company_name,
        contact_name=buyer.contact_name,
        reliability_tier=buyer.reliability_tier,
        on_time_rate_pct=buyer.on_time_payment_rate * 100.0,
        relationship_years=years_rel,
        total_invoices_count=len(invoices),
        open_invoices_count=len(open_invoices),
        total_outstanding_inr=f"{total_outstanding:,.2f}",
        recent_interactions=interactions,
        active_promises=promises,
        recent_audits=audits,
    )

    result = await briefer.brief(req)

    return SuccessEnvelope(
        data=BuyerBriefOut(
            buyer_id=buyer.buyer_id,
            company_name=buyer.company_name,
            contact_name=buyer.contact_name,
            summary=result.summary,
            spoken_summary=result.spoken_summary,
            risk_assessment=result.risk_assessment,
            recommended_action=result.recommended_action,
            total_outstanding_inr=f"₹{total_outstanding:,.0f}",
            open_invoices_count=len(open_invoices),
            model=result.model,
        )
    )
