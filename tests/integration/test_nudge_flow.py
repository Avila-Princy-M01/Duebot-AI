"""Nudge dry-run does not send; policy still runs."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from backend.integrations.razorpay import RazorpayClient
from backend.integrations.whatsapp import WhatsAppSender
from backend.llm.client import AnthropicClient
from backend.llm.message_drafter import MessageDrafter
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.tasks.nudge_executor import execute_nudge
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_dry_run_does_not_transition(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """dry_run stops before send and leaves state as overdue."""
    async with session_factory() as session:
        session.add(
            Merchant(
                merchant_id="MER-001",
                business_name="Test Co",
                business_type="services",
                gstin="27AAAAA0000A1Z5",
                city="Pune",
                state_code="27",
                onboarded_date=date(2025, 1, 1),
            )
        )
        session.add(
            Buyer(
                buyer_id="MER-001-BUY-0001",
                merchant_id="MER-001",
                company_name="Buyer LLC",
                contact_name="Asha Rao",
                phone="+919890123456",
                email="ops@example.com",
                gstin="29BBBBB0000B1Z2",
                reliability_tier="reliable",
                on_time_payment_rate=0.9,
                relationship_since=date(2025, 6, 1),
            )
        )
        session.add(
            Invoice(
                invoice_id="INV-dryrun01",
                merchant_id="MER-001",
                buyer_id="MER-001-BUY-0001",
                invoice_number="TST/2026/00001",
                issue_date=date(2026, 7, 1),
                due_date=date(2026, 7, 31),
                payment_terms_days=30,
                subtotal_amount=Decimal("10000"),
                gst_rate=18,
                gst_amount=Decimal("1800"),
                total_amount=Decimal("11800"),
                currency="INR",
                status="overdue",
                amount_paid=Decimal("0"),
                paid_date=None,
                days_overdue=21,
                risk_tier="medium",
                payment_link_id=None,
                state="overdue",
                opted_out=False,
                edge_case="none",
                would_have_paid_without_intervention=True,
                promise_outcome="none",
                split="train",
            )
        )
        await session.commit()

        invoice = await session.get(Invoice, "INV-dryrun01")
        buyer = await session.get(Buyer, "MER-001-BUY-0001")
        assert invoice is not None and buyer is not None
        sent, decision, body = await execute_nudge(
            session,
            invoice,
            buyer,
            drafter=MessageDrafter(AnthropicClient()),
            razorpay=RazorpayClient(),
            whatsapp=WhatsAppSender(),
            dry_run=True,
            as_of=datetime(2026, 8, 21, tzinfo=UTC),
        )
        assert sent is False
        assert decision.allowed is True
        assert "INV" in body or "11800" in body or "11,800" in body
        assert invoice.state == "overdue"
