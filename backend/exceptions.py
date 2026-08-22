"""Domain exceptions for DueBot.

These are raised from the engine, API, and integrations so callers can
distinguish a policy block from a missing invoice from an invalid state
transition — never a bare ``Exception``.
"""

from __future__ import annotations

from backend.engine.states import InvalidTransitionError

__all__ = [
    "DueBotError",
    "NotFoundError",
    "PolicyBlockedError",
    "ConfigurationError",
    "IntegrationError",
    "InvalidTransitionError",
]


class DueBotError(Exception):
    """Base class for expected, handleable DueBot failures."""


class NotFoundError(DueBotError):
    """The requested merchant, invoice, buyer, or promise does not exist."""


class PolicyBlockedError(DueBotError):
    """``can_contact`` (or another hard invariant) refused the action."""


class ConfigurationError(DueBotError):
    """Required settings are missing or invalid."""


class IntegrationError(DueBotError):
    """An external API (Razorpay, WhatsApp, email) failed after retries."""
