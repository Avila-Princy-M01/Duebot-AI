"""Recovery-rate and baseline-comparison math.

Pure functions over in-memory invoice snapshots. Persistence of a
``baseline_comparison`` row is the caller's job.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from backend.engine.states import InvoiceState

__all__ = [
    "RECOVERY_HORIZON_30_DAYS",
    "RECOVERY_HORIZON_60_DAYS",
    "RECOVERY_HORIZON_90_DAYS",
    "MetricInvoice",
    "RecoveryReport",
    "recovery_rate",
    "promise_kept_rate",
    "false_escalation_rate",
    "recovery_report",
]


RECOVERY_HORIZON_30_DAYS = 30
RECOVERY_HORIZON_60_DAYS = 60
RECOVERY_HORIZON_90_DAYS = 90


class MetricInvoice(Protocol):
    """Invoice fields needed to compute recovery metrics."""

    invoice_id: str
    state: InvoiceState
    total_amount: Decimal
    amount_paid: Decimal
    due_date: date
    paid_date: date | None
    would_have_paid_without_intervention: bool | None
    promise_outcome: str


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    """One strategy's numbers on a fixed invoice batch."""

    eval_set_size: int
    recovered_count: int
    recovered_value: Decimal
    total_value: Decimal
    recovery_rate: float
    recovery_30d: float
    recovery_60d: float
    recovery_90d: float
    avg_days_to_recovery: float
    promise_kept_rate: float
    false_escalation_rate: float
    total_contacts_sent: int
    recovery_per_contact: float = 0.0


def _is_recovered(invoice: MetricInvoice) -> bool:
    return invoice.state is InvoiceState.RECOVERED


def _value_at_risk(invoice: MetricInvoice) -> Decimal:
    remaining = invoice.total_amount - invoice.amount_paid
    return remaining if remaining > 0 else Decimal("0")


def recovery_rate(invoices: Sequence[MetricInvoice]) -> float:
    """Share of batch value that is recovered (paid / RECOVERED)."""
    total = sum((inv.total_amount for inv in invoices), Decimal("0"))
    if total == 0:
        return 0.0
    recovered = sum(
        (inv.total_amount for inv in invoices if _is_recovered(inv)),
        Decimal("0"),
    )
    return float(recovered / total)


def promise_kept_rate(invoices: Sequence[MetricInvoice]) -> float:
    """Kept / (kept + broken) among invoices with a promise outcome."""
    decided = [inv for inv in invoices if inv.promise_outcome in ("kept", "broken")]
    if not decided:
        return 0.0
    kept = sum(1 for inv in decided if inv.promise_outcome == "kept")
    return kept / len(decided)


def false_escalation_rate(invoices: Sequence[MetricInvoice]) -> float:
    """Escalated invoices that the ground-truth label says would have self-cured."""
    escalated = [
        inv for inv in invoices if inv.state in (InvoiceState.ESCALATED, InvoiceState.HUMAN_REVIEW)
    ]
    if not escalated:
        return 0.0
    false_pos = sum(1 for inv in escalated if inv.would_have_paid_without_intervention is True)
    return false_pos / len(escalated)


def _horizon_rate(
    invoices: Sequence[MetricInvoice],
    as_of: date,
    horizon_days: int,
) -> float:
    total = sum((inv.total_amount for inv in invoices), Decimal("0"))
    if total == 0:
        return 0.0
    recovered = Decimal("0")
    for inv in invoices:
        if not _is_recovered(inv):
            continue
        paid_on = inv.paid_date if inv.paid_date is not None else as_of
        if (paid_on - inv.due_date).days <= horizon_days:
            recovered += inv.total_amount
    return float(recovered / total)


def recovery_report(
    invoices: Sequence[MetricInvoice],
    *,
    as_of: date,
    total_contacts_sent: int = 0,
) -> RecoveryReport:
    """Build a full recovery report for one strategy on ``invoices``.

    Args:
        invoices: The evaluation batch (typically the generator ``test`` split).
        as_of: Reference date for 30/60/90-day horizons.
        total_contacts_sent: Outbound count for this strategy (0 for no-agent).

    Returns:
        ``RecoveryReport`` ready to persist as a ``baseline_comparison`` row.
    """
    recovered_invoices = [inv for inv in invoices if _is_recovered(inv)]
    recovered_value = sum((inv.total_amount for inv in recovered_invoices), Decimal("0"))
    total_value = sum((inv.total_amount for inv in invoices), Decimal("0"))
    delays: list[int] = []
    for inv in recovered_invoices:
        paid_on = inv.paid_date if inv.paid_date is not None else as_of
        delays.append(max((paid_on - inv.due_date).days, 0))
    avg_days = float(sum(delays) / len(delays)) if delays else 0.0
    rpc = float(recovered_value / Decimal(total_contacts_sent)) if total_contacts_sent > 0 else 0.0
    return RecoveryReport(
        eval_set_size=len(invoices),
        recovered_count=len(recovered_invoices),
        recovered_value=recovered_value,
        total_value=total_value,
        recovery_rate=recovery_rate(invoices),
        recovery_30d=_horizon_rate(invoices, as_of, RECOVERY_HORIZON_30_DAYS),
        recovery_60d=_horizon_rate(invoices, as_of, RECOVERY_HORIZON_60_DAYS),
        recovery_90d=_horizon_rate(invoices, as_of, RECOVERY_HORIZON_90_DAYS),
        avg_days_to_recovery=avg_days,
        promise_kept_rate=promise_kept_rate(invoices),
        false_escalation_rate=false_escalation_rate(invoices),
        total_contacts_sent=total_contacts_sent,
        recovery_per_contact=rpc,
    )
