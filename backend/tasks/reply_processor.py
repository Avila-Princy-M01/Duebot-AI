"""Inbound reply → structured intent → state transition. LLM never chooses the event."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.policy import event_for_parsed_intent
from backend.engine.states import InvoiceState, TransitionEvent
from backend.llm.reply_parser import ReplyParser
from backend.llm.types import ParsedIntent
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.promise import Promise
from backend.tasks.lifecycle import apply_transition

logger = structlog.get_logger("duebot.reply_processor")


async def process_reply(
    session: AsyncSession,
    invoice: Invoice,
    buyer: Buyer,
    reply_text: str,
    *,
    parser: ReplyParser,
    parsed: ParsedIntent | None = None,
    as_of: datetime | None = None,
) -> Invoice:
    """Log inbound message, parse (or use injected parse), then transition.

    ``parsed`` is injectable so tests and the eval harness never need a live LLM.
    """
    now = as_of or datetime.now(UTC)
    if invoice.state == InvoiceState.CREATED.value:
        await apply_transition(
            session,
            invoice,
            TransitionEvent.AGED,
            reasoning="invoice past due date",
            occurred_at=now,
        )
    if invoice.state == InvoiceState.OVERDUE.value:
        await apply_transition(
            session,
            invoice,
            TransitionEvent.NUDGE_SENT,
            reasoning="outbound nudge sent before reply received",
            occurred_at=now,
        )
    if invoice.state == InvoiceState.NUDGED.value:
        await apply_transition(
            session,
            invoice,
            TransitionEvent.REPLY_RECEIVED,
            reasoning="inbound buyer message received",
            occurred_at=now,
        )

    intent = parsed if parsed is not None else await parser.parse(reply_text, as_of=now.date())
    event = event_for_parsed_intent(intent.intent, intent.confidence)

    inbound = Interaction(
        id=uuid4(),
        invoice_id=invoice.invoice_id,
        buyer_id=buyer.buyer_id,
        channel="whatsapp",
        direction="inbound",
        sent_at=now,
        message_text=reply_text,
        intent_label=intent.intent.value,
        confidence=intent.confidence,
        delivery_status="delivered",
        attempt_number=0,
    )
    session.add(inbound)
    await session.flush()

    if event is TransitionEvent.PROMISE_LOGGED:
        if intent.promised_date is None:
            event = TransitionEvent.NEEDS_HUMAN
            intent.reasoning = "promise intent without a date — routed to human"
        else:
            session.add(
                Promise(
                    invoice_id=invoice.invoice_id,
                    source_interaction_id=inbound.id,
                    promised_date=intent.promised_date,
                    promised_amount=intent.promised_amount,
                    confidence=intent.confidence,
                    status="pending",
                )
            )
            invoice.promise_outcome = "pending"

    await apply_transition(
        session,
        invoice,
        event,
        reasoning=intent.reasoning,
        metadata={
            "intent": intent.intent.value,
            "confidence": intent.confidence,
        },
        occurred_at=now,
    )
    if event is TransitionEvent.DISPUTE_RAISED:
        await apply_transition(
            session,
            invoice,
            TransitionEvent.ROUTED_TO_HUMAN,
            reasoning="disputed invoices are immediately escalated to a human",
            actor="system",
        )
    if event is TransitionEvent.OPT_OUT_RECEIVED:
        await apply_transition(
            session,
            invoice,
            TransitionEvent.OPT_OUT_FINALIZED,
            reasoning="opt-out acknowledged; sequence terminated",
            actor="system",
        )
    return invoice


async def process_unparsed_inbounds(
    session: AsyncSession,
    parser: ReplyParser,
) -> int:
    """Find inbound rows with no confidence yet — used by the poll loop."""
    result = await session.execute(
        select(Interaction, Invoice, Buyer)
        .join(Invoice, Invoice.invoice_id == Interaction.invoice_id)
        .join(Buyer, Buyer.buyer_id == Invoice.buyer_id)
        .where(
            Interaction.direction == "inbound",
            Interaction.confidence.is_(None),
        )
    )
    count = 0
    for _interaction, invoice, buyer in result.all():
        await process_reply(session, invoice, buyer, _interaction.message_text, parser=parser)
        count += 1
    return count
