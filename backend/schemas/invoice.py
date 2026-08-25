"""Invoice schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, field_serializer

if TYPE_CHECKING:
    from backend.models.invoice import Invoice as InvoiceModel


class InvoiceOut(BaseModel):
    """Invoice list row, denormalised with buyer identity and derived balances."""

    invoice_id: str
    merchant_id: str
    buyer_id: str
    buyer_company_name: str
    buyer_contact_name: str
    buyer_reliability_tier: str
    buyer_on_time_payment_rate: float
    invoice_number: str
    issue_date: date
    due_date: date
    paid_date: date | None
    total_amount: Decimal
    amount_paid: Decimal
    outstanding_amount: Decimal
    currency: str
    status: str
    state: str
    days_overdue: int
    days_late: int
    risk_tier: str
    opted_out: bool
    split: str
    edge_case: str
    payment_link_id: str | None

    @staticmethod
    def from_invoice(inv: InvoiceModel) -> InvoiceOut:
        """Build a row from an ORM invoice, deriving balance and settlement lateness.

        Two values cannot be read straight off a column:

        - ``outstanding_amount`` is what a collections operator actually chases.
          A partially-paid invoice carries a balance well below ``total_amount``.
        - ``days_overdue`` is reset to 0 the moment an invoice settles, so a paid
          invoice alone cannot say whether it was paid late. ``days_late``
          preserves that, measured from ``due_date`` to ``paid_date``.

        The caller must eager-load ``inv.buyer``; lazy-loading a relationship
        inside an async session raises ``MissingGreenlet``.
        """
        outstanding = max(Decimal("0"), inv.total_amount - inv.amount_paid)
        days_late = max((inv.paid_date - inv.due_date).days, 0) if inv.paid_date else 0
        return InvoiceOut(
            invoice_id=inv.invoice_id,
            merchant_id=inv.merchant_id,
            buyer_id=inv.buyer_id,
            buyer_company_name=inv.buyer.company_name,
            buyer_contact_name=inv.buyer.contact_name,
            buyer_reliability_tier=inv.buyer.reliability_tier,
            buyer_on_time_payment_rate=inv.buyer.on_time_payment_rate,
            invoice_number=inv.invoice_number,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            paid_date=inv.paid_date,
            total_amount=inv.total_amount,
            amount_paid=inv.amount_paid,
            outstanding_amount=outstanding,
            currency=inv.currency,
            status=inv.status,
            state=inv.state,
            days_overdue=inv.days_overdue,
            days_late=days_late,
            risk_tier=inv.risk_tier,
            opted_out=inv.opted_out,
            split=inv.split,
            edge_case=inv.edge_case,
            payment_link_id=inv.payment_link_id,
        )


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

    @field_serializer("sent_at")
    def serialize_sent_at(self, val: datetime) -> str:
        if val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val.isoformat()

    model_config = {"from_attributes": True}


class PromiseOutLite(BaseModel):
    """Promise nested on invoice detail."""

    id: UUID
    promised_date: date
    promised_amount: Decimal | None
    confidence: float
    status: str
    resolved_at: datetime | None = None

    @field_serializer("resolved_at")
    def serialize_resolved_at(self, val: datetime | None) -> str | None:
        if val is None:
            return None
        if val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val.isoformat()

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

    @field_serializer("occurred_at")
    def serialize_occurred_at(self, val: datetime) -> str:
        if val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val.isoformat()

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
