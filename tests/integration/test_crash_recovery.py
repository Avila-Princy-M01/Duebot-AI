"""Integration test for process crash recovery and log-before-send idempotency.

Verifies that if a crash occurs after DB interaction logging but before WhatsApp confirmation,
re-running the task skips duplicate outbound sends and preserves state immutability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from backend.engine.states import InvoiceState
from backend.exceptions import IntegrationError
from backend.integrations.razorpay import RazorpayClient
from backend.integrations.whatsapp import WhatsAppSender
from backend.llm.client import AnthropicClient
from backend.llm.message_drafter import MessageDrafter
from backend.models.buyer import Buyer
from backend.models.interaction import Interaction
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.tasks.nudge_executor import execute_nudge
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_nudge_crash_recovery_prevents_duplicate_sends(db_session: AsyncSession) -> None:
    """Simulate process crash after DB write but before WhatsApp API confirmation."""
    today = datetime.now(UTC).date()
    merchant_id = str(uuid4())
    merchant = Merchant(
        merchant_id=merchant_id,
        business_name="Test Corp",
        business_type="wholesale",
        gstin="27AAAAA0000A1Z5",
        city="Mumbai",
        state_code="27",
        onboarded_date=today,
    )
    buyer_id = str(uuid4())
    buyer = Buyer(
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        company_name="Buyer Ltd",
        contact_name="Ramesh Kumar",
        phone="+919876543211",
        email="buyer@example.com",
        gstin="27BBBBB1111B1Z5",
        reliability_tier="occasional_late",
        on_time_payment_rate=0.85,
        relationship_since=today,
    )
    invoice_id = str(uuid4())
    invoice = Invoice(
        invoice_id=invoice_id,
        merchant_id=merchant_id,
        buyer_id=buyer_id,
        invoice_number="INV-CRASH-001",
        issue_date=today,
        due_date=today,
        payment_terms_days=30,
        subtotal_amount=Decimal("42372.88"),
        gst_rate=18,
        gst_amount=Decimal("7627.12"),
        total_amount=Decimal("50000.00"),
        currency="INR",
        status="overdue",
        amount_paid=Decimal("0.00"),
        days_overdue=10,
        risk_tier="medium",
        state=InvoiceState.OVERDUE.value,
        opted_out=False,
        split="test",
    )
    db_session.add_all([merchant, buyer, invoice])
    await db_session.commit()

    drafter = MessageDrafter(AnthropicClient())
    razorpay = RazorpayClient()

    # Track how many times WhatsApp send is actually invoked
    send_attempts = 0

    class CrashingWhatsAppSender(WhatsAppSender):
        async def send(
            self,
            *,
            policy: object,
            interaction_id: object,
            invoice_id: str,
            to_phone: str,
            body: str,
        ) -> str:
            nonlocal send_attempts
            send_attempts += 1
            if send_attempts == 1:
                # Simulate network crash / timeout right after DB write
                raise IntegrationError("Simulated network crash during WhatsApp HTTP send")
            return await super().send(
                policy=policy,
                interaction_id=interaction_id,
                invoice_id=invoice_id,
                to_phone=to_phone,
                body=body,
            )

    crashing_whatsapp = CrashingWhatsAppSender()

    # Step 1: Execute nudge -> Crashes mid-send after interaction logged to DB
    with pytest.raises(IntegrationError, match="Simulated network crash"):
        await execute_nudge(
            db_session,
            invoice,
            buyer,
            drafter=drafter,
            razorpay=razorpay,
            whatsapp=crashing_whatsapp,
        )

    assert send_attempts == 1

    # Verify that DB record was created before crash
    result = await db_session.execute(
        select(Interaction).where(Interaction.invoice_id == invoice.invoice_id)
    )
    interactions = list(result.scalars().all())
    assert len(interactions) == 1
    assert interactions[0].delivery_status == "pending"

    # Step 2: System recovers and re-runs execute_nudge on the same invoice
    did_send, decision, body = await execute_nudge(
        db_session,
        invoice,
        buyer,
        drafter=drafter,
        razorpay=razorpay,
        whatsapp=crashing_whatsapp,
    )

    # Step 3: Idempotency check prevents duplicate WhatsApp send
    assert did_send is False
    assert send_attempts == 1  # No secondary HTTP call made!

    # Verify no duplicate interaction rows were created
    result_after = await db_session.execute(
        select(Interaction).where(Interaction.invoice_id == invoice.invoice_id)
    )
    interactions_after = list(result_after.scalars().all())
    assert len(interactions_after) == 1
