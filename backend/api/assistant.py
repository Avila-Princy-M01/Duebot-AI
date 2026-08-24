"""Interactive portfolio and buyer assistant routes."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import duebot_assistant, get_db
from backend.llm.assistant import AssistantContext, DueBotAssistant
from backend.models.audit_log import AuditLog
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.promise import Promise
from backend.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from backend.schemas.common import SuccessEnvelope

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask")
async def ask_assistant(
    body: AssistantQueryRequest,
    session: AsyncSession = Depends(get_db),
    assistant: DueBotAssistant = Depends(duebot_assistant),
) -> SuccessEnvelope[AssistantQueryResponse]:
    """Answer merchant natural language/voice queries grounded in live database facts."""
    # 1. Invoices & Aging metrics
    inv_rows = await session.execute(select(Invoice))
    all_invoices = list(inv_rows.scalars().all())

    overdue_invoices = [inv for inv in all_invoices if inv.status in ("overdue", "partial")]
    total_at_risk = sum(
        (inv.total_amount - inv.amount_paid for inv in overdue_invoices),
        Decimal("0"),
    )

    b0_30 = len([inv for inv in overdue_invoices if 0 <= inv.days_overdue <= 30])
    b31_60 = len([inv for inv in overdue_invoices if 31 <= inv.days_overdue <= 60])
    b61_90 = len([inv for inv in overdue_invoices if 61 <= inv.days_overdue <= 90])
    b90_plus = len([inv for inv in overdue_invoices if inv.days_overdue > 90])

    aging_str = (
        f"0-30 days: {b0_30}, 31-60 days: {b31_60}, "
        f"61-90 days: {b61_90}, 90+ days: {b90_plus}"
    )

    # 2. Buyers summary
    buyer_rows = await session.execute(select(Buyer).limit(50))
    all_buyers = list(buyer_rows.scalars().all())
    buyers_summary = [
        f"{b.company_name} (ID: {b.buyer_id}, Contact: {b.contact_name}, "
        f"Tier: {b.reliability_tier}, On-time: {b.on_time_payment_rate * 100:.0f}%)"
        for b in all_buyers
    ]

    # 3. Active promises
    prom_rows = await session.execute(
        select(Promise).order_by(Promise.promised_date.desc()).limit(5)
    )
    promises = [
        f"Invoice {p.invoice_id}: promised {p.promised_date} (status: {p.status})"
        for p in prom_rows.scalars().all()
    ]

    # 4. Recent audits
    audit_rows = await session.execute(
        select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(8)
    )
    audits = [
        f"{a.invoice_id} ({a.occurred_at.strftime('%b %d')}): "
        f"{a.from_state}->{a.to_state} ({a.reasoning_summary})"
        for a in audit_rows.scalars().all()
    ]

    # 5. Check specific buyer / invoice context
    specific_buyer_ctx: str | None = None
    target_buyer_id = body.buyer_id
    if not target_buyer_id:
        # Check if buyer name was mentioned in query
        q_low = body.query.lower()
        for b in all_buyers:
            if b.company_name.lower() in q_low or b.buyer_id.lower() in q_low:
                target_buyer_id = b.buyer_id
                break

    if target_buyer_id:
        b_obj = await session.get(Buyer, target_buyer_id)
        if b_obj:
            b_invs = [inv for inv in all_invoices if inv.buyer_id == target_buyer_id]
            b_open = [inv for inv in b_invs if inv.status in ("overdue", "partial", "pending")]
            b_out = sum((inv.total_amount - inv.amount_paid for inv in b_open), Decimal("0"))

            # Recent interactions for this buyer
            b_ints = await session.execute(
                select(Interaction)
                .where(Interaction.buyer_id == target_buyer_id)
                .order_by(Interaction.sent_at.desc())
                .limit(4)
            )
            int_texts = [
                f"{i.direction.upper()}: {i.message_text[:80]}"
                for i in b_ints.scalars().all()
            ]

            rate_val = b_obj.on_time_payment_rate * 100
            specific_buyer_ctx = (
                f"Company: {b_obj.company_name} (ID: {b_obj.buyer_id})\n"
                f"Contact: {b_obj.contact_name}, Phone: {b_obj.phone}, Email: {b_obj.email}\n"
                f"Reliability: {b_obj.reliability_tier}, On-time Rate: {rate_val:.1f}%\n"
                f"Open Invoices: {len(b_open)} (Total Outstanding: INR {b_out:,.0f})\n"
                f"Recent Messages:\n" + "\n".join(f"  * {t}" for t in int_texts)
            )

    specific_inv_ctx: str | None = None
    target_inv_id = body.invoice_id
    if not target_inv_id:
        q_low = body.query.lower()
        for inv in all_invoices:
            if (
                inv.invoice_id.lower() in q_low
                or inv.invoice_number.lower() in q_low
            ):
                target_inv_id = inv.invoice_id
                break

    if target_inv_id:
        inv_obj = await session.get(Invoice, target_inv_id)
        if inv_obj:
            specific_inv_ctx = (
                f"Invoice Number: {inv_obj.invoice_number} (ID: {inv_obj.invoice_id})\n"
                f"Total: INR {inv_obj.total_amount:,.0f}, Paid: INR {inv_obj.amount_paid:,.0f}\n"
                f"Status: {inv_obj.status}, Current State: {inv_obj.state}, "
                f"Days Overdue: {inv_obj.days_overdue}, Risk Tier: {inv_obj.risk_tier}\n"
                f"Payment Link: {inv_obj.payment_link_id}"
            )

    ctx = AssistantContext(
        query=body.query,
        total_invoices_count=len(all_invoices),
        overdue_count=len(overdue_invoices),
        amount_at_risk_inr=f"{total_at_risk:,.0f}",
        aging_summary=aging_str,
        buyers_summary=buyers_summary,
        active_promises=promises,
        recent_audits=audits,
        specific_buyer_context=specific_buyer_ctx,
        specific_invoice_context=specific_inv_ctx,
    )

    ans = await assistant.answer(ctx)

    return SuccessEnvelope(
        data=AssistantQueryResponse(
            answer=ans.answer,
            spoken_answer=ans.spoken_answer,
            category=ans.category,
            suggested_action=ans.suggested_action,
            model=ans.model,
        )
    )
