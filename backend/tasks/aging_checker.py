"""Periodic aging scan: CREATED → OVERDUE when due_date has passed."""

from __future__ import annotations

from datetime import UTC, date, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.aging import days_overdue
from backend.engine.risk_tier import risk_tier
from backend.engine.states import InvoiceState, TransitionEvent
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.tasks.lifecycle import apply_transition

logger = structlog.get_logger("duebot.aging_checker")

AGING_BATCH_SIZE = 500


async def run_aging_check(session: AsyncSession, *, as_of: date | None = None) -> int:
    """Advance overdue CREATED invoices. Returns how many transitioned."""
    today = as_of or date.today()
    result = await session.execute(
        select(Invoice, Buyer)
        .join(Buyer, Buyer.buyer_id == Invoice.buyer_id)
        .where(Invoice.state == InvoiceState.CREATED.value)
        .limit(AGING_BATCH_SIZE)
    )
    moved = 0
    for invoice, buyer in result.all():
        overdue = days_overdue(invoice.due_date, today)
        invoice.days_overdue = overdue
        invoice.risk_tier = risk_tier(buyer.reliability_tier, overdue).value
        if overdue <= 0:
            continue
        invoice.status = "overdue"
        await apply_transition(
            session,
            invoice,
            TransitionEvent.AGED,
            reasoning=f"due_date {invoice.due_date.isoformat()} is before {today.isoformat()}",
            actor="system",
            occurred_at=datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC),
        )
        moved += 1
    logger.info("aging_check_complete", moved=moved)
    return moved
