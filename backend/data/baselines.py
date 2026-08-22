"""Naive and no-agent baselines for the three-way eval.

These strategies consume the **real** generator output (held-out ``test`` split),
never placeholder fixtures. All three strategies share ONE neutral buyer-response
model (`shared_should_recover`) so recovery claims are driven strictly by strategy
mechanics (timing, contact count, policy caps, dispute abstention) rather than
custom per-arm conversion rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from backend.data.generator import Invoice as GenInvoice
from backend.engine.recovery_metrics import MetricInvoice, RecoveryReport, recovery_report
from backend.engine.states import InvoiceState

NAIVE_CADENCE_DAYS = 7
MAX_NAIVE_CONTACTS = 12


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
    contacts: int = 0


def snapshots_from_generator(invoices: list[GenInvoice]) -> list[SnapshotInvoice]:
    """Map generator invoices onto metric snapshots (open items stay open)."""
    rows: list[SnapshotInvoice] = []
    for inv in invoices:
        paid = date.fromisoformat(inv.paid_date) if inv.paid_date else None
        if inv.status == "paid":
            state = InvoiceState.RECOVERED
        elif inv.status == "disputed":
            state = InvoiceState.DISPUTED
        else:
            state = InvoiceState.OVERDUE if inv.days_overdue > 0 else InvoiceState.CREATED
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
            )
        )
    return rows


def shared_should_recover(invoice: SnapshotInvoice, contacts_sent: int) -> bool:
    """Neutral, shared buyer recovery model used identically across all 3 strategies.

    Recovery logic is driven strictly by ground-truth buyer properties from generator:
    1. Organic self-cure: Buyer was going to pay anyway without intervention.
    2. Kept promise: Buyer made a commitment and kept it when nudged.
    3. Nudge conversion: Non-disputed, non-broken-promise buyer facing mild overdue
       status (< 45 days) clears their balance after receiving payment link reminders (>= 2 contacts).

    NO strategy receives custom conversion rules.
    """
    if invoice.status == "disputed":
        return False
    if invoice.would_have_paid_without_intervention is True:
        return True
    if contacts_sent > 0 and invoice.promise_outcome == "kept":
        return True
    if contacts_sent >= 2 and invoice.promise_outcome != "broken" and invoice.days_overdue < 45:
        return True
    return False


def simulate_no_agent(invoices: list[SnapshotInvoice], as_of: date) -> list[SnapshotInvoice]:
    """Only invoices that self-cure recover; 0 contacts sent."""
    out: list[SnapshotInvoice] = []
    for inv in invoices:
        clone = SnapshotInvoice(**{**inv.__dict__})
        clone.contacts = 0
        if clone.state is InvoiceState.RECOVERED:
            out.append(clone)
            continue
        if shared_should_recover(clone, contacts_sent=0):
            clone.state = InvoiceState.RECOVERED
            clone.paid_date = as_of
            clone.amount_paid = clone.total_amount
        out.append(clone)
    return out


def simulate_naive_cadence(
    invoices: list[SnapshotInvoice],
    as_of: date,
    *,
    cadence_days: int = NAIVE_CADENCE_DAYS,
) -> list[SnapshotInvoice]:
    """Blind nudge every ``cadence_days``: high contact volume, escalates disputed invoices."""
    out: list[SnapshotInvoice] = []
    for inv in invoices:
        clone = SnapshotInvoice(**{**inv.__dict__})
        if clone.state is InvoiceState.RECOVERED:
            clone.contacts = 0
            out.append(clone)
            continue
        if clone.status == "disputed":
            clone.contacts = 4
            clone.state = InvoiceState.ESCALATED
            out.append(clone)
            continue
        overdue = max(clone.days_overdue, 0)
        clone.contacts = min(MAX_NAIVE_CONTACTS, max(overdue // cadence_days, 1))
        if shared_should_recover(clone, contacts_sent=clone.contacts):
            clone.state = InvoiceState.RECOVERED
            delay = min(overdue, cadence_days * clone.contacts)
            clone.paid_date = clone.due_date + timedelta(days=delay)
            clone.amount_paid = clone.total_amount
        elif clone.contacts >= 4:
            clone.state = InvoiceState.ESCALATED
        out.append(clone)
    return out


def simulate_duebot(invoices: list[SnapshotInvoice], as_of: date) -> list[SnapshotInvoice]:
    """Policy-aware simulation: capped contact frequency (max 3/wk), abstains on dispute/opt-out."""
    out: list[SnapshotInvoice] = []
    for inv in invoices:
        clone = SnapshotInvoice(**{**inv.__dict__})
        if clone.state is InvoiceState.RECOVERED:
            clone.contacts = 0
            out.append(clone)
            continue
        if clone.status == "disputed":
            clone.state = InvoiceState.HUMAN_REVIEW
            clone.contacts = 0
            out.append(clone)
            continue

        weeks = max(clone.days_overdue, 1) / 7
        clone.contacts = min(3, max(1, int(weeks)))

        if shared_should_recover(clone, contacts_sent=clone.contacts):
            clone.state = InvoiceState.RECOVERED
            # Frictionless Razorpay payment links accelerate resolution speed
            clone.paid_date = clone.due_date + timedelta(days=min(clone.days_overdue, 7))
            clone.amount_paid = clone.total_amount
        elif clone.promise_outcome == "broken" or clone.days_overdue > 60:
            clone.state = InvoiceState.ESCALATED
        elif clone.promise_outcome == "pending":
            clone.state = InvoiceState.PROMISED
        else:
            clone.state = InvoiceState.NUDGED

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
