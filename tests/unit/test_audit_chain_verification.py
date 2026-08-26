"""Unit tests for cryptographic SHA-256 hash chaining and tamper-evidence verification."""

from __future__ import annotations

import pytest
from backend.data.seed import seed_from_generator
from backend.engine.audit_chain import GENESIS_HASH, verify_chain
from backend.models.audit_log import AuditLog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_audit_cryptographic_chain_validity(db_session: AsyncSession) -> None:
    """A freshly seeded database must pass 100% cryptographic SHA-256 chain verification."""
    await seed_from_generator(db_session, num_invoices=40, seed=42)
    await db_session.commit()

    rows = await db_session.execute(
        select(AuditLog).order_by(AuditLog.occurred_at.asc(), AuditLog.id.asc())
    )
    all_rows = list(rows.scalars())
    assert len(all_rows) > 0

    is_valid, count_verified, latest_hash, error_msg = verify_chain(all_rows)
    assert is_valid is True
    assert count_verified == len(all_rows)
    assert error_msg is None
    assert latest_hash != GENESIS_HASH
    assert len(latest_hash) == 64


@pytest.mark.asyncio
async def test_audit_cryptographic_chain_detects_tampering(db_session: AsyncSession) -> None:
    """Modifying a single field in any past audit log block must be immediately flagged as tampering."""
    await seed_from_generator(db_session, num_invoices=20, seed=42)
    await db_session.commit()

    rows = await db_session.execute(
        select(AuditLog).order_by(AuditLog.occurred_at.asc(), AuditLog.id.asc())
    )
    all_rows = list(rows.scalars())
    assert len(all_rows) >= 3

    # Tamper with the reasoning of the second row
    original_reason = all_rows[1].reasoning_summary
    all_rows[1].reasoning_summary = "Forged unauthorized reason by an attacker"

    is_valid, count_verified, _, error_msg = verify_chain(all_rows)
    assert is_valid is False
    assert count_verified == 1
    assert error_msg is not None
    assert "Tampered row at block 1" in error_msg

    # Restore and verify it passes again
    all_rows[1].reasoning_summary = original_reason
    is_valid_restored, count_restored, _, _ = verify_chain(all_rows)
    assert is_valid_restored is True
    assert count_restored == len(all_rows)
