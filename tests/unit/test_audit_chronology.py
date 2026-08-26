"""Test that every invoice audit trail is a strictly monotonic, connected chain
and respects simulation timeline bounds (never dated after SIM_TODAY)."""

from __future__ import annotations

from datetime import UTC

import pytest
from backend.data.generator import SIM_TODAY
from backend.data.seed import SIM_NOW, seed_from_generator
from backend.models.audit_log import AuditLog
from backend.models.invoice import Invoice
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_audit_trail_is_connected_monotonic_chain(db_session: AsyncSession) -> None:
    """For every invoice, the chronologically-sorted audit trail must be a connected
    chain starting at 'created' and ending at the invoice's current state."""
    await seed_from_generator(db_session, num_invoices=50, seed=42)
    await db_session.commit()

    invoices_res = await db_session.execute(select(Invoice))
    invoices = list(invoices_res.scalars())
    assert len(invoices) > 0

    audit_res = await db_session.execute(
        select(AuditLog).order_by(AuditLog.occurred_at.asc(), AuditLog.id.asc())
    )
    all_audit = list(audit_res.scalars())
    assert len(all_audit) > 0

    # 1. Invariant: No audit row may ever be timestamped in the future relative to SIM_TODAY
    for entry in all_audit:
        occurred = (
            entry.occurred_at
            if entry.occurred_at.tzinfo is not None
            else entry.occurred_at.replace(tzinfo=UTC)
        )
        assert occurred <= SIM_NOW, f"Future timestamp found: {occurred} > {SIM_NOW}"
        assert entry.occurred_at.date() <= SIM_TODAY, (
            f"Audit entry date {entry.occurred_at.date()} exceeds SIM_TODAY {SIM_TODAY}"
        )

    # 2. Invariant: Invoices not yet due must remain 'created' with 0 days overdue
    for inv in invoices:
        if inv.due_date > SIM_TODAY:
            assert inv.days_overdue == 0, (
                f"Invoice {inv.invoice_id} with future due date {inv.due_date} has days_overdue={inv.days_overdue}"
            )
            if inv.amount_paid == 0:
                assert inv.state == "created", (
                    f"Future invoice {inv.invoice_id} has state {inv.state}, expected 'created'"
                )

    # 3. Invariant: Graph connectivity and monotonicity per invoice
    by_invoice: dict[str, list[AuditLog]] = {}
    for entry in all_audit:
        by_invoice.setdefault(entry.invoice_id, []).append(entry)

    for inv in invoices:
        trail = by_invoice.get(inv.invoice_id, [])
        if not trail:
            assert inv.state == "created", (
                f"Invoice {inv.invoice_id} in {inv.state} has no audit entries"
            )
            continue

        # Chain must start from 'created'
        assert trail[0].from_state == "created", (
            f"Invoice {inv.invoice_id} trail starts at {trail[0].from_state}, expected 'created'"
        )

        # Strict monotonicity and connected edges
        for i in range(len(trail) - 1):
            curr_step = trail[i]
            next_step = trail[i + 1]

            # Monotonic timestamps
            assert curr_step.occurred_at < next_step.occurred_at, (
                f"Invoice {inv.invoice_id} timestamp non-monotonic: {curr_step.occurred_at} >= {next_step.occurred_at}"
            )

            # Connected graph chain
            assert curr_step.to_state == next_step.from_state, (
                f"Invoice {inv.invoice_id} broken chain at step {i}: {curr_step.to_state} != {next_step.from_state}"
            )

        # Trail must terminate at invoice.state
        assert trail[-1].to_state == inv.state, (
            f"Invoice {inv.invoice_id} trail ends at {trail[-1].to_state}, expected invoice.state={inv.state}"
        )
