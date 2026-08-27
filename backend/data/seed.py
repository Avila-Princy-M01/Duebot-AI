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
from backend.data.generator import SIM_TODAY, BuyerMessage, DueBotDataGenerator
from backend.engine.audit_chain import GENESIS_HASH, compute_row_hash
from backend.engine.states import Actor, InvoiceState, TransitionEvent, transition
from backend.logging_util import mask_email, mask_phone
from backend.models.audit_log import AuditLog
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.models.promise import Promise
from backend.tasks.lifecycle import InvoiceRef

SIM_NOW = datetime.combine(SIM_TODAY, datetime.min.time()).replace(hour=18, tzinfo=UTC)

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
    pending_audit_logs: list[AuditLog] = []

    def _record_step(
        orm_inv: Invoice,
        ref: InvoiceRef,
        clock: datetime,
        event: TransitionEvent,
        *,
        reasoning: str,
        actor: Actor,
        metadata: dict[str, object] | None,
        target_dt: datetime,
    ) -> datetime:
        if target_dt > SIM_NOW:
            return clock
        # Monotonic guard: Each step occurs strictly after the previous step, capped at SIM_NOW
        actual_dt = min(max(target_dt, clock + timedelta(seconds=15)), SIM_NOW)
        if actual_dt <= clock:
            return clock

        res = transition(
            ref,
            event,
            reasoning=reasoning,
            actor=actor,
            metadata=metadata,
            occurred_at=actual_dt,
        )
        meta = dict(res.audit_entry.metadata)
        meta["event"] = res.audit_entry.event.value
        if "policy_version" not in meta:
            meta["policy_version"] = "v1.0.0"
        pending_audit_logs.append(
            AuditLog(
                id=uuid4(),
                invoice_id=orm_inv.invoice_id,
                from_state=res.audit_entry.from_state.value,
                to_state=res.audit_entry.to_state.value,
                actor=res.audit_entry.actor,
                occurred_at=actual_dt,
                reasoning_summary=res.audit_entry.reasoning_summary,
                extra_metadata=meta,
            )
        )
        ref.state = res.new_state
        orm_inv.state = res.new_state.value
        return actual_dt

    for idx, inv in enumerate(gen.invoices):
        orm_inv = orm_invoices[inv.invoice_id]
        ref = InvoiceRef(invoice_id=inv.invoice_id, state=InvoiceState.CREATED)

        if inv.status == "draft":
            continue

        # Invariant: Strictly monotonic simulated clock per invoice
        inv_created_at = _dt(f"{inv.issue_date}T09:{(idx * 3) % 60:02d}:{(idx * 7) % 60:02d}")
        current_clock = inv_created_at

        def step(
            event: TransitionEvent,
            *,
            reasoning: str,
            actor: Actor,
            metadata: dict[str, object] | None,
            target_dt: datetime,
            _inv: Invoice = orm_inv,
            _ref: InvoiceRef = ref,
        ) -> bool:
            nonlocal current_clock
            new_clock = _record_step(
                _inv,
                _ref,
                current_clock,
                event,
                reasoning=reasoning,
                actor=actor,
                metadata=metadata,
                target_dt=target_dt,
            )
            if new_clock > current_clock:
                current_clock = new_clock
                return True
            return False

        inbound = inbound_msgs_by_invoice.get(inv.invoice_id)
        outbound = outbound_msgs_by_invoice.get(inv.invoice_id, [])
        has_outbound = len(outbound) > 0
        is_opt_out = inv.edge_case == "opt_out_mid_sequence"
        is_ambiguous = inv.edge_case == "ambiguous_reply"
        is_dispute = inv.edge_case == "disputed_invoice" or inv.status == "disputed"

        paid_date_obj = date.fromisoformat(inv.paid_date) if inv.paid_date else None
        due_date_obj = date.fromisoformat(inv.due_date)
        is_early_paid = (
            inv.status == "paid"
            and paid_date_obj is not None
            and paid_date_obj <= due_date_obj
            and paid_date_obj <= SIM_TODAY
            and not has_outbound
            and not inbound
            and inv.promise_outcome not in ("pending", "kept", "broken")
        )

        # Early payment directly from CREATED -> RECOVERED without ever becoming overdue
        if is_early_paid:
            paid_dt = _dt(f"{inv.paid_date}T11:{(idx * 7) % 60:02d}:00")
            step(
                TransitionEvent.PAYMENT_CONFIRMED,
                reasoning=(
                    f"Razorpay payment confirmation webhook received for ₹{inv.total_amount:,.0f}; "
                    "invoice settled on-time before due date without reminders."
                ),
                actor="system",
                metadata={
                    "event": "payment_confirmed",
                    "payment_link_id": inv.payment_link_id,
                    "amount": str(inv.total_amount),
                    "early_payment": True,
                },
                target_dt=paid_dt,
            )
            continue

        # If due_date is in the future relative to SIM_TODAY, invoice has not aged yet!
        if due_date_obj > SIM_TODAY:
            orm_inv.state = InvoiceState.CREATED.value
            orm_inv.days_overdue = 0
            orm_inv.status = "pending"
            continue

        # Aging step: CREATED -> OVERDUE (only when due_date <= SIM_TODAY)
        due_dt = _dt(f"{inv.due_date}T10:{(idx * 5) % 60:02d}:{(idx * 11) % 60:02d}")
        if not step(
            TransitionEvent.AGED,
            reasoning=(
                f"Invoice reached due date ({inv.due_date}) with outstanding "
                f"balance of ₹{inv.total_amount:,.0f}; marked overdue."
            ),
            actor="system",
            metadata={"event": "aged", "due_date": str(inv.due_date)},
            target_dt=due_dt,
        ):
            continue

        # Self-cure payment after aging without nudge
        if (
            inv.status == "paid"
            and not has_outbound
            and not inbound
            and inv.promise_outcome not in ("pending", "kept", "broken")
        ):
            paid_dt = _dt(f"{inv.paid_date or inv.due_date}T11:00:00")
            step(
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
                target_dt=paid_dt,
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
            if not step(
                TransitionEvent.NUDGE_SENT,
                reasoning=(
                    "Deterministic scheduler dispatched payment reminder with Razorpay link "
                    "via WhatsApp (attempt 1)."
                ),
                actor="agent",
                metadata={"event": "nudge_sent", "attempt_number": 1, "channel": "whatsapp"},
                target_dt=nudge_dt,
            ):
                continue

            # Payment after nudge without reply
            if (
                inv.status == "paid"
                and not inbound
                and inv.promise_outcome not in ("pending", "kept", "broken")
            ):
                paid_dt = _dt(f"{inv.paid_date or inv.due_date}T14:30:00")
                step(
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
                    target_dt=paid_dt,
                )
                continue

            # Contact-cap escalation: buyer never replied after 3+ outbound nudges.
            # NUDGED → CONTACT_CAP_REACHED → ESCALATED → ROUTED_TO_HUMAN → HUMAN_REVIEW
            if not inbound and len(outbound) >= 3:
                cap_dt = nudge_dt + timedelta(days=7)
                if step(
                    TransitionEvent.CONTACT_CAP_REACHED,
                    reasoning=(
                        f"Maximum nudge sequence ({len(outbound)} touches) completed with no "
                        "buyer response; contact cap reached."
                    ),
                    actor="agent",
                    metadata={
                        "event": "contact_cap_reached",
                        "attempt_number": len(outbound),
                        "channel": "whatsapp",
                    },
                    target_dt=cap_dt,
                ):
                    esc_route_dt = cap_dt + timedelta(minutes=10)
                    if step(
                        TransitionEvent.ROUTED_TO_HUMAN,
                        reasoning=(
                            "Escalated to collections agent after exhausting automated nudge "
                            "sequence without response."
                        ),
                        actor="agent",
                        metadata={"event": "routed_to_human", "reason": "contact_cap_reached"},
                        target_dt=esc_route_dt,
                    ):
                        # Leave parked in HUMAN_REVIEW — human has not resolved yet in the demo.
                        pass
                continue

            # Inbound reply processing
            if inbound:
                reply_dt = _dt(inbound.timestamp)
                if not step(
                    TransitionEvent.REPLY_RECEIVED,
                    reasoning=f'Inbound buyer WhatsApp reply received: "{inbound.message_text}"',
                    actor="system",
                    metadata={"event": "reply_received", "channel": "whatsapp"},
                    target_dt=reply_dt,
                ):
                    continue

                if inbound.intent_label == "promise" or inv.promise_outcome in (
                    "pending",
                    "kept",
                    "broken",
                ):
                    prom_dt = current_clock + timedelta(seconds=15)
                    conf = 0.90
                    promised_d = inbound.promised_date or inv.notes or str(inv.due_date)
                    if step(
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
                        target_dt=prom_dt,
                    ):
                        if inv.promise_outcome == "kept" or inv.status == "paid":
                            paid_dt = _dt(
                                f"{inv.paid_date or inbound.promised_date or inv.due_date}T12:00:00"
                            )
                            step(
                                TransitionEvent.PAYMENT_CONFIRMED,
                                reasoning=(
                                    f"Payment of ₹{inv.total_amount:,.0f} settled on promised "
                                    "date; promise kept."
                                ),
                                actor="system",
                                metadata={
                                    "event": "payment_confirmed",
                                    "promise_status": "kept",
                                    "amount": str(inv.total_amount),
                                },
                                target_dt=paid_dt,
                            )
                        elif (
                            inv.promise_outcome == "broken"
                            or inv.edge_case == "promise_then_silent"
                        ):
                            passed_dt = min(
                                current_clock + timedelta(days=2),
                                SIM_NOW - timedelta(days=2),
                            )
                            if step(
                                TransitionEvent.PROMISE_DATE_PASSED,
                                reasoning=(
                                    f"Promised date ({inbound.promised_date or inv.due_date}) "
                                    "passed without settlement; sent reminder."
                                ),
                                actor="agent",
                                metadata={"event": "promise_date_passed"},
                                target_dt=passed_dt,
                            ):
                                broken_dt = min(
                                    current_clock + timedelta(days=2),
                                    SIM_NOW - timedelta(hours=6),
                                )
                                step(
                                    TransitionEvent.PROMISE_BROKEN,
                                    reasoning=(
                                        "Grace period expired without settlement; "
                                        "promise marked broken and escalated."
                                    ),
                                    actor="agent",
                                    metadata={
                                        "event": "promise_broken",
                                        "promise_status": "broken",
                                    },
                                    target_dt=broken_dt,
                                )
                                # Alternate: some escalate further to human_review,
                                # while ~6-8 remain parked in ESCALATED for live visibility.
                                if idx % 3 == 0:
                                    esc_dt = min(
                                        current_clock + timedelta(hours=4),
                                        SIM_NOW - timedelta(minutes=15),
                                    )
                                    step(
                                        TransitionEvent.ROUTED_TO_HUMAN,
                                        reasoning=(
                                            "Broken promise escalated to collections "
                                            "manager review."
                                        ),
                                        actor="agent",
                                        metadata={
                                            "event": "routed_to_human",
                                            "reason": "broken_promise",
                                        },
                                        target_dt=esc_dt,
                                    )
                elif is_dispute or inbound.intent_label == "dispute":
                    disp_dt = current_clock + timedelta(seconds=15)
                    conf = 0.92
                    if step(
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
                        target_dt=disp_dt,
                    ):
                        route_dt = current_clock + timedelta(minutes=5)
                        # All disputes route to human_review — no idx gate.
                        # Alternate resolution: even idx → billing error confirmed, close;
                        # odd idx → error disproved, recover the invoice.
                        if step(
                            TransitionEvent.ROUTED_TO_HUMAN,
                            reasoning=(
                                "Dispute routed to merchant billing desk for credit note "
                                "or invoice review."
                            ),
                            actor="agent",
                            metadata={"event": "routed_to_human"},
                            target_dt=route_dt,
                        ):
                            res_dt = current_clock + timedelta(days=1)
                            if idx % 2 == 0:
                                step(
                                    TransitionEvent.HUMAN_RESOLVED_CLOSED,
                                    reasoning=(
                                        "Merchant operator verified billing adjustment "
                                        "and closed dispute."
                                    ),
                                    actor="human",
                                    metadata={
                                        "event": "human_resolved_closed",
                                        "resolution": "credit_note_issued",
                                        "actor_role": "billing_manager",
                                    },
                                    target_dt=res_dt,
                                )
                            else:
                                step(
                                    TransitionEvent.HUMAN_RESOLVED_RECOVERED,
                                    reasoning=(
                                        "Merchant operator reviewed dispute, confirmed invoice "
                                        "is valid, and buyer settled."
                                    ),
                                    actor="human",
                                    metadata={
                                        "event": "human_resolved_recovered",
                                        "resolution": "dispute_disproved",
                                        "actor_role": "billing_manager",
                                    },
                                    target_dt=res_dt,
                                )
                elif is_opt_out or inbound.intent_label == "opt_out":
                    opt_dt = current_clock + timedelta(seconds=15)
                    conf = 0.95
                    if step(
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
                        target_dt=opt_dt,
                    ):
                        fin_dt = current_clock + timedelta(hours=1)
                        step(
                            TransitionEvent.OPT_OUT_FINALIZED,
                            reasoning=(
                                "Opt-out acknowledged and archived; automated workflow terminated."
                            ),
                            actor="system",
                            metadata={"event": "opt_out_finalized"},
                            target_dt=fin_dt,
                        )
                elif is_ambiguous or inbound.intent_label == "ambiguous":
                    amb_dt = current_clock + timedelta(seconds=15)
                    conf = 0.45  # Below 70% threshold -> Abstention story
                    # All ambiguous replies reach HUMAN_REVIEW — no idx gate on the route step.
                    # ~half resolve (even idx); odd idx stays parked in human_review for the demo.
                    if (
                        step(
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
                            target_dt=amb_dt,
                        )
                        and idx % 2 == 0
                    ):
                        human_dt = current_clock + timedelta(hours=4)
                        step(
                            TransitionEvent.HUMAN_RESOLVED_RECOVERED,
                            reasoning=(
                                "Merchant operator spoke with buyer directly, "
                                "verified transfer, and settled invoice."
                            ),
                            actor="human",
                            metadata={
                                "event": "human_resolved_recovered",
                                "resolution": "manual_transfer_confirmed",
                                "actor_role": "collections_agent",
                            },
                            target_dt=human_dt,
                        )
                elif inbound.intent_label == "objection":
                    obj_dt = current_clock + timedelta(seconds=15)
                    conf = 0.88
                    step(
                        TransitionEvent.OBJECTION_RECEIVED,
                        reasoning="Buyer requested short extension; re-queued into nudge cycle.",
                        actor="agent",
                        metadata={
                            "event": "objection_received",
                            "intent": "objection",
                            "confidence": conf,
                        },
                        target_dt=obj_dt,
                    )

    # -----------------------------------------------------------------------
    # Build Cryptographic SHA-256 Hash Chain over all chronologically ordered audit logs
    # -----------------------------------------------------------------------
    pending_audit_logs.sort(key=lambda a: (a.occurred_at, str(a.id)))
    current_prev_hash = GENESIS_HASH
    for row in pending_audit_logs:
        row.prev_hash = current_prev_hash
        row.row_hash = compute_row_hash(
            invoice_id=row.invoice_id,
            from_state=row.from_state,
            to_state=row.to_state,
            actor=row.actor,
            occurred_at=row.occurred_at,
            reasoning_summary=row.reasoning_summary,
            prev_hash=row.prev_hash,
            extra_metadata=row.extra_metadata,
        )
        current_prev_hash = row.row_hash
        session.add(row)

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


async def _cli_main() -> None:
    import argparse

    from backend.db import create_engine, session_factory

    parser = argparse.ArgumentParser(description="Seed DueBot database from synthetic generator.")
    parser.add_argument(
        "--num-invoices",
        type=int,
        default=260,
        help="Number of invoices to generate (default: 260)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic generator seed (default: 42)",
    )
    args = parser.parse_args()

    engine = create_engine()
    factory = session_factory(engine)
    async with factory() as session:
        counts = await seed_from_generator(session, num_invoices=args.num_invoices, seed=args.seed)
        await session.commit()
        print(f"Successfully seeded DueBot database: {counts}")
    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_cli_main())


seed_database = seed_from_generator

__all__ = ["seed_from_generator", "seed_database", "BuyerMessage"]
