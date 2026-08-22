"""Invoice schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class InvoiceOut(BaseModel):
    """Invoice list row."""

    invoice_id: str
    merchant_id: str
    buyer_id: str
    invoice_number: str
    issue_date: date
    due_date: date
    total_amount: Decimal
    amount_paid: Decimal
    currency: str
    status: str
    state: str
    days_overdue: int
    risk_tier: str
    opted_out: bool
    split: str
    edge_case: str
    payment_link_id: str | None

    model_config = {"from_attributes": True}


class InteractionOut(BaseModel):
    """Message on an invoice timeline."""

    id: UUID
    channel: str
    direction: str
    sent_at: datetime
    message_text: str
    intent_label: str
    confidence: float | None
    delivery_status: str
    attempt_number: int

    model_config = {"from_attributes": True}


class PromiseOutLite(BaseModel):
    """Promise nested on invoice detail."""

    id: UUID
    promised_date: date
    promised_amount: Decimal | None
    confidence: float
    status: str

    model_config = {"from_attributes": True}


class AuditOutLite(BaseModel):
    """Audit row nested on invoice detail."""

    id: UUID
    from_state: str
    to_state: str
    actor: str
    occurred_at: datetime
    reasoning_summary: str
    extra_metadata: dict[str, object] | None = None

    model_config = {"from_attributes": True}


class InvoiceDetail(InvoiceOut):
    """Invoice plus thread, promises, and audit trail."""

    subtotal_amount: Decimal
    gst_rate: int
    gst_amount: Decimal
    payment_terms_days: int
    notes: str | None
    would_have_paid_without_intervention: bool | None
    promise_outcome: str
    interactions: list[InteractionOut]
    promises: list[PromiseOutLite]
    audit: list[AuditOutLite]
