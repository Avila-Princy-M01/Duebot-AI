"""WhatsApp send requires a PolicyDecision, not a boolean."""

from __future__ import annotations

from uuid import uuid4

import pytest
from backend.engine.policy import PolicyDecision
from backend.exceptions import PolicyBlockedError
from backend.integrations.whatsapp import WhatsAppSender


@pytest.mark.asyncio
async def test_send_refuses_blocked_policy() -> None:
    """A blocked decision cannot be overridden at the integration boundary."""
    sender = WhatsAppSender()
    with pytest.raises(PolicyBlockedError):
        await sender.send(
            policy=PolicyDecision.blocked("no"),
            interaction_id=uuid4(),
            invoice_id="INV-1",
            to_phone="+919999999999",
            body="hi",
        )
