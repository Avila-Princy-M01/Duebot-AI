"""Simulated WhatsApp inbox + inbound reply injection for the demo."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db, reply_parser
from backend.engine.states import InvalidTransitionError
from backend.exceptions import NotFoundError
from backend.integrations.whatsapp import INBOX, SimulatedMessage
from backend.llm.reply_parser import ReplyParser
from backend.models.buyer import Buyer
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
async def list_inbox() -> SuccessEnvelope[list[InboxMessageOut]]:
    """Process-local simulated WhatsApp inbox."""
    data = [
        InboxMessageOut(
            interaction_id=str(m.interaction_id),
            invoice_id=m.invoice_id,
            to_phone_masked=m.to_phone_masked,
            body=m.body,
            sent_at=m.sent_at.isoformat(),
            direction=m.direction,
        )
        for m in INBOX.messages
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
        note = (
            f"Invoice is in state '{invoice.state}' — repeat automated transitions locked."
        )
        return SuccessEnvelope(
            data={
                "invoice_id": invoice.invoice_id,
                "state": invoice.state,
                "note": note,
            }
        )

    INBOX.messages.append(
        SimulatedMessage(
            interaction_id=uuid4(),
            invoice_id=invoice.invoice_id,
            to_phone_masked="inbound",
            body=body.text,
            sent_at=datetime.now(UTC),
            direction="inbound",
        )
    )
    return SuccessEnvelope(data={"invoice_id": invoice.invoice_id, "state": invoice.state})
