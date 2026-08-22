"""Email fallback. Logs and no-ops when SMTP is unset."""

from __future__ import annotations

import structlog

from backend.config import Settings, get_settings
from backend.engine.policy import PolicyDecision
from backend.exceptions import PolicyBlockedError
from backend.logging_util import mask_email

logger = structlog.get_logger("duebot.email")


class EmailSender:
    """Send an email nudge. Same policy gate as WhatsApp."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def send(
        self,
        *,
        policy: PolicyDecision,
        to_email: str,
        subject: str,
        body: str,
        invoice_id: str,
    ) -> str:
        """Send or stub-send an email.

        Raises:
            PolicyBlockedError: Policy did not allow contact.
        """
        if not policy.allowed:
            raise PolicyBlockedError(policy.reason)
        logger.info(
            "email_send",
            invoice_id=invoice_id,
            to=mask_email(to_email),
            smtp_configured=bool(self._settings.smtp_host),
            subject=subject,
        )
        return "sent"
