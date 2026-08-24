"""Send pending nudges: policy check → log outbound → send → NUDGE_SENT."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engine.policy import PolicyDecision, can_contact
from backend.engine.states import InvoiceState, TransitionEvent
from backend.exceptions import PolicyBlockedError
from backend.integrations.razorpay import RazorpayClient
from backend.integrations.whatsapp import WhatsAppSender
from backend.llm.message_drafter import MessageDrafter
from backend.llm.types import DraftRequest
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.tasks.lifecycle import apply_transition, next_attempt_number

logger = structlog.get_logger("duebot.nudge_executor")

NUDGEABLE_STATES = frozenset(
    {InvoiceState.OVERDUE.value, InvoiceState.NUDGED.value, InvoiceState.REPLIED.value}
)


async def _history(session: AsyncSession, invoice_id: str) -> list[Interaction]:
    result = await session.execute(select(Interaction).where(Interaction.invoice_id == invoice_id))
    return list(result.scalars().all())


async def preview_nudge(
    session: AsyncSession,
    invoice: Invoice,
    buyer: Buyer,
    drafter: MessageDrafter,
    razorpay: RazorpayClient,
    *,
    as_of: datetime | None = None,
) -> tuple[PolicyDecision, str, str]:
    """Policy + draft without sending. Returns (decision, body, payment_link)."""
    now = as_of or datetime.now(UTC)
    history = await _history(session, invoice.invoice_id)
    decision = can_contact(invoice_as_policy(invoice), history, as_of=now)
    link_id = invoice.payment_link_id
    if not link_id:
        created = razorpay.create_payment_link(
            amount_inr=invoice.total_amount - invoice.amount_paid,
            invoice_number=invoice.invoice_number,
            customer_name=buyer.contact_name,
        )
        link_id = created.short_url
        invoice.payment_link_id = created.payment_link_id
    else:
        link_id = f"https://rzp.io/l/{link_id[-8:]}"
    amount = f"{(invoice.total_amount - invoice.amount_paid):,.0f}"
    drafted = await drafter.draft(
        DraftRequest(
            buyer_first_name=buyer.contact_name.split()[0],
            invoice_number=invoice.invoice_number,
            amount_inr=amount,
            due_date=invoice.due_date.isoformat(),
            days_overdue=invoice.days_overdue,
            payment_link=link_id,
        )
    )
    return decision, drafted.body, link_id


def invoice_as_policy(invoice: Invoice) -> SimpleNamespace:
    """Wrap an ORM invoice so ``state`` is an ``InvoiceState`` enum."""
    return SimpleNamespace(
        invoice_id=invoice.invoice_id,
        state=InvoiceState(invoice.state),
        opted_out=invoice.opted_out,
        due_date=invoice.due_date,
    )


async def execute_nudge(
    session: AsyncSession,
    invoice: Invoice,
    buyer: Buyer,
    *,
    drafter: MessageDrafter,
    razorpay: RazorpayClient,
    whatsapp: WhatsAppSender,
    dry_run: bool = False,
    as_of: datetime | None = None,
) -> tuple[bool, PolicyDecision, str]:
    """Run one nudge cycle. Log-before-send is mandatory when not dry_run."""
    now = as_of or datetime.now(UTC)
    decision, body, _link = await preview_nudge(
        session, invoice, buyer, drafter, razorpay, as_of=now
    )
    if dry_run:
        return False, decision, body
    if not decision.allowed:
        if "contact cap" in decision.reason and invoice.state == InvoiceState.NUDGED.value:
            await apply_transition(
                session,
                invoice,
                TransitionEvent.CONTACT_CAP_REACHED,
                reasoning=decision.reason,
                actor="system",
                metadata={"contacts_this_week": decision.contacts_this_week},
            )
        raise PolicyBlockedError(decision.reason)

    existing_pending = await session.execute(
        select(Interaction).where(
            Interaction.invoice_id == invoice.invoice_id,
            Interaction.direction == "outbound",
            Interaction.delivery_status == "pending",
        )
    )
    if existing_pending.scalar_one_or_none() is not None:
        logger.info("nudge_idempotent_skip_pending", invoice_id=invoice.invoice_id)
        return False, decision, body

    attempt = await next_attempt_number(session, invoice.invoice_id)
    existing = await session.execute(
        select(Interaction).where(
            Interaction.invoice_id == invoice.invoice_id,
            Interaction.attempt_number == attempt,
            Interaction.direction == "outbound",
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("nudge_idempotent_skip", invoice_id=invoice.invoice_id, attempt=attempt)
        return False, decision, body

    interaction = Interaction(
        id=uuid4(),
        invoice_id=invoice.invoice_id,
        buyer_id=buyer.buyer_id,
        channel="whatsapp",
        direction="outbound",
        sent_at=now,
        message_text=body,
        intent_label="nudge",
        confidence=None,
        delivery_status="pending",
        attempt_number=attempt,
    )
    session.add(interaction)
    await session.flush()

    status = await whatsapp.send(
        policy=decision,
        interaction_id=interaction.id,
        invoice_id=invoice.invoice_id,
        to_phone=buyer.phone,
        body=body,
    )
    interaction.delivery_status = status

    if invoice.state == InvoiceState.OVERDUE.value:
        await apply_transition(
            session,
            invoice,
            TransitionEvent.NUDGE_SENT,
            reasoning="outbound nudge logged and sent",
            metadata={"attempt_number": attempt, "interaction_id": str(interaction.id)},
        )
    else:
        from backend.models.audit_log import AuditLog

        session.add(
            AuditLog(
                invoice_id=invoice.invoice_id,
                from_state=invoice.state,
                to_state=invoice.state,
                actor="agent",
                occurred_at=now,
                reasoning_summary=f"outbound follow-up WhatsApp nudge sent (attempt #{attempt})",
                extra_metadata={
                    "event": "nudge_sent",
                    "attempt_number": attempt,
                    "interaction_id": str(interaction.id),
                },
            )
        )
        await session.flush()
    return True, decision, body


async def run_nudge_cycle(
    session: AsyncSession,
    *,
    drafter: MessageDrafter,
    razorpay: RazorpayClient,
    whatsapp: WhatsAppSender,
) -> int:
    """Nudge all currently nudgeable invoices that pass policy."""
    result = await session.execute(
        select(Invoice, Buyer)
        .join(Buyer, Buyer.buyer_id == Invoice.buyer_id)
        .where(Invoice.state.in_(NUDGEABLE_STATES))
    )
    sent = 0
    for invoice, buyer in result.all():
        try:
            did_send, _decision, _body = await execute_nudge(
                session, invoice, buyer, drafter=drafter, razorpay=razorpay, whatsapp=whatsapp
            )
        except PolicyBlockedError:
            continue
        if did_send:
            sent += 1
    logger.info("nudge_cycle_complete", sent=sent)
    return sent
