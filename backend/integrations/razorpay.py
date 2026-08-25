import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

import structlog

from backend.config import Settings, get_settings
from backend.logging_util import mask_amount

logger = structlog.get_logger("duebot.razorpay")


def verify_webhook_signature(
    raw_body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify HMAC SHA-256 signature from X-Razorpay-Signature header.

    Matches razorpay.utility.Utility.verify_webhook_signature standard.
    """
    if not signature or not secret:
        return False
    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


@dataclass(frozen=True, slots=True)
class PaymentLinkResult:
    """Created (or mocked) Payment Link."""

    payment_link_id: str
    short_url: str


class RazorpayClient:
    """Create Payment Links and verify webhook signatures. Never captures or auto-debits."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._sdk: Any | None = None
        if self._settings.razorpay_configured:
            import razorpay

            self._sdk = razorpay.Client(
                auth=(self._settings.razorpay_key_id, self._settings.razorpay_key_secret)
            )

    @property
    def uses_mock(self) -> bool:
        """True when credentials are absent and links are synthetic."""
        return self._sdk is None

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify webhook signature against configured secret."""
        if not signature:
            return False
        secret = self._settings.razorpay_webhook_secret or "test_webhook_secret"
        return verify_webhook_signature(raw_body, signature, secret)

    def create_payment_link(
        self,
        *,
        amount_inr: Decimal,
        invoice_number: str,
        customer_name: str,
    ) -> PaymentLinkResult:
        """Create a test-mode Payment Link or a deterministic mock.

        Amount is sent in paise. DueBot never initiates a debit.
        """
        paise = int((amount_inr * 100).quantize(Decimal("1")))
        logger.info(
            "create_payment_link",
            invoice_number=invoice_number,
            amount_bucket=mask_amount(amount_inr),
            mock=self.uses_mock,
        )
        if self._sdk is None:
            link_id = f"plink_mock_{uuid4().hex[:14]}"
            return PaymentLinkResult(
                payment_link_id=link_id,
                short_url=f"https://rzp.io/l/{link_id[-8:]}",
            )

        created = self._sdk.payment_link.create(
            {
                "amount": paise,
                "currency": "INR",
                "description": f"Invoice {invoice_number}",
                "customer": {"name": customer_name},
            }
        )
        return PaymentLinkResult(
            payment_link_id=str(created["id"]),
            short_url=str(created.get("short_url") or created["id"]),
        )
