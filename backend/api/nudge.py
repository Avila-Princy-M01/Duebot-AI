"""Manual nudge trigger and preview."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db, message_drafter, razorpay_client, whatsapp_sender
from backend.engine.scheduler import next_action_at
from backend.engine.states import TransitionEvent
from backend.exceptions import NotFoundError
from backend.integrations.razorpay import RazorpayClient
from backend.integrations.whatsapp import WhatsAppSender
from backend.llm.message_drafter import MessageDrafter
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.schemas.common import SuccessEnvelope
from backend.schemas.nudge import NudgePreview, NudgeTriggerRequest, NudgeTriggerResult
from backend.tasks.nudge_executor import execute_nudge, invoice_as_policy, preview_nudge

router = APIRouter(prefix="/nudge", tags=["nudge"])


@router.get("/preview/{invoice_id}")
async def preview(
    invoice_id: str,
    session: AsyncSession = Depends(get_db),
    drafter: MessageDrafter = Depends(message_drafter),
    razorpay: RazorpayClient = Depends(razorpay_client),
) -> SuccessEnvelope[NudgePreview]:
    """Preview what would be sent. Never sends."""
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError(f"invoice {invoice_id} not found")
    buyer = await session.get(Buyer, invoice.buyer_id)
    if buyer is None:
        raise NotFoundError(f"buyer {invoice.buyer_id} not found")
    decision, body, _link = await preview_nudge(session, invoice, buyer, drafter, razorpay)
    history = list(
        (await session.execute(select(Interaction).where(Interaction.invoice_id == invoice_id)))
        .scalars()
        .all()
    )
    nxt = next_action_at(invoice_as_policy(invoice), history, as_of=datetime.now(UTC))
    return SuccessEnvelope(
        data=NudgePreview(
            invoice_id=invoice_id,
            allowed=decision.allowed,
            policy_reason=decision.reason,
            approaching_cap=decision.approaching_cap,
            contacts_this_week=decision.contacts_this_week,
            drafted_message=body,
            channel="whatsapp",
            next_action_at=nxt.isoformat() if nxt else None,
            current_state=invoice.state,
            target_event=TransitionEvent.NUDGE_SENT.value,
        )
    )


@router.post("/trigger")
async def trigger(
    body: NudgeTriggerRequest,
    dry_run: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    drafter: MessageDrafter = Depends(message_drafter),
    razorpay: RazorpayClient = Depends(razorpay_client),
    whatsapp: WhatsAppSender = Depends(whatsapp_sender),
) -> SuccessEnvelope[NudgeTriggerResult]:
    """Manually run one nudge cycle. ``dry_run=true`` stops before send."""
    invoice = await session.get(Invoice, body.invoice_id)
    if invoice is None:
        raise NotFoundError(f"invoice {body.invoice_id} not found")
    buyer = await session.get(Buyer, invoice.buyer_id)
    if buyer is None:
        raise NotFoundError(f"buyer {invoice.buyer_id} not found")
    sent, decision, text = await execute_nudge(
        session,
        invoice,
        buyer,
        drafter=drafter,
        razorpay=razorpay,
        whatsapp=whatsapp,
        dry_run=dry_run,
    )
    preview_body = NudgePreview(
        invoice_id=invoice.invoice_id,
        allowed=decision.allowed,
        policy_reason=decision.reason,
        approaching_cap=decision.approaching_cap,
        contacts_this_week=decision.contacts_this_week,
        drafted_message=text,
        channel="whatsapp",
        next_action_at=None,
        current_state=invoice.state,
        target_event=TransitionEvent.NUDGE_SENT.value,
    )
    return SuccessEnvelope(
        data=NudgeTriggerResult(
            invoice_id=invoice.invoice_id,
            dry_run=dry_run,
            sent=sent,
            preview=preview_body,
            new_state=invoice.state,
        )
    )
