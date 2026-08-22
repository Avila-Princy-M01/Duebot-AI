"""Apply a payment-confirmed webhook to any non-terminal invoice that allows it."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.states import InvoiceState, TransitionEvent, is_valid_transition
from backend.models.invoice import Invoice
from backend.models.promise import Promise
from backend.tasks.lifecycle import apply_transition


async def confirm_payment(session: AsyncSession, invoice: Invoice) -> Invoice:
    """Mark recovered if the graph allows PAYMENT_CONFIRMED from the current state."""
    state = InvoiceState(invoice.state)
    if not is_valid_transition(state, TransitionEvent.PAYMENT_CONFIRMED):
        if state is InvoiceState.RECOVERED:
            return invoice
        return invoice
    now = datetime.now(UTC)
    result = await apply_transition(
        session,
        invoice,
        TransitionEvent.PAYMENT_CONFIRMED,
        reasoning="Razorpay payment link marked paid",
        actor="system",
        occurred_at=now,
    )
    promises = await session.execute(
        select(Promise).where(Promise.invoice_id == invoice.invoice_id, Promise.status == "pending")
    )
    for promise in promises.scalars():
        promise.status = "kept"
        promise.resolved_at = now
        invoice.promise_outcome = "kept"
    return result
