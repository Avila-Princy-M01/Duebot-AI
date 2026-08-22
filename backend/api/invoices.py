"""Invoice list, detail, and CSV ingest."""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.data.csv_mapper import (
    coerce_decimal,
    initial_state_for_status,
    parse_optional_bool,
    parse_optional_date,
)
from backend.dependencies import get_db
from backend.exceptions import NotFoundError
from backend.models.buyer import Buyer
from backend.models.invoice import Invoice
from backend.models.merchant import Merchant
from backend.schemas.common import Meta, SuccessEnvelope
from backend.schemas.invoice import (
    AuditOutLite,
    InteractionOut,
    InvoiceDetail,
    InvoiceOut,
    PromiseOutLite,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("")
async def list_invoices(
    status: str | None = None,
    risk_tier: str | None = None,
    days_overdue_min: int | None = None,
    days_overdue_max: int | None = None,
    merchant_id: str | None = None,
    split: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[InvoiceOut]]:
    """Filterable invoice list."""
    stmt = select(Invoice)
    count_stmt = select(func.count()).select_from(Invoice)
    if status:
        stmt = stmt.where(Invoice.status == status)
        count_stmt = count_stmt.where(Invoice.status == status)
    if risk_tier:
        stmt = stmt.where(Invoice.risk_tier == risk_tier)
        count_stmt = count_stmt.where(Invoice.risk_tier == risk_tier)
    if days_overdue_min is not None:
        stmt = stmt.where(Invoice.days_overdue >= days_overdue_min)
        count_stmt = count_stmt.where(Invoice.days_overdue >= days_overdue_min)
    if days_overdue_max is not None:
        stmt = stmt.where(Invoice.days_overdue <= days_overdue_max)
        count_stmt = count_stmt.where(Invoice.days_overdue <= days_overdue_max)
    if merchant_id:
        stmt = stmt.where(Invoice.merchant_id == merchant_id)
        count_stmt = count_stmt.where(Invoice.merchant_id == merchant_id)
    if split:
        stmt = stmt.where(Invoice.split == split)
        count_stmt = count_stmt.where(Invoice.split == split)
    total = await session.scalar(count_stmt)
    rows = await session.execute(stmt.offset(offset).limit(limit))
    data = [InvoiceOut.model_validate(inv) for inv in rows.scalars()]
    return SuccessEnvelope(data=data, meta=Meta(total_count=int(total or 0)))


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[InvoiceDetail]:
    """Invoice with timeline, promises, and audit."""
    stmt = (
        select(Invoice)
        .where(Invoice.invoice_id == invoice_id)
        .options(
            selectinload(Invoice.interactions),
            selectinload(Invoice.promises),
            selectinload(Invoice.audit_entries),
        )
    )
    invoice = (await session.execute(stmt)).scalar_one_or_none()
    if invoice is None:
        raise NotFoundError(f"invoice {invoice_id} not found")
    invoice.interactions.sort(key=lambda row: row.sent_at)
    invoice.audit_entries.sort(key=lambda row: row.occurred_at)
    base = InvoiceOut.model_validate(invoice)
    return SuccessEnvelope(
        data=InvoiceDetail(
            **base.model_dump(),
            subtotal_amount=invoice.subtotal_amount,
            gst_rate=invoice.gst_rate,
            gst_amount=invoice.gst_amount,
            payment_terms_days=invoice.payment_terms_days,
            notes=invoice.notes,
            would_have_paid_without_intervention=invoice.would_have_paid_without_intervention,
            promise_outcome=invoice.promise_outcome,
            interactions=[InteractionOut.model_validate(row) for row in invoice.interactions],
            promises=[PromiseOutLite.model_validate(row) for row in invoice.promises],
            audit=[AuditOutLite.model_validate(row) for row in invoice.audit_entries],
        )
    )


@router.post("/ingest")
async def ingest_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[dict[str, int]]:
    """Bulk ingest a generator CSV (invoices.csv). Merchants/buyers must already exist."""
    raw = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(raw))
    inserted = 0
    for row in reader:
        existing = await session.get(Invoice, row["invoice_id"])
        if existing is not None:
            continue
        merchant = await session.get(Merchant, row["merchant_id"])
        buyer = await session.get(Buyer, row["buyer_id"])
        if merchant is None or buyer is None:
            continue
        status = row["status"]
        state = initial_state_for_status(status, has_inbound=False)
        session.add(
            Invoice(
                invoice_id=row["invoice_id"],
                merchant_id=row["merchant_id"],
                buyer_id=row["buyer_id"],
                invoice_number=row["invoice_number"],
                issue_date=date.fromisoformat(row["issue_date"]),
                due_date=date.fromisoformat(row["due_date"]),
                payment_terms_days=int(row["payment_terms_days"]),
                subtotal_amount=coerce_decimal(row["subtotal_amount"]),
                gst_rate=int(row["gst_rate"]),
                gst_amount=coerce_decimal(row["gst_amount"]),
                total_amount=coerce_decimal(row["total_amount"]),
                currency=row.get("currency") or "INR",
                status=status,
                amount_paid=coerce_decimal(row.get("amount_paid") or "0"),
                paid_date=parse_optional_date(row.get("paid_date")),
                days_overdue=int(row.get("days_overdue") or 0),
                risk_tier=row["risk_tier"],
                payment_link_id=row.get("payment_link_id") or None,
                state=state.value,
                opted_out=False,
                edge_case=row.get("edge_case") or "none",
                would_have_paid_without_intervention=parse_optional_bool(
                    row.get("would_have_paid_without_intervention")
                ),
                promise_outcome=row.get("promise_outcome") or "none",
                split=row.get("split") or "train",
                notes=row.get("notes") or None,
            )
        )
        inserted += 1
    await session.flush()
    return SuccessEnvelope(data={"inserted": inserted})
