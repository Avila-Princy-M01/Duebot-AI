"""Seed Postgres from the synthetic generator. No placeholder fixture data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.csv_mapper import (
    initial_state_for_status,
    parse_optional_date,
)
from backend.data.generator import BuyerMessage, DueBotDataGenerator
from backend.logging_util import mask_email, mask_phone
from backend.models.audit_log import AuditLog
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.models.promise import Promise

logger = structlog.get_logger("duebot.seed")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


async def seed_from_generator(
    session: AsyncSession,
    *,
    num_invoices: int = 260,
    seed: int = 42,
) -> dict[str, int]:
    """Generate a reproducible batch and insert it.

    Returns:
        Counts of rows inserted per table.
    """
    gen = DueBotDataGenerator(seed=seed)
    gen.run(num_invoices=num_invoices)
    logger.info(
        "seed_start",
        merchants=len(gen.merchants),
        buyers=len(gen.buyers),
        invoices=len(gen.invoices),
        messages=len(gen.messages),
    )

    from sqlalchemy import delete

    # Clear existing synthetic rows for an idempotent seed operation.
    # Promise must be deleted first: it holds foreign keys into both
    # interactions and invoices, so removing those first would violate them.
    await session.execute(delete(Promise))
    await session.execute(delete(AuditLog))
    await session.execute(delete(Interaction))
    await session.execute(delete(Invoice))
    await session.execute(delete(Buyer))
    await session.execute(delete(Merchant))

    inbound_by_invoice: set[str] = {m.invoice_id for m in gen.messages if m.direction == "inbound"}

    for merch in gen.merchants:
        session.add(
            Merchant(
                merchant_id=merch.merchant_id,
                business_name=merch.business_name,
                business_type=merch.business_type,
                gstin=merch.gstin,
                city=merch.city,
                state_code=merch.state_code,
                onboarded_date=date.fromisoformat(merch.onboarded_date),
            )
        )
    await session.flush()

    for buyer in gen.buyers:
        logger.debug(
            "seed_buyer",
            buyer_id=buyer.buyer_id,
            phone=mask_phone(buyer.phone),
            email=mask_email(buyer.email),
        )
        session.add(
            Buyer(
                buyer_id=buyer.buyer_id,
                merchant_id=buyer.merchant_id,
                company_name=buyer.company_name,
                contact_name=buyer.contact_name,
                phone=buyer.phone,
                email=buyer.email,
                gstin=buyer.gstin,
                reliability_tier=buyer.reliability_tier,
                on_time_payment_rate=buyer.on_time_payment_rate,
                relationship_since=date.fromisoformat(buyer.relationship_since),
            )
        )
    await session.flush()

    for idx, inv in enumerate(gen.invoices):
        state = initial_state_for_status(inv.status, inv.invoice_id in inbound_by_invoice)
        opted_out = inv.edge_case == "opt_out_mid_sequence"
        if opted_out:
            from backend.engine.states import InvoiceState

            state = InvoiceState.OPTED_OUT
        session.add(
            Invoice(
                invoice_id=inv.invoice_id,
                merchant_id=inv.merchant_id,
                buyer_id=inv.buyer_id,
                invoice_number=inv.invoice_number,
                issue_date=date.fromisoformat(inv.issue_date),
                due_date=date.fromisoformat(inv.due_date),
                payment_terms_days=inv.payment_terms_days,
                subtotal_amount=Decimal(str(inv.subtotal_amount)),
                gst_rate=inv.gst_rate,
                gst_amount=Decimal(str(inv.gst_amount)),
                total_amount=Decimal(str(inv.total_amount)),
                currency=inv.currency,
                status=inv.status,
                amount_paid=Decimal(str(inv.amount_paid)),
                paid_date=parse_optional_date(inv.paid_date),
                days_overdue=inv.days_overdue,
                risk_tier=inv.risk_tier,
                payment_link_id=inv.payment_link_id,
                state=state.value,
                opted_out=opted_out,
                edge_case=inv.edge_case,
                would_have_paid_without_intervention=inv.would_have_paid_without_intervention,
                promise_outcome=inv.promise_outcome,
                split=inv.split,
                notes=inv.notes or None,
            )
        )

        # Seed realistic audit trail entries with deterministic minute/second jitter
        inv_created_at = _dt(f"{inv.issue_date}T09:{(idx * 3) % 60:02d}:{(idx * 7) % 60:02d}")
        session.add(
            AuditLog(
                invoice_id=inv.invoice_id,
                from_state="created",
                to_state="created",
                actor="system",
                occurred_at=inv_created_at,
                reasoning_summary="invoice ingested into receivables ledger",
                extra_metadata={"event": "invoice_created"},
            )
        )
        if state.value != "created":
            due_dt = _dt(f"{inv.due_date}T10:{(idx * 5) % 60:02d}:{(idx * 11) % 60:02d}")
            session.add(
                AuditLog(
                    invoice_id=inv.invoice_id,
                    from_state="created",
                    to_state="overdue",
                    actor="agent",
                    occurred_at=due_dt,
                    reasoning_summary="invoice passed due date with outstanding balance",
                    extra_metadata={"event": "aged"},
                )
            )
            if state.value in (
                "nudged",
                "replied",
                "promised",
                "disputed",
                "opted_out",
                "recovered",
            ):
                nudge_offset = timedelta(
                    days=min(max(inv.days_overdue, 1), 5),
                    hours=(idx % 6),
                    minutes=(idx * 7) % 60,
                )
                nudge_dt = due_dt + nudge_offset
                session.add(
                    AuditLog(
                        invoice_id=inv.invoice_id,
                        from_state="overdue",
                        to_state="nudged",
                        actor="agent",
                        occurred_at=nudge_dt,
                        reasoning_summary=(
                            "automated WhatsApp payment reminder sent with Razorpay link"
                        ),
                        extra_metadata={"event": "nudge_sent", "attempt_number": 1},
                    )
                )
    await session.flush()

    # Synthetic message timestamps directly from generator timeline
    attempt_by_invoice: dict[str, int] = {}
    # Latest promise-bearing inbound reply per invoice, so each Promise row can
    # cite the exact interaction its date was extracted from.
    promise_sources: dict[str, tuple[UUID, str]] = {}
    for msg in gen.messages:
        if msg.direction == "outbound":
            attempt_by_invoice[msg.invoice_id] = attempt_by_invoice.get(msg.invoice_id, 0) + 1
            attempt = attempt_by_invoice[msg.invoice_id]
        else:
            attempt = attempt_by_invoice.get(msg.invoice_id, 1)

        msg_sent_at = _dt(msg.timestamp)

        interaction_id = uuid4()
        if msg.direction == "inbound" and msg.intent_label == "promise" and msg.promised_date:
            promise_sources[msg.invoice_id] = (interaction_id, msg.promised_date)

        session.add(
            Interaction(
                id=interaction_id,
                invoice_id=msg.invoice_id,
                buyer_id=msg.buyer_id,
                channel=msg.channel,
                direction=msg.direction,
                sent_at=msg_sent_at,
                message_text=msg.message_text,
                intent_label=msg.intent_label,
                confidence=None if msg.direction == "outbound" else 0.9,
                delivery_status="delivered",
                attempt_number=attempt,
            )
        )

    await session.flush()

    # Promise-to-pay rows, derived from the promise replies inserted above.
    # Only invoices with a tracked outcome qualify: the status CHECK excludes
    # "none", and an ambiguous reply must never yield a promise -- abstaining
    # there is the behaviour the reply-parser eval measures.
    invoice_by_id = {inv.invoice_id: inv for inv in gen.invoices}
    promises_created = 0
    for invoice_id, (source_id, promised_date) in promise_sources.items():
        gen_inv = invoice_by_id.get(invoice_id)
        if gen_inv is None or gen_inv.promise_outcome not in ("pending", "kept", "broken"):
            continue

        # Resolved on the date the outcome became knowable: payment arrival for a
        # kept promise (or promised date fallback), the promised date itself for one that lapsed.
        # A pending promise is still inside its grace window and stays unresolved.
        resolved_at: datetime | None = None
        if gen_inv.promise_outcome == "kept":
            kept_date = gen_inv.paid_date or promised_date
            resolved_at = _dt(f"{kept_date}T12:00:00")
        elif gen_inv.promise_outcome == "broken":
            resolved_at = _dt(f"{promised_date}T12:00:00")

        # The synthetic reply parser extracts a promised date, not a specific amount.
        # Storing None honestly reflects what was extracted from the reply text.
        session.add(
            Promise(
                id=uuid4(),
                invoice_id=invoice_id,
                source_interaction_id=source_id,
                promised_date=date.fromisoformat(promised_date),
                promised_amount=None,
                # Matches the inbound interaction confidence set above and
                # satisfies the CHECK (confidence >= 0.7) auto-log threshold.
                confidence=0.9,
                status=gen_inv.promise_outcome,
                resolved_at=resolved_at,
            )
        )
        promises_created += 1

    await session.flush()
    return {
        "merchants": len(gen.merchants),
        "buyers": len(gen.buyers),
        "invoices": len(gen.invoices),
        "messages": len(gen.messages),
        "promises": promises_created,
    }


__all__ = ["seed_from_generator", "BuyerMessage"]

