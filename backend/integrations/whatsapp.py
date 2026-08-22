"""WhatsApp sender. Simulated inbox is the default (demo-safe).

``send`` requires a ``PolicyDecision`` — a boolean cannot be passed.
The outbound interaction row must already exist with ``delivery_status=pending``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog

from backend.config import Settings, get_settings
from backend.engine.policy import PolicyDecision
from backend.exceptions import PolicyBlockedError
from backend.logging_util import mask_phone

logger = structlog.get_logger("duebot.whatsapp")


@dataclass
class SimulatedMessage:
    """One row in the in-process demo inbox."""

    interaction_id: UUID
    invoice_id: str
    to_phone_masked: str
    body: str
    sent_at: datetime
    direction: str


class SimulatedInbox:
    """Process-local inbox used when WHATSAPP_MODE=simulated."""

    def __init__(self) -> None:
        self.messages: list[SimulatedMessage] = []


INBOX = SimulatedInbox()


class WhatsAppSender:
    """Send a pre-logged nudge. Refuses to send without an allowed policy."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def send(
        self,
        *,
        policy: PolicyDecision,
        interaction_id: UUID,
        invoice_id: str,
        to_phone: str,
        body: str,
    ) -> str:
        """Deliver the message.

        Args:
            policy: Must be ``allowed``. This argument is required so callers
                cannot skip ``can_contact``.
            interaction_id: Pre-inserted outbound row.
            invoice_id: Invoice being nudged.
            to_phone: Destination (masked in logs).
            body: Already-drafted body.

        Returns:
            Delivery status: ``sent``.

        Raises:
            PolicyBlockedError: Policy did not allow contact.
        """
        if not policy.allowed:
            raise PolicyBlockedError(policy.reason)

        masked = mask_phone(to_phone)
        logger.info(
            "whatsapp_send",
            invoice_id=invoice_id,
            interaction_id=str(interaction_id),
            to=masked,
            mode=self._settings.whatsapp_mode,
        )
        INBOX.messages.append(
            SimulatedMessage(
                interaction_id=interaction_id,
                invoice_id=invoice_id,
                to_phone_masked=masked,
                body=body,
                sent_at=datetime.now(UTC),
                direction="outbound",
            )
        )
        return "sent"
