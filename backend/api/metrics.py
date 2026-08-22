"""Recovery metrics and baseline comparison."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.baselines import (
    NAIVE_CADENCE_DAYS,
    report_for,
    simulate_duebot,
    simulate_naive_cadence,
    simulate_no_agent,
    snapshots_from_generator,
)
from backend.data.generator import DueBotDataGenerator
from backend.dependencies import get_db
from backend.engine.recovery_metrics import recovery_report
from backend.engine.states import InvoiceState
from backend.models.baseline import BaselineComparison
from backend.models.invoice import Invoice
from backend.schemas.common import SuccessEnvelope
from backend.schemas.metrics import BaselineRowOut, RecoveryMetricsOut

router = APIRouter(prefix="/metrics", tags=["metrics"])


class _MetricInv:
    def __init__(self, inv: Invoice) -> None:
        self.invoice_id = inv.invoice_id
        self.state = InvoiceState(inv.state)
        self.total_amount: Decimal = inv.total_amount
        self.amount_paid: Decimal = inv.amount_paid
        self.due_date = inv.due_date
        self.paid_date = inv.paid_date
        self.would_have_paid_without_intervention = inv.would_have_paid_without_intervention
        self.promise_outcome = inv.promise_outcome


@router.get("/recovery")
async def recovery_metrics(
    split: str = Query(default="test"),
    as_of: date | None = None,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[RecoveryMetricsOut]:
    """Live recovery metrics from the database for ``split``."""
    today = as_of or date.today()
    result = await session.execute(select(Invoice).where(Invoice.split == split))
    invoices = list(result.scalars())
    wrapped = [_MetricInv(inv) for inv in invoices]
    report = recovery_report(wrapped, as_of=today, total_contacts_sent=0)
    return SuccessEnvelope(
        data=RecoveryMetricsOut(
            eval_set_size=report.eval_set_size,
            recovered_count=report.recovered_count,
            recovered_value=report.recovered_value,
            total_value=report.total_value,
            recovery_rate=report.recovery_rate,
            recovery_30d=report.recovery_30d,
            recovery_60d=report.recovery_60d,
            recovery_90d=report.recovery_90d,
            avg_days_to_recovery=report.avg_days_to_recovery,
            promise_kept_rate=report.promise_kept_rate,
            false_escalation_rate=report.false_escalation_rate,
            total_contacts_sent=report.total_contacts_sent,
            split=split,
        )
    )


@router.get("/baseline")
async def baseline_metrics(
    cadence_days: int = Query(default=NAIVE_CADENCE_DAYS, ge=1, le=30),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[BaselineRowOut]]:
    """Latest persisted three-way comparison, or compute in-memory from generator test split."""
    result = await session.execute(
        select(BaselineComparison).order_by(BaselineComparison.created_at.desc()).limit(3)
    )
    rows = list(result.scalars())
    if rows:
        return SuccessEnvelope(data=[BaselineRowOut.model_validate(r) for r in rows])

    gen = DueBotDataGenerator(seed=42)
    gen.run(num_invoices=120)
    test = [inv for inv in gen.invoices if inv.split == "test"]
    snaps = snapshots_from_generator(test)
    as_of = date(2026, 8, 21)
    _ = (
        report_for(simulate_no_agent(snaps, as_of), as_of=as_of),
        report_for(simulate_naive_cadence(snaps, as_of, cadence_days=cadence_days), as_of=as_of),
        report_for(simulate_duebot(snaps, as_of), as_of=as_of),
    )
    from uuid import uuid4

    from backend.models.baseline import BaselineComparison as BC

    run_id = uuid4()
    persisted: list[BaselineComparison] = []
    for strategy, sim in (
        ("no_agent", simulate_no_agent(snaps, as_of)),
        ("naive_cadence", simulate_naive_cadence(snaps, as_of, cadence_days=cadence_days)),
        ("duebot", simulate_duebot(snaps, as_of)),
    ):
        report = report_for(sim, as_of=as_of)
        row = BC(
            run_id=run_id,
            strategy=strategy,
            eval_set_size=report.eval_set_size,
            recovered_count=report.recovered_count,
            recovered_value=report.recovered_value,
            total_value=report.total_value,
            avg_days_to_recovery=report.avg_days_to_recovery,
            recovery_30d=report.recovery_30d,
            recovery_60d=report.recovery_60d,
            recovery_90d=report.recovery_90d,
            total_contacts_sent=report.total_contacts_sent,
        )
        session.add(row)
        persisted.append(row)
    await session.flush()
    return SuccessEnvelope(data=[BaselineRowOut.model_validate(r) for r in persisted])
