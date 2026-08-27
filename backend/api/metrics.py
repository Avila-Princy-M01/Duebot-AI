"""Recovery metrics and baseline comparison."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.baselines import (
    NAIVE_CADENCE_DAYS,
    report_for,
    simulate_duebot,
    simulate_naive_cadence,
    simulate_no_agent,
    snapshots_from_generator,
)
from backend.data.generator import SIM_TODAY, DueBotDataGenerator
from backend.dependencies import get_db
from backend.engine.recovery_metrics import recovery_report
from backend.engine.states import InvoiceState
from backend.models.baseline import BaselineComparison
from backend.models.interaction import Interaction
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


@router.get("")
@router.get("/recovery")
async def recovery_metrics(
    split: str = Query(default="test"),
    as_of: date | None = None,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[RecoveryMetricsOut]:
    """Live recovery metrics from the database for ``split``."""
    today = as_of or date.today()
    if split == "all":
        result = await session.execute(select(Invoice))
    else:
        result = await session.execute(select(Invoice).where(Invoice.split == split))
    invoices = list(result.scalars())
    invoice_ids = [inv.invoice_id for inv in invoices]

    # Count outbound contacts actually sent for this split's invoice set.
    total_contacts = 0
    if invoice_ids:
        contacts_result = await session.execute(
            select(func.count())
            .select_from(Interaction)
            .where(
                Interaction.direction == "outbound",
                Interaction.invoice_id.in_(invoice_ids),
            )
        )
        total_contacts = int(contacts_result.scalar_one() or 0)

    wrapped = [_MetricInv(inv) for inv in invoices]
    report = recovery_report(wrapped, as_of=today, total_contacts_sent=total_contacts)
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
            recovery_per_contact=report.recovery_per_contact,
            baseline_recovered_count=report.baseline_recovered_count,
            duebot_attributed_recovered_count=report.duebot_attributed_recovered_count,
            baseline_recovery_rate=report.baseline_recovery_rate,
            duebot_attributed_recovery_rate=report.duebot_attributed_recovery_rate,
            split=split,
        )
    )


@router.get("/baseline")
async def baseline_metrics(
    cadence_days: int = Query(default=NAIVE_CADENCE_DAYS, ge=1, le=30),
    refresh: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[BaselineRowOut]]:
    """Latest persisted three-way comparison run, or compute fresh from generator test split."""
    if not refresh and cadence_days == NAIVE_CADENCE_DAYS:
        latest_run_subquery = (
            select(BaselineComparison.run_id)
            .order_by(BaselineComparison.created_at.desc(), BaselineComparison.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        result = await session.execute(
            select(BaselineComparison)
            .where(BaselineComparison.run_id == latest_run_subquery)
            .order_by(BaselineComparison.id.asc())
        )
        rows = list(result.scalars())
        if len(rows) == 3:
            return SuccessEnvelope(data=[BaselineRowOut.model_validate(r) for r in rows])

    gen = DueBotDataGenerator(seed=42)
    gen.run(num_invoices=260)
    test = [inv for inv in gen.invoices if inv.split == "test"]
    snaps = snapshots_from_generator(test, gen.messages)
    as_of = SIM_TODAY

    run_id = uuid4()
    persisted: list[BaselineComparison] = []
    for strategy, sim in (
        ("no_agent", simulate_no_agent(snaps, as_of)),
        ("naive_cadence", simulate_naive_cadence(snaps, as_of, cadence_days=cadence_days)),
        ("duebot", simulate_duebot(snaps, as_of)),
    ):
        report = report_for(sim, as_of=as_of)
        row = BaselineComparison(
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
    await session.commit()
    return SuccessEnvelope(data=[BaselineRowOut.model_validate(r) for r in persisted])
