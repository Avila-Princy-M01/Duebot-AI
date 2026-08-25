"""Razorpay webhook handlers for payment link status updates."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models.invoice import Invoice
from backend.tasks.payment import confirm_payment

logger = structlog.get_logger("duebot.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    """Process incoming Razorpay webhook events (e.g. payment_link.paid).

    Finds the matched invoice by payment_link_id or invoice_id/number,
    and applies the PAYMENT_CONFIRMED lifecycle transition.
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception as exc:
        logger.warning("invalid_webhook_payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    event = body.get("event")
    logger.info(
        "webhook_received",
        webhook_event=event,
        signature_present=bool(x_razorpay_signature),
    )

    invoice: Invoice | None = None

    # 1. Look up by direct invoice_id or payment_link_id in body
    if "invoice_id" in body:
        inv_id = str(body["invoice_id"])
        res = await session.execute(select(Invoice).where(Invoice.invoice_id == inv_id))
        invoice = res.scalar_one_or_none()

    elif "payment_link_id" in body:
        plink_id = str(body["payment_link_id"])
        res = await session.execute(
            select(Invoice).where(Invoice.payment_link_id == plink_id)
        )
        invoice = res.scalar_one_or_none()

    # 2. Look up by standard nested Razorpay webhook structure
    # e.g., payload.payment_link.entity.id or payload.payment.entity.notes.invoice_id
    elif "payload" in body and isinstance(body["payload"], dict):
        pl_entity = (
            body["payload"].get("payment_link", {}).get("entity", {})
            if isinstance(body["payload"].get("payment_link"), dict)
            else {}
        )
        plink_raw = pl_entity.get("id")
        if plink_raw is not None:
            plink_id = str(plink_raw)
            res = await session.execute(
                select(Invoice).where(Invoice.payment_link_id == plink_id)
            )
            invoice = res.scalar_one_or_none()

        if not invoice:
            notes = pl_entity.get("notes", {})
            if isinstance(notes, dict) and "invoice_id" in notes:
                res = await session.execute(
                    select(Invoice).where(Invoice.invoice_id == str(notes["invoice_id"]))
                )
                invoice = res.scalar_one_or_none()

    if invoice is None:
        logger.warning("webhook_invoice_not_found", event=event)
        return {"status": "ignored", "reason": "invoice_not_found"}

    # Apply idempotent payment confirmation
    updated = await confirm_payment(session, invoice)
    await session.commit()
    logger.info(
        "webhook_payment_confirmed",
        invoice_id=updated.invoice_id,
        new_state=updated.state,
    )
    return {
        "status": "ok",
        "invoice_id": updated.invoice_id,
        "state": updated.state,
    }
