"""Test that every invoice audit trail is a strictly monotonic, connected chain."""

from __future__ import annotations

import pytest
from backend.data.seed import seed_from_generator
from backend.models.audit_log import AuditLog
from backend.models.invoice import Invoice
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_audit_trail_is_connected_monotonic_chain(db_session: AsyncSession) -> None:
    """For every invoice, the chronologically-sorted audit trail must be a connected
    chain starting at 'created' and ending at the invoice's current state."""
    await seed_from_generator(db_session, num_invoices=40, seed=42)
    await db_session.commit()

    invoices_res = await db_session.execute(select(Invoice))
    invoices = list(invoices_res.scalars())
    assert len(invoices) > 0

    audit_res = await db_session.execute(
        select(AuditLog).order_by(AuditLog.occurred_at.asc(), AuditLog.id.asc())
    )
    all_audit = list(audit_res.scalars())

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

        # 1. Chain must start from 'created'
        assert trail[0].from_state == "created", (
            f"Invoice {inv.invoice_id} trail starts at {trail[0].from_state}, expected 'created'"
        )

        # 2. Strict monotonicity and connected edges
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

        # 3. Trail must terminate at invoice.state
        assert trail[-1].to_state == inv.state, (
            f"Invoice {inv.invoice_id} trail ends at {trail[-1].to_state}, expected invoice.state={inv.state}"
        )
