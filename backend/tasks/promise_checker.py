"""Promise date passed → REMINDED; grace elapsed unpaid → ESCALATED."""

from __future__ import annotations

from datetime import UTC, date, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.scheduler import PROMISE_BREAK_GRACE_DAYS
from backend.engine.states import InvoiceState, TransitionEvent
from backend.models.invoice import Invoice
from backend.models.promise import Promise
from backend.tasks.lifecycle import apply_transition

logger = structlog.get_logger("duebot.promise_checker")


async def run_promise_check(session: AsyncSession, *, as_of: date | None = None) -> int:
    """Advance promised/reminded invoices. Returns transitions applied."""
    today = as_of or date.today()
    now = datetime.now(UTC)
    moved = 0

    promised = await session.execute(
        select(Invoice, Promise)
        .join(Promise, Promise.invoice_id == Invoice.invoice_id)
        .where(
            Invoice.state == InvoiceState.PROMISED.value,
            Promise.status == "pending",
        )
    )
    for invoice, promise in promised.all():
        if promise.promised_date > today:
            continue
        await apply_transition(
            session,
            invoice,
            TransitionEvent.PROMISE_DATE_PASSED,
            reasoning=f"promised_date {promise.promised_date.isoformat()} has passed unpaid",
            actor="system",
            occurred_at=now,
        )
        moved += 1

    reminded = await session.execute(
        select(Invoice, Promise)
        .join(Promise, Promise.invoice_id == Invoice.invoice_id)
        .where(
            Invoice.state == InvoiceState.REMINDED.value,
            Promise.status == "pending",
        )
    )
    for invoice, promise in reminded.all():
        broken_on = promise.promised_date.toordinal() + PROMISE_BREAK_GRACE_DAYS
        if today.toordinal() < broken_on:
            continue
        promise.status = "broken"
        promise.resolved_at = now
        invoice.promise_outcome = "broken"
        await apply_transition(
            session,
            invoice,
            TransitionEvent.PROMISE_BROKEN,
            reasoning=(
                f"promise broken: unpaid {PROMISE_BREAK_GRACE_DAYS} days after "
                f"{promise.promised_date.isoformat()}"
            ),
            actor="system",
            occurred_at=now,
        )
        await apply_transition(
            session,
            invoice,
            TransitionEvent.ROUTED_TO_HUMAN,
            reasoning="broken promise assigned to merchant review",
            actor="system",
            occurred_at=now,
        )
        moved += 1

    logger.info("promise_check_complete", moved=moved)
    return moved
