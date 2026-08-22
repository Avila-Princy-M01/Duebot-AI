"""Structured logging helpers with PII masking.

Never pass a raw phone, email, or invoice amount into ``structlog``.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Final

import structlog

_PHONE_RE: Final[re.Pattern[str]] = re.compile(r"\+?\d[\d\s-]{8,}\d")
_EMAIL_RE: Final[re.Pattern[str]] = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def mask_phone(phone: str) -> str:
    """Mask all but the last four digits of a phone number."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def mask_email(email: str) -> str:
    """Mask the local part of an email address."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def mask_amount(amount: Decimal | float | int) -> str:
    """Replace an invoice amount with a magnitude bucket, not the value."""
    value = float(amount)
    if value < 10_000:
        return "<10k"
    if value < 100_000:
        return "10k-1L"
    return ">1L"


def mask_text(text: str) -> str:
    """Redact phone numbers and emails inside free text before logging."""

    def _phone(match: re.Match[str]) -> str:
        return mask_phone(match.group(0))

    def _email(match: re.Match[str]) -> str:
        return mask_email(match.group(0))

    redacted = _PHONE_RE.sub(_phone, text)
    return _EMAIL_RE.sub(_email, redacted)


def configure_logging(level: str) -> None:
    """Configure stdlib + structlog processors for the process."""
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
