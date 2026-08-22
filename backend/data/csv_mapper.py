"""CSV ingest mapper — generator columns onto ORM invoices/buyers/merchants."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from backend.engine.states import InvoiceState


def parse_optional_date(value: str | None) -> date | None:
    """Parse an ISO date or return None for blanks."""
    if value is None or value == "":
        return None
    return date.fromisoformat(value)


def parse_optional_bool(value: str | bool | None) -> bool | None:
    """Parse generator boolean fields that may arrive as strings."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"true", "1", "yes"}


def initial_state_for_status(status: str, has_inbound: bool) -> InvoiceState:
    """Map generator ``status`` onto a state-machine starting state."""
    if status == "paid":
        return InvoiceState.RECOVERED
    if status == "disputed":
        return InvoiceState.DISPUTED
    if status in {"overdue", "partial"}:
        return InvoiceState.NUDGED if has_inbound else InvoiceState.OVERDUE
    return InvoiceState.CREATED


def coerce_decimal(value: Any) -> Decimal:
    """CSV amounts as Decimal."""
    return Decimal(str(value))
