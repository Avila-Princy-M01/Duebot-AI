"""Seed database from synthetic generator using real state machine engine replay."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.csv_mapper import (
    parse_optional_date,
)
from backend.data.generator import BuyerMessage, DueBotDataGenerator
from backend.engine.states import Actor, InvoiceState, TransitionEvent, transition
from backend.logging_util import mask_email, mask_phone
from backend.models.audit_log import AuditLog
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.models.promise import Promise
from backend.tasks.lifecycle import InvoiceRef

logger = structlog.get_logger("duebot.seed")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


async def _reset_demo_fixtures(session: AsyncSession) -> None:
    """Reset test demo fixtures for idempotent generator re-runs.

    Note: Application code never modifies or deletes rows from AuditLog.
    This reset is strictly a test/demo fixture teardown for local environments.
    """
    from sqlalchemy import delete

    # Promise must be deleted first: it holds foreign keys into both
    # interactions and invoices, so removing those first would violate them.
    await session.execute(delete(Promise))
    await session.execute(delete(AuditLog))
    await session.execute(delete(Interaction))
    await session.execute(delete(Invoice))
    await session.execute(delete(Buyer))
    await session.execute(delete(Merchant))


async def seed_from_generator(
    session: AsyncSession,
    *,
    num_invoices: int = 260,
    seed: int = 42,
) -> dict[str, int]:
    """Generate a reproducible batch and replay state machine transitions.

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

    await _reset_demo_fixtures(session)

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

    # Create Invoice entities initialised at CREATED
    orm_invoices: dict[str, Invoice] = {}
    for inv in gen.invoices:
        opted_out = inv.edge_case == "opt_out_mid_sequence"
        orm_inv = Invoice(
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
            state=InvoiceState.CREATED.value,
            opted_out=opted_out,
            edge_case=inv.edge_case,
            would_have_paid_without_intervention=inv.would_have_paid_without_intervention,
            promise_outcome=inv.promise_outcome,
            split=inv.split,
            notes=inv.notes or None,
        )
        session.add(orm_inv)
        orm_invoices[inv.invoice_id] = orm_inv
    await session.flush()

    # Synthetic message timestamps directly from generator timeline
    attempt_by_invoice: dict[str, int] = {}
    promise_sources: dict[str, tuple[UUID, str]] = {}
    inbound_msgs_by_invoice: dict[str, BuyerMessage] = {}
    outbound_msgs_by_invoice: dict[str, list[BuyerMessage]] = {}

    for msg in gen.messages:
        if msg.direction == "outbound":
            attempt_by_invoice[msg.invoice_id] = attempt_by_invoice.get(msg.invoice_id, 0) + 1
            attempt = attempt_by_invoice[msg.invoice_id]
            outbound_msgs_by_invoice.setdefault(msg.invoice_id, []).append(msg)
        else:
            attempt = attempt_by_invoice.get(msg.invoice_id, 1)
            inbound_msgs_by_invoice[msg.invoice_id] = msg

        msg_sent_at = _dt(msg.timestamp)
        interaction_id = uuid4()
        if msg.direction == "inbound" and msg.intent_label == "promise" and msg.promised_date:
            promise_sources[msg.invoice_id] = (interaction_id, msg.promised_date)

        confidence = None
        if msg.direction == "inbound":
            if msg.intent_label == "ambiguous":
                confidence = 0.45
            elif msg.intent_label == "dispute":
                confidence = 0.92
            elif msg.intent_label == "opt_out":
                confidence = 0.95
            elif msg.intent_label == "objection":
                confidence = 0.88
            else:
                confidence = 0.90

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
                confidence=confidence,
                delivery_status="delivered",
                attempt_number=attempt,
            )
        )

    await session.flush()

    # -----------------------------------------------------------------------
    # Pure State-Machine Engine Replay for Immutable Audit Log Generation
    # -----------------------------------------------------------------------
    def _record_step(
        orm_inv: Invoice,
        ref: InvoiceRef,
        event: TransitionEvent,
        *,
        reasoning: str,
        actor: Actor,
        metadata: dict[str, object] | None,
        occurred_at: datetime,
    ) -> None:
        res = transition(
            ref,
            event,
            reasoning=reasoning,
            actor=actor,
            metadata=metadata,
            occurred_at=occurred_at,
        )
        meta = dict(res.audit_entry.metadata)
        meta["event"] = res.audit_entry.event.value
        if "policy_version" not in meta:
            meta["policy_version"] = "v1.0.0"
        session.add(
            AuditLog(
                invoice_id=orm_inv.invoice_id,
                from_state=res.audit_entry.from_state.value,
                to_state=res.audit_entry.to_state.value,
                actor=res.audit_entry.actor,
                occurred_at=res.audit_entry.occurred_at,
                reasoning_summary=res.audit_entry.reasoning_summary,
                extra_metadata=meta,
            )
        )
        ref.state = res.new_state
        orm_inv.state = res.new_state.value

    for idx, inv in enumerate(gen.invoices):
        orm_inv = orm_invoices[inv.invoice_id]
        ref = InvoiceRef(invoice_id=inv.invoice_id, state=InvoiceState.CREATED)

        if inv.status == "draft":
            continue

        due_dt = _dt(f"{inv.due_date}T10:{(idx * 5) % 60:02d}:{(idx * 11) % 60:02d}")
        inbound = inbound_msgs_by_invoice.get(inv.invoice_id)
        outbound = outbound_msgs_by_invoice.get(inv.invoice_id, [])
        has_outbound = len(outbound) > 0
        is_opt_out = inv.edge_case == "opt_out_mid_sequence"
        is_ambiguous = inv.edge_case == "ambiguous_reply"
        is_dispute = inv.edge_case == "disputed_invoice" or inv.status == "disputed"

        # Step 1: Aging: CREATED -> OVERDUE
        _record_step(
            orm_inv,
            ref,
            TransitionEvent.AGED,
            reasoning=(
                f"Invoice reached due date ({inv.due_date}) with outstanding "
                f"balance of ₹{inv.total_amount:,.0f}; marked overdue."
            ),
            actor="system",
            metadata={"event": "aged", "due_date": str(inv.due_date)},
            occurred_at=due_dt,
        )

        # Self-cure payment without nudge
        if (
            inv.status == "paid"
            and not has_outbound
            and not inbound
            and inv.promise_outcome not in ("pending", "kept", "broken")
        ):
            paid_dt = _dt(f"{inv.paid_date or inv.due_date}T11:00:00")
            _record_step(
                orm_inv,
                ref,
                TransitionEvent.PAYMENT_CONFIRMED,
                reasoning=(
                    f"Razorpay webhook confirmed payment of ₹{inv.total_amount:,.0f} "
                    "without reminders."
                ),
                actor="system",
                metadata={
                    "event": "payment_confirmed",
                    "payment_link_id": inv.payment_link_id,
                    "amount": str(inv.total_amount),
                },
                occurred_at=paid_dt,
            )
            continue

        # Nudge step
        if has_outbound or inv.status in (
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
            _record_step(
                orm_inv,
                ref,
                TransitionEvent.NUDGE_SENT,
                reasoning=(
                    "Deterministic scheduler dispatched payment reminder with Razorpay link "
                    "via WhatsApp (attempt 1)."
                ),
                actor="agent",
                metadata={"event": "nudge_sent", "attempt_number": 1, "channel": "whatsapp"},
                occurred_at=nudge_dt,
            )

            # Payment after nudge without reply
            if (
                inv.status == "paid"
                and not inbound
                and inv.promise_outcome not in ("pending", "kept", "broken")
            ):
                paid_dt = _dt(f"{inv.paid_date or inv.due_date}T14:30:00")
                _record_step(
                    orm_inv,
                    ref,
                    TransitionEvent.PAYMENT_CONFIRMED,
                    reasoning=(
                        f"Razorpay webhook confirmed payment of ₹{inv.total_amount:,.0f} "
                        "after reminder."
                    ),
                    actor="system",
                    metadata={
                        "event": "payment_confirmed",
                        "payment_link_id": inv.payment_link_id,
                        "amount": str(inv.total_amount),
                    },
                    occurred_at=paid_dt,
                )
                continue

            # Inbound reply processing
            if inbound:
                reply_dt = _dt(inbound.timestamp)
                _record_step(
                    orm_inv,
                    ref,
                    TransitionEvent.REPLY_RECEIVED,
                    reasoning=f'Inbound buyer WhatsApp reply received: "{inbound.message_text}"',
                    actor="system",
                    metadata={"event": "reply_received", "channel": "whatsapp"},
                    occurred_at=reply_dt,
                )

                if inbound.intent_label == "promise" or inv.promise_outcome in (
                    "pending",
                    "kept",
                    "broken",
                ):
                    prom_dt = reply_dt + timedelta(seconds=15)
                    conf = 0.90
                    promised_d = inbound.promised_date or inv.notes or str(inv.due_date)
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.PROMISE_LOGGED,
                        reasoning=(
                            f"Zero-shot classifier extracted promise to pay by {promised_d} "
                            f"(confidence {conf:.0%}); auto-logged (>=70% threshold)."
                        ),
                        actor="agent",
                        metadata={
                            "event": "promise_logged",
                            "intent": "promise",
                            "confidence": conf,
                            "promised_date": str(promised_d),
                        },
                        occurred_at=prom_dt,
                    )

                    if inv.promise_outcome == "kept" or inv.status == "paid":
                        paid_dt = _dt(
                            f"{inv.paid_date or inbound.promised_date or inv.due_date}T12:00:00"
                        )
                        _record_step(
                            orm_inv,
                            ref,
                            TransitionEvent.PAYMENT_CONFIRMED,
                            reasoning=(
                                f"Payment of ₹{inv.total_amount:,.0f} settled on promised date; "
                                "promise kept."
                            ),
                            actor="system",
                            metadata={
                                "event": "payment_confirmed",
                                "promise_status": "kept",
                                "amount": str(inv.total_amount),
                            },
                            occurred_at=paid_dt,
                        )
                    elif inv.promise_outcome == "broken":
                        passed_dt = _dt(
                            f"{inbound.promised_date or inv.due_date}T10:00:00"
                        ) + timedelta(days=1)
                        _record_step(
                            orm_inv,
                            ref,
                            TransitionEvent.PROMISE_DATE_PASSED,
                            reasoning=(
                                f"Promised date ({inbound.promised_date or inv.due_date}) passed "
                                "without settlement; sent reminder."
                            ),
                            actor="agent",
                            metadata={"event": "promise_date_passed"},
                            occurred_at=passed_dt,
                        )
                        broken_dt = passed_dt + timedelta(days=3)
                        _record_step(
                            orm_inv,
                            ref,
                            TransitionEvent.PROMISE_BROKEN,
                            reasoning=(
                                "Grace period expired without settlement; promise marked broken "
                                "and escalated."
                            ),
                            actor="agent",
                            metadata={"event": "promise_broken", "promise_status": "broken"},
                            occurred_at=broken_dt,
                        )
                elif is_dispute or inbound.intent_label == "dispute":
                    disp_dt = reply_dt + timedelta(seconds=15)
                    conf = 0.92
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.DISPUTE_RAISED,
                        reasoning=(
                            f'Buyer indicated billing dispute: "{inbound.message_text}"; '
                            "halted automated reminders."
                        ),
                        actor="agent",
                        metadata={
                            "event": "dispute_raised",
                            "intent": "dispute",
                            "confidence": conf,
                        },
                        occurred_at=disp_dt,
                    )
                    route_dt = disp_dt + timedelta(minutes=5)
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.ROUTED_TO_HUMAN,
                        reasoning=(
                            "Dispute routed to merchant billing desk for credit note "
                            "or invoice review."
                        ),
                        actor="agent",
                        metadata={"event": "routed_to_human"},
                        occurred_at=route_dt,
                    )
                    if idx % 2 == 0:
                        res_dt = route_dt + timedelta(days=1)
                        _record_step(
                            orm_inv,
                            ref,
                            TransitionEvent.HUMAN_RESOLVED_CLOSED,
                            reasoning=(
                                "Merchant operator verified billing adjustment and closed dispute."
                            ),
                            actor="human",
                            metadata={
                                "event": "human_resolved_closed",
                                "resolution": "credit_note_issued",
                                "actor_role": "billing_manager",
                            },
                            occurred_at=res_dt,
                        )
                elif is_opt_out or inbound.intent_label == "opt_out":
                    opt_dt = reply_dt + timedelta(seconds=15)
                    conf = 0.95
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.OPT_OUT_RECEIVED,
                        reasoning=(
                            f'Buyer requested opt-out: "{inbound.message_text}"; '
                            "messaging halted permanently."
                        ),
                        actor="agent",
                        metadata={
                            "event": "opt_out_received",
                            "intent": "opt_out",
                            "confidence": conf,
                        },
                        occurred_at=opt_dt,
                    )
                    fin_dt = opt_dt + timedelta(hours=1)
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.OPT_OUT_FINALIZED,
                        reasoning=(
                            "Opt-out acknowledged and archived; automated workflow terminated."
                        ),
                        actor="system",
                        metadata={"event": "opt_out_finalized"},
                        occurred_at=fin_dt,
                    )
                elif is_ambiguous or inbound.intent_label == "ambiguous":
                    amb_dt = reply_dt + timedelta(seconds=15)
                    conf = 0.45  # Below 70% threshold -> Abstention story
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.NEEDS_HUMAN,
                        reasoning=(
                            f'Ambiguous reply: "{inbound.message_text}"; abstained below 70% '
                            "threshold and routed to Human Review."
                        ),
                        actor="agent",
                        metadata={
                            "event": "needs_human",
                            "intent": "ambiguous",
                            "confidence": conf,
                            "threshold": 0.70,
                            "abstained": True,
                        },
                        occurred_at=amb_dt,
                    )
                    if idx % 3 == 0:
                        human_dt = amb_dt + timedelta(hours=4)
                        _record_step(
                            orm_inv,
                            ref,
                            TransitionEvent.HUMAN_RESOLVED_RECOVERED,
                            reasoning=(
                                "Merchant operator spoke with buyer directly, verified transfer, "
                                "and settled invoice."
                            ),
                            actor="human",
                            metadata={
                                "event": "human_resolved_recovered",
                                "resolution": "manual_transfer_confirmed",
                                "actor_role": "collections_agent",
                            },
                            occurred_at=human_dt,
                        )
                elif inbound.intent_label == "objection":
                    obj_dt = reply_dt + timedelta(seconds=15)
                    conf = 0.88
                    _record_step(
                        orm_inv,
                        ref,
                        TransitionEvent.OBJECTION_RECEIVED,
                        reasoning="Buyer requested short extension; re-queued into nudge cycle.",
                        actor="agent",
                        metadata={
                            "event": "objection_received",
                            "intent": "objection",
                            "confidence": conf,
                        },
                        occurred_at=obj_dt,
                    )

    await session.flush()

    # Promise-to-pay rows, derived from the promise replies inserted above.
    promises_created = 0
    for invoice_id, (source_id, promised_date) in promise_sources.items():
        gen_inv = next((i for i in gen.invoices if i.invoice_id == invoice_id), None)
        if gen_inv is None or gen_inv.promise_outcome not in ("pending", "kept", "broken"):
            continue

        resolved_at: datetime | None = None
        if gen_inv.promise_outcome == "kept":
            kept_date = gen_inv.paid_date or promised_date
            resolved_at = _dt(f"{kept_date}T12:00:00")
        elif gen_inv.promise_outcome == "broken":
            resolved_at = _dt(f"{promised_date}T12:00:00")

        session.add(
            Promise(
                id=uuid4(),
                invoice_id=invoice_id,
                source_interaction_id=source_id,
                promised_date=date.fromisoformat(promised_date),
                promised_amount=None,
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
