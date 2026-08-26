"""Simulated WhatsApp inbox + inbound reply injection for the demo."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db, reply_parser
from backend.engine.states import InvalidTransitionError
from backend.exceptions import NotFoundError
from backend.llm.reply_parser import ReplyParser
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.schemas.common import SuccessEnvelope
from backend.tasks.reply_processor import process_reply

router = APIRouter(prefix="/inbox", tags=["inbox"])


class InboxMessageOut(BaseModel):
    """Simulated inbox row."""

    interaction_id: str
    invoice_id: str
    to_phone_masked: str
    body: str
    sent_at: str
    direction: str


class InboundReplyBody(BaseModel):
    """Demo: inject a buyer reply for an invoice."""

    invoice_id: str
    text: str


@router.get("")
async def list_inbox(
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[InboxMessageOut]]:
    """Return all interactions from the database as inbox rows."""
    result = await session.execute(
        select(Interaction)
        .where(Interaction.channel == "whatsapp")
        .order_by(Interaction.sent_at.desc())
        .limit(200)
    )
    rows = result.scalars().all()
    data = [
        InboxMessageOut(
            interaction_id=str(r.id),
            invoice_id=r.invoice_id,
            to_phone_masked=("inbound" if r.direction == "inbound" else "outbound"),
            body=r.message_text,
            sent_at=r.sent_at.isoformat(),
            direction=r.direction,
        )
        for r in rows
    ]
    return SuccessEnvelope(data=data)


@router.post("/reply")
async def inject_reply(
    body: InboundReplyBody,
    session: AsyncSession = Depends(get_db),
    parser: ReplyParser = Depends(reply_parser),
) -> SuccessEnvelope[dict[str, str]]:
    """Inject a buyer reply (demo / simulated inbound webhook)."""
    invoice = await session.get(Invoice, body.invoice_id)
    if invoice is None:
        raise NotFoundError(f"invoice {body.invoice_id} not found")
    buyer = await session.get(Buyer, invoice.buyer_id)
    if buyer is None:
        raise NotFoundError(f"buyer {invoice.buyer_id} not found")

    try:
        await process_reply(session, invoice, buyer, body.text, parser=parser)
    except InvalidTransitionError:
        note = f"Invoice is in state '{invoice.state}' — repeat automated transitions locked."
        return SuccessEnvelope(
            data={
                "invoice_id": invoice.invoice_id,
                "state": invoice.state,
                "note": note,
            }
        )

    return SuccessEnvelope(
        data={
            "invoice_id": invoice.invoice_id,
            "state": invoice.state,
        }
    )
