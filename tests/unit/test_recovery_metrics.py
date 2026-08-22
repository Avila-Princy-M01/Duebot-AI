"""Recovery metrics math."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.engine.recovery_metrics import recovery_report
from backend.engine.states import InvoiceState


@dataclass
class Inv:
    invoice_id: str
    state: InvoiceState
    total_amount: Decimal
    amount_paid: Decimal
    due_date: date
    paid_date: date | None
    would_have_paid_without_intervention: bool | None
    promise_outcome: str


def test_recovery_report_rates() -> None:
    """Recovered value / total, promise-kept, and false escalation."""
    invoices = [
        Inv(
            "a",
            InvoiceState.RECOVERED,
            Decimal("100"),
            Decimal("100"),
            date(2026, 7, 1),
            date(2026, 7, 10),
            True,
            "kept",
        ),
        Inv(
            "b",
            InvoiceState.OVERDUE,
            Decimal("100"),
            Decimal("0"),
            date(2026, 7, 1),
            None,
            False,
            "none",
        ),
        Inv(
            "c",
            InvoiceState.ESCALATED,
            Decimal("100"),
            Decimal("0"),
            date(2026, 6, 1),
            None,
            True,
            "broken",
        ),
        Inv(
            "d",
            InvoiceState.HUMAN_REVIEW,
            Decimal("100"),
            Decimal("0"),
            date(2026, 6, 1),
            None,
            False,
            "broken",
        ),
    ]
    report = recovery_report(invoices, as_of=date(2026, 8, 21), total_contacts_sent=4)
    assert report.eval_set_size == 4
    assert report.recovered_count == 1
    assert report.recovery_rate == 0.25
    assert report.promise_kept_rate == 1 / 3
    assert report.false_escalation_rate == 0.5
    assert report.total_contacts_sent == 4
