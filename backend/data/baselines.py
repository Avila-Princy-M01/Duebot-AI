"""Naive and no-agent baselines for the three-way eval.

These strategies consume the **real** generator output (held-out ``test`` split).
DueBot's evaluation is driven by its real deterministic engine (``can_contact``,
``transition``, ``event_for_parsed_intent``, and ``fallback_intent``), stepping a
simulated clock day-by-day.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from backend.data.generator import BuyerMessage
from backend.data.generator import Invoice as GenInvoice
from backend.engine.policy import (
    ReplyIntent,
    can_contact,
    event_for_parsed_intent,
)
from backend.engine.recovery_metrics import MetricInvoice, RecoveryReport, recovery_report
from backend.engine.scheduler import next_action_at
from backend.engine.states import (
    TERMINAL_STATES,
    InvoiceState,
    TransitionEvent,
    is_valid_transition,
    transition,
)
from backend.llm.reply_parser import fallback_intent

NAIVE_CADENCE_DAYS = 7
MAX_NAIVE_CONTACTS = 12


@dataclass(slots=True)
class SnapshotTouch:
    """An interaction touch that satisfies HasOutboundTouch."""

    direction: str
    sent_at: datetime


@dataclass
class SnapshotInvoice:
    """In-memory invoice snapshot used by the eval harness."""

    invoice_id: str
    state: InvoiceState
    total_amount: Decimal
    amount_paid: Decimal
    due_date: date
    paid_date: date | None
    would_have_paid_without_intervention: bool | None
    promise_outcome: str
    days_overdue: int
    status: str
    opted_out: bool = False
    promised_date: date | None = None
    scripted_reply_text: str | None = None
    scripted_reply_date: date | None = None
    history: list[SnapshotTouch] = field(default_factory=list)

    @property
    def contacts(self) -> int:
        """Actual measured outbound contacts recorded in interaction history."""
        return sum(1 for touch in self.history if touch.direction == "outbound")


def snapshots_from_generator(
    invoices: list[GenInvoice],
    messages: list[BuyerMessage] | None = None,
) -> list[SnapshotInvoice]:
    """Map generator invoices and scripted replies onto evaluation snapshots."""
    replies_by_inv: dict[str, tuple[str, date]] = {}
    if messages:
        for msg in messages:
            if msg.direction == "inbound":
                msg_dt = datetime.fromisoformat(msg.timestamp).date()
                replies_by_inv[msg.invoice_id] = (msg.message_text, msg_dt)

    rows: list[SnapshotInvoice] = []
    for inv in invoices:
        paid = date.fromisoformat(inv.paid_date) if inv.paid_date else None
        if inv.status == "paid":
            state = InvoiceState.RECOVERED
        elif inv.status == "disputed":
            state = InvoiceState.DISPUTED
        else:
            state = InvoiceState.OVERDUE if inv.days_overdue > 0 else InvoiceState.CREATED

        scripted_text, scripted_date = replies_by_inv.get(inv.invoice_id, (None, None))

        rows.append(
            SnapshotInvoice(
                invoice_id=inv.invoice_id,
                state=state,
                total_amount=Decimal(str(inv.total_amount)),
                amount_paid=Decimal(str(inv.amount_paid)),
                due_date=date.fromisoformat(inv.due_date),
                paid_date=paid,
                would_have_paid_without_intervention=inv.would_have_paid_without_intervention,
                promise_outcome=inv.promise_outcome,
                days_overdue=inv.days_overdue,
                status=inv.status,
                opted_out=False,
                promised_date=None,
                scripted_reply_text=scripted_text,
                scripted_reply_date=scripted_date,
                history=[],
            )
        )
    return rows


def shared_should_settle(invoice: SnapshotInvoice, clock_date: date) -> bool:
    """Neutral, shared buyer settlement model used identically across all 3 strategies.

    Settlement conditions are driven strictly by ground-truth buyer properties:
    1. Organic self-cure: Buyer pays 3 days post-due without intervention.
    2. Kept promise: Buyer pays when the promised date is reached after receiving outreach.
    3. Nudge conversion: Non-disputed, non-broken-promise buyer pays after receiving >= 2 touches.

    Zero strategy-specific speed bonuses or artificial paid_date overrides.
    """
    if invoice.status == "disputed":
        return False

    outbound_count = invoice.contacts

    # 1. Organic Self-Cure
    if invoice.would_have_paid_without_intervention is True:
        return clock_date >= invoice.due_date + timedelta(days=3)

    # 2. Kept Promise
    if outbound_count > 0 and invoice.promise_outcome == "kept":
        if invoice.promised_date is not None:
            return clock_date >= invoice.promised_date
        return clock_date >= invoice.due_date + timedelta(days=7)

    # 3. Nudge Conversion (converts once buyer receives >= 2 touches before 45 days)
    return bool(
        outbound_count >= 2
        and invoice.promise_outcome != "broken"
        and (clock_date - invoice.due_date).days < 45
    )


def simulate_no_agent(invoices: list[SnapshotInvoice], as_of: date) -> list[SnapshotInvoice]:
    """No-agent baseline: 0 contacts sent, recovers only if organic self-cure."""
    out: list[SnapshotInvoice] = []
    for inv in invoices:
        clone = SnapshotInvoice(
            invoice_id=inv.invoice_id,
            state=inv.state,
            total_amount=inv.total_amount,
            amount_paid=inv.amount_paid,
            due_date=inv.due_date,
            paid_date=inv.paid_date,
            would_have_paid_without_intervention=inv.would_have_paid_without_intervention,
            promise_outcome=inv.promise_outcome,
            days_overdue=inv.days_overdue,
            status=inv.status,
            opted_out=inv.opted_out,
            promised_date=inv.promised_date,
            scripted_reply_text=inv.scripted_reply_text,
            scripted_reply_date=inv.scripted_reply_date,
            history=[],
        )
        if clone.state is InvoiceState.RECOVERED:
            out.append(clone)
            continue

        start_date = min(clone.due_date, as_of)
        days_span = max((as_of - start_date).days, 1)

        for day_offset in range(days_span + 1):
            clock_date = start_date + timedelta(days=day_offset)
            if shared_should_settle(clone, clock_date):
                clone.state = InvoiceState.RECOVERED
                clone.paid_date = clock_date
                clone.amount_paid = clone.total_amount
                break

        out.append(clone)
    return out


def simulate_naive_cadence(
    invoices: list[SnapshotInvoice],
    as_of: date,
    *,
    cadence_days: int = NAIVE_CADENCE_DAYS,
    max_contacts: int = MAX_NAIVE_CONTACTS,
) -> list[SnapshotInvoice]:
    """Naive baseline: fixed interval send, NO can_contact policy gate, NO dispute check."""
    out: list[SnapshotInvoice] = []
    for inv in invoices:
        clone = SnapshotInvoice(
            invoice_id=inv.invoice_id,
            state=inv.state,
            total_amount=inv.total_amount,
            amount_paid=inv.amount_paid,
            due_date=inv.due_date,
            paid_date=inv.paid_date,
            would_have_paid_without_intervention=inv.would_have_paid_without_intervention,
            promise_outcome=inv.promise_outcome,
            days_overdue=inv.days_overdue,
            status=inv.status,
            opted_out=inv.opted_out,
            promised_date=inv.promised_date,
            scripted_reply_text=inv.scripted_reply_text,
            scripted_reply_date=inv.scripted_reply_date,
            history=[],
        )

        if clone.state is InvoiceState.RECOVERED:
            out.append(clone)
            continue

        start_date = min(clone.due_date, as_of)
        days_span = max((as_of - start_date).days, 1)

        # Naive steps in intervals of cadence_days with NO policy check
        for day_offset in range(0, days_span + 1, cadence_days):
            clock_date = start_date + timedelta(days=day_offset)
            clock_dt = datetime.combine(clock_date, time(10, 0), tzinfo=UTC)

            # Blind send (no policy check): sends on disputed, exceeds weekly frequency caps
            if len(clone.history) < max_contacts:
                clone.history.append(SnapshotTouch(direction="outbound", sent_at=clock_dt))

            # Buyer response model check (shared, neutral across all arms)
            if shared_should_settle(clone, clock_date) and clone.status != "disputed":
                clone.state = InvoiceState.RECOVERED
                clone.paid_date = clock_date
                clone.amount_paid = clone.total_amount
                break

        out.append(clone)
    return out


def simulate_duebot(invoices: list[SnapshotInvoice], as_of: date) -> list[SnapshotInvoice]:
    """Execute DueBot's real deterministic engine, policy gates, and state machine day-by-day."""
    out: list[SnapshotInvoice] = []

    for inv in invoices:
        clone = SnapshotInvoice(
            invoice_id=inv.invoice_id,
            state=inv.state,
            total_amount=inv.total_amount,
            amount_paid=inv.amount_paid,
            due_date=inv.due_date,
            paid_date=inv.paid_date,
            would_have_paid_without_intervention=inv.would_have_paid_without_intervention,
            promise_outcome=inv.promise_outcome,
            days_overdue=inv.days_overdue,
            status=inv.status,
            opted_out=inv.opted_out,
            promised_date=inv.promised_date,
            scripted_reply_text=inv.scripted_reply_text,
            scripted_reply_date=inv.scripted_reply_date,
            history=[],
        )

        if clone.state is InvoiceState.RECOVERED:
            out.append(clone)
            continue

        # If disputed prior to start, route to human review
        if clone.status == "disputed":
            if is_valid_transition(clone.state, TransitionEvent.ROUTED_TO_HUMAN):
                tr = transition(
                    clone,
                    TransitionEvent.ROUTED_TO_HUMAN,
                    reasoning="Disputed invoice routed to human review",
                    occurred_at=datetime.combine(clone.due_date, time(9, 0), tzinfo=UTC),
                )
                clone.state = tr.new_state
            else:
                clone.state = InvoiceState.HUMAN_REVIEW
            out.append(clone)
            continue

        start_date = min(clone.due_date, as_of)
        days_span = max((as_of - start_date).days, 1)

        # Step simulated clock day-by-day
        for day_offset in range(days_span + 1):
            clock_date = start_date + timedelta(days=day_offset)
            clock_dt = datetime.combine(clock_date, time(10, 0), tzinfo=UTC)

            if clone.state in TERMINAL_STATES:
                break

            # 1. Aging step
            if clock_date > clone.due_date and clone.state is InvoiceState.CREATED:
                tr = transition(
                    clone,
                    TransitionEvent.AGED,
                    reasoning="Invoice past due date",
                    occurred_at=clock_dt,
                )
                clone.state = tr.new_state
                clone.days_overdue = (clock_date - clone.due_date).days

            # 2. Promise expiry check
            if (
                clone.state is InvoiceState.PROMISED
                and clone.promised_date is not None
                and clock_date > clone.promised_date
            ):
                tr = transition(
                    clone,
                    TransitionEvent.PROMISE_DATE_PASSED,
                    reasoning="Promised payment date passed",
                    occurred_at=clock_dt,
                )
                clone.state = tr.new_state
                if clone.promise_outcome == "broken":
                    tr_brk = transition(
                        clone,
                        TransitionEvent.PROMISE_BROKEN,
                        reasoning="Promise broken by buyer",
                        occurred_at=clock_dt,
                    )
                    clone.state = tr_brk.new_state

            # 3. Ground-truth buyer payment resolution (shared, neutral across all arms)
            if shared_should_settle(clone, clock_date) and is_valid_transition(
                clone.state, TransitionEvent.PAYMENT_CONFIRMED
            ):
                tr = transition(
                    clone,
                    TransitionEvent.PAYMENT_CONFIRMED,
                    reasoning="Payment confirmed via webhook",
                    occurred_at=clock_dt,
                )
                clone.state = tr.new_state
                clone.paid_date = clock_date
                clone.amount_paid = clone.total_amount
                break

            # 4. Outbound Nudge execution governed by real scheduler and can_contact() policy
            if clone.state in (InvoiceState.OVERDUE, InvoiceState.NUDGED, InvoiceState.REMINDED):
                if (
                    clone.contacts >= 3
                    and clone.state is InvoiceState.NUDGED
                    and is_valid_transition(clone.state, TransitionEvent.CONTACT_CAP_REACHED)
                ):
                    tr = transition(
                        clone,
                        TransitionEvent.CONTACT_CAP_REACHED,
                        reasoning="Maximum nudge sequence (3 touches) completed",
                        occurred_at=clock_dt,
                    )
                    clone.state = tr.new_state
                    continue

                prom_dt = (
                    datetime.combine(clone.promised_date, time(10, 0), tzinfo=UTC)
                    if clone.promised_date
                    else None
                )
                action_due = next_action_at(
                    clone, clone.history, as_of=clock_dt, promised_date=prom_dt
                )
                if action_due is not None and clock_dt >= action_due:
                    decision = can_contact(clone, clone.history, as_of=clock_dt)
                    if decision.allowed:
                        if clone.state is InvoiceState.OVERDUE and is_valid_transition(
                            clone.state, TransitionEvent.NUDGE_SENT
                        ):
                            tr = transition(
                                clone,
                                TransitionEvent.NUDGE_SENT,
                                reasoning=decision.reason,
                                occurred_at=clock_dt,
                            )
                            clone.state = tr.new_state

                        # Append actual outbound touch
                        clone.history.append(SnapshotTouch(direction="outbound", sent_at=clock_dt))

            # 5. Inbound buyer reply processing
            if clone.scripted_reply_text and clone.scripted_reply_date == clock_date:
                reply_dt = datetime.combine(clock_date, time(14, 0), tzinfo=UTC)
                if clone.state is InvoiceState.NUDGED and is_valid_transition(
                    clone.state, TransitionEvent.REPLY_RECEIVED
                ):
                    tr_rep = transition(
                        clone,
                        TransitionEvent.REPLY_RECEIVED,
                        reasoning="Inbound buyer WhatsApp message received",
                        occurred_at=reply_dt,
                    )
                    clone.state = tr_rep.new_state

                if clone.state is InvoiceState.REPLIED:
                    parsed = fallback_intent(clone.scripted_reply_text, as_of=clock_date)
                    evt = event_for_parsed_intent(parsed.intent, parsed.confidence)
                    if is_valid_transition(clone.state, evt):
                        tr_evt = transition(
                            clone,
                            evt,
                            reasoning=parsed.reasoning,
                            occurred_at=reply_dt,
                        )
                        clone.state = tr_evt.new_state
                        if parsed.intent == ReplyIntent.PROMISE and parsed.promised_date:
                            clone.promised_date = parsed.promised_date
                        elif parsed.intent == ReplyIntent.OPT_OUT:
                            clone.opted_out = True

        out.append(clone)

    return out


def report_for(
    invoices: list[SnapshotInvoice],
    *,
    as_of: date,
) -> RecoveryReport:
    """Build a ``RecoveryReport`` from snapshots (satisfies ``MetricInvoice``)."""
    typed: list[MetricInvoice] = list(invoices)
    return recovery_report(
        typed,
        as_of=as_of,
        total_contacts_sent=sum(item.contacts for item in invoices),
    )
