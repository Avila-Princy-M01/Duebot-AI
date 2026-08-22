"""Persist a state-machine transition atomically with its audit row.

If the audit insert fails, the invoice state is not updated (same transaction).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.states import Actor, InvoiceState, TransitionEvent, transition
from backend.models.audit_log import AuditLog
from backend.models.invoice import Invoice


@dataclass
class InvoiceRef:
    """Adapter so ORM invoices satisfy ``HasInvoiceState``."""

    invoice_id: str
    state: InvoiceState


async def apply_transition(
    session: AsyncSession,
    invoice: Invoice,
    event: TransitionEvent,
    *,
    reasoning: str,
    actor: Actor = "agent",
    metadata: dict[str, object] | None = None,
    occurred_at: datetime | None = None,
) -> Invoice:
    """Apply ``transition()`` and persist audit + new state in one flush.

    Args:
        session: Open unit of work. Caller commits.
        invoice: ORM invoice (mutated).
        event: Deterministic trigger.
        reasoning: Merchant-readable explanation.
        actor: agent | human | system.
        metadata: Extra audit JSON (event name is always added).
        occurred_at: Optional clock.

    Returns:
        The same invoice instance with ``state`` updated.
    """
    result = transition(
        InvoiceRef(invoice_id=invoice.invoice_id, state=InvoiceState(invoice.state)),
        event,
        reasoning=reasoning,
        actor=actor,
        metadata=metadata,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    payload = dict(result.audit_entry.metadata)
    payload["event"] = result.audit_entry.event.value
    session.add(
        AuditLog(
            invoice_id=result.audit_entry.invoice_id,
            from_state=result.audit_entry.from_state.value,
            to_state=result.audit_entry.to_state.value,
            actor=result.audit_entry.actor,
            occurred_at=result.audit_entry.occurred_at,
            reasoning_summary=result.audit_entry.reasoning_summary,
            extra_metadata=payload,
        )
    )
    invoice.state = result.new_state.value
    if result.new_state is InvoiceState.OPTED_OUT:
        invoice.opted_out = True
    if result.new_state is InvoiceState.DISPUTED:
        invoice.status = "disputed"
    if result.new_state is InvoiceState.RECOVERED:
        invoice.status = "paid"
        if invoice.paid_date is None:
            invoice.paid_date = (occurred_at or datetime.now(UTC)).date()
        invoice.amount_paid = invoice.total_amount
        invoice.days_overdue = 0
    await session.flush()
    return invoice


async def next_attempt_number(session: AsyncSession, invoice_id: str) -> int:
    """Return the next outbound attempt number for idempotency keys."""
    from sqlalchemy import func

    from backend.models.interaction import Interaction

    count_result = await session.execute(
        select(func.coalesce(func.max(Interaction.attempt_number), 0)).where(
            Interaction.invoice_id == invoice_id,
            Interaction.direction == "outbound",
        )
    )
    current = int(count_result.scalar_one())
    return current + 1
