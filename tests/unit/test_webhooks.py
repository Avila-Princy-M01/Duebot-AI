"""Unit tests for Razorpay webhook handling."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from backend.dependencies import get_db
from backend.engine.states import InvoiceState
from backend.main import create_app
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_webhook_payment_link_paid_transitions_invoice(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Razorpay payment_link.paid webhook transitions invoice to RECOVERED."""
    app = create_app()

    async def _override_get_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_session

    async with session_factory() as session:
        merchant = Merchant(
            merchant_id="mer_wh_1",
            business_name="Test Merchant",
            business_type="Retail",
            gstin="29ABCDE1234F1Z5",
            city="Bengaluru",
            state_code="KA",
            onboarded_date=date(2026, 1, 1),
        )
        buyer = Buyer(
            buyer_id="buy_wh_1",
            merchant_id="mer_wh_1",
            company_name="Acme Corp",
            contact_name="Ramesh Kumar",
            phone="+919876543210",
            email="ramesh@acme.com",
            gstin="29ABCDE1234F1Z6",
            reliability_tier="reliable",
            on_time_payment_rate=0.9,
            relationship_since=date(2025, 1, 1),
        )
        invoice = Invoice(
            invoice_id="inv_wh_1",
            merchant_id="mer_wh_1",
            buyer_id="buy_wh_1",
            invoice_number="INV-WH-001",
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
            payment_terms_days=30,
            subtotal_amount=Decimal("25000.00"),
            gst_rate=18,
            gst_amount=Decimal("4500.00"),
            total_amount=Decimal("29500.00"),
            amount_paid=Decimal("0.00"),
            status="overdue",
            risk_tier="low",
            split="train",
            state=InvoiceState.NUDGED.value,
            payment_link_id="plink_test_12345",
        )
        session.add_all([merchant, buyer, invoice])
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Standard Razorpay payload format
        payload = {
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test_12345",
                        "status": "paid",
                    }
                }
            },
        }
        res = await client.post("/api/webhooks/razorpay", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["invoice_id"] == "inv_wh_1"
        assert data["state"] == "recovered"

    async with session_factory() as session:
        refreshed = await session.get(Invoice, "inv_wh_1")
        assert refreshed is not None
        assert refreshed.state == "recovered"
        assert refreshed.amount_paid == Decimal("29500.00")
