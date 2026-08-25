"""Unit tests for Razorpay webhook signature verification, security, and event processing."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date
from decimal import Decimal

import pytest
from backend.config import Settings, get_settings
from backend.dependencies import get_db
from backend.engine.states import InvoiceState
from backend.main import create_app
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

TEST_SECRET = "test_webhook_secret_key_12345"


def _sign_payload(payload_bytes: bytes, secret: str = TEST_SECRET) -> str:
    """Generate authentic Razorpay HMAC-SHA256 signature."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.mark.asyncio
async def test_webhook_unconfigured_secret_fails_closed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """If razorpay_webhook_secret is not configured, endpoint must fail closed with 503."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    def _override_get_settings():
        return Settings(razorpay_webhook_secret="", database_url="sqlite+aiosqlite:///:memory:")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = _override_get_settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {"event": "payment_link.paid"}
        body_bytes = json.dumps(payload).encode("utf-8")
        res = await client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "any_signature",
            },
        )
        assert res.status_code == 503
        assert "Razorpay webhook secret not configured" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_webhook_payment_link_paid_valid_signature(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Authentic payment_link.paid with valid signature marks invoice RECOVERED."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    def _override_get_settings():
        return Settings(razorpay_webhook_secret=TEST_SECRET, database_url="sqlite+aiosqlite:///:memory:")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = _override_get_settings

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
        payload = {
            "entity": "event",
            "account_id": "acc_test",
            "event": "payment_link.paid",
            "contains": ["payment_link"],
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test_12345",
                        "amount": 2950000,
                        "status": "paid",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = _sign_payload(body_bytes)

        res = await client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
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


@pytest.mark.asyncio
async def test_webhook_idempotent_retry_on_already_recovered(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Subsequent delivery of payment_link.paid returns 200 already_recovered without error."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    def _override_get_settings():
        return Settings(razorpay_webhook_secret=TEST_SECRET, database_url="sqlite+aiosqlite:///:memory:")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = _override_get_settings

    async with session_factory() as session:
        merchant = Merchant(
            merchant_id="mer_wh_2",
            business_name="Test Merchant 2",
            business_type="Retail",
            gstin="29ABCDE1234F1Z7",
            city="Bengaluru",
            state_code="KA",
            onboarded_date=date(2026, 1, 1),
        )
        buyer = Buyer(
            buyer_id="buy_wh_2",
            merchant_id="mer_wh_2",
            company_name="Acme Corp 2",
            contact_name="Ramesh Kumar",
            phone="+919876543211",
            email="ramesh2@acme.com",
            gstin="29ABCDE1234F1Z8",
            reliability_tier="reliable",
            on_time_payment_rate=0.9,
            relationship_since=date(2025, 1, 1),
        )
        invoice = Invoice(
            invoice_id="inv_wh_2",
            merchant_id="mer_wh_2",
            buyer_id="buy_wh_2",
            invoice_number="INV-WH-002",
            issue_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
            payment_terms_days=30,
            subtotal_amount=Decimal("10000.00"),
            gst_rate=18,
            gst_amount=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
            amount_paid=Decimal("11800.00"),
            status="paid",
            risk_tier="low",
            split="train",
            state=InvoiceState.RECOVERED.value,
            payment_link_id="plink_test_already_paid",
        )
        session.add_all([merchant, buyer, invoice])
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "entity": "event",
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test_already_paid",
                        "status": "paid",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = _sign_payload(body_bytes)

        res = await client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "already_recovered"
        assert data["invoice_id"] == "inv_wh_2"
        assert data["state"] == "recovered"


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Forged or missing webhook signature must be rejected with 401 Unauthorized."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    def _override_get_settings():
        return Settings(razorpay_webhook_secret=TEST_SECRET, database_url="sqlite+aiosqlite:///:memory:")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = _override_get_settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "event": "payment_link.paid",
            "payload": {"payment_link": {"entity": {"id": "plink_fake"}}},
        }
        body_bytes = json.dumps(payload).encode("utf-8")

        # 1. Missing signature header
        res_no_sig = await client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={"Content-Type": "application/json"},
        )
        assert res_no_sig.status_code == 401

        # 2. Tampered signature
        res_bad_sig = await client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "invalid_tampered_signature_hex",
            },
        )
        assert res_bad_sig.status_code == 401


@pytest.mark.asyncio
async def test_webhook_non_settlement_event_ignored(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Non-settlement events (e.g. payment_link.cancelled) do NOT trigger state transitions."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as s:
            yield s

    def _override_get_settings():
        return Settings(razorpay_webhook_secret=TEST_SECRET, database_url="sqlite+aiosqlite:///:memory:")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = _override_get_settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "entity": "event",
            "event": "payment_link.cancelled",
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test_12345",
                        "status": "cancelled",
                    }
                }
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = _sign_payload(body_bytes)

        res = await client.post(
            "/api/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "non_settlement_event"
