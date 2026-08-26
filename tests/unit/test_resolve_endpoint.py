"""API-level tests for POST /api/invoices/{id}/resolve.

Covers:
- Happy path: human_review → recovered (HUMAN_RESOLVED_RECOVERED)
- Happy path: human_review → terminated (HUMAN_RESOLVED_CLOSED)
- Wrong state: 409 when invoice is not in human_review
- Not found: 404 for unknown invoice_id
- Validation: 422 when reasoning is too short (< 5 chars)
- Audit: resolved row written to audit_log with actor=human
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from backend.config import Settings, get_settings
from backend.dependencies import get_db
from backend.engine.states import InvoiceState
from backend.main import create_app
from backend.models.audit_log import AuditLog
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(session_factory: async_sessionmaker[AsyncSession]):
    app = create_app()

    async def _override_db():
        async with session_factory() as s:
            yield s

    def _override_settings():
        return Settings(database_url="sqlite+aiosqlite:///:memory:")

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_settings] = _override_settings
    return app


async def _seed(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    invoice_id: str,
    state: InvoiceState,
) -> None:
    """Insert the minimum rows needed to hit the resolve endpoint."""
    async with session_factory() as session:
        session.add(
            Merchant(
                merchant_id="mer_res_1",
                business_name="Resolve Merchant",
                business_type="services",
                gstin="27ABCDE1234F1Z5",
                city="Mumbai",
                state_code="27",
                onboarded_date=date(2025, 1, 1),
            )
        )
        session.add(
            Buyer(
                buyer_id="buy_res_1",
                merchant_id="mer_res_1",
                company_name="Buyer Co",
                contact_name="Test Buyer",
                phone="+919900000001",
                email="buyer@test.com",
                gstin="27ABCDE1234F1Z6",
                reliability_tier="reliable",
                on_time_payment_rate=0.85,
                relationship_since=date(2025, 1, 1),
            )
        )
        session.add(
            Invoice(
                invoice_id=invoice_id,
                merchant_id="mer_res_1",
                buyer_id="buy_res_1",
                invoice_number=f"INV-RES-{invoice_id[-3:]}",
                issue_date=date(2026, 7, 1),
                due_date=date(2026, 8, 1),
                payment_terms_days=30,
                subtotal_amount=Decimal("10000.00"),
                gst_rate=18,
                gst_amount=Decimal("1800.00"),
                total_amount=Decimal("11800.00"),
                amount_paid=Decimal("0.00"),
                status="overdue",
                risk_tier="medium",
                split="test",
                state=state.value,
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_resolve_recovered_happy_path(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """human_review → recovered: 200, state updated, audit row actor=human."""
    inv_id = "inv_res_001"
    await _seed(session_factory, invoice_id=inv_id, state=InvoiceState.HUMAN_REVIEW)
    app = _make_app(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/invoices/{inv_id}/resolve",
            json={"resolution": "recovered", "reasoning": "Spoke with buyer — confirmed payment."},
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["data"]["previous_state"] == "human_review"
    assert body["data"]["new_state"] == "recovered"
    assert body["data"]["resolution"] == "recovered"

    # Verify DB state
    async with session_factory() as session:
        invoice = await session.get(Invoice, inv_id)
        assert invoice is not None
        assert invoice.state == "recovered"
        assert invoice.amount_paid == Decimal("11800.00")

        # Verify audit row
        audit_rows = (
            (
                await session.execute(
                    select(AuditLog)
                    .where(AuditLog.invoice_id == inv_id)
                    .order_by(AuditLog.occurred_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .all()
        )
        assert len(audit_rows) == 1
        row = audit_rows[0]
        assert row.from_state == "human_review"
        assert row.to_state == "recovered"
        assert row.actor == "human"


@pytest.mark.anyio
async def test_resolve_closed_happy_path(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """human_review → terminated: 200, state = terminated."""
    inv_id = "inv_res_002"
    await _seed(session_factory, invoice_id=inv_id, state=InvoiceState.HUMAN_REVIEW)
    app = _make_app(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/invoices/{inv_id}/resolve",
            json={"resolution": "closed", "reasoning": "Dispute confirmed — written off."},
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["data"]["new_state"] == "terminated"

    async with session_factory() as session:
        invoice = await session.get(Invoice, inv_id)
        assert invoice is not None
        assert invoice.state == "terminated"


@pytest.mark.anyio
async def test_resolve_wrong_state_returns_409(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Resolving an invoice not in human_review returns 409."""
    inv_id = "inv_res_003"
    await _seed(session_factory, invoice_id=inv_id, state=InvoiceState.NUDGED)
    app = _make_app(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/invoices/{inv_id}/resolve",
            json={"resolution": "recovered", "reasoning": "Should not work from nudged state."},
        )

    assert res.status_code == 409
    assert "human_review" in res.json()["error"]["message"]


@pytest.mark.anyio
async def test_resolve_not_found_returns_404(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Resolving a non-existent invoice returns 404."""
    app = _make_app(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/invoices/inv_does_not_exist/resolve",
            json={"resolution": "recovered", "reasoning": "Should 404."},
        )

    assert res.status_code == 404


@pytest.mark.anyio
async def test_resolve_short_reasoning_returns_422(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Reasoning shorter than 5 chars is rejected by Pydantic validation (422)."""
    inv_id = "inv_res_004"
    await _seed(session_factory, invoice_id=inv_id, state=InvoiceState.HUMAN_REVIEW)
    app = _make_app(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/invoices/{inv_id}/resolve",
            json={"resolution": "recovered", "reasoning": "ok"},  # 2 chars, below min_length=5
        )

    assert res.status_code == 422
