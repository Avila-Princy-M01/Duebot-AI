"""Razorpay webhook handler with HMAC-SHA256 signature verification."""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.dependencies import get_db
from backend.engine.states import InvoiceState
from backend.integrations.razorpay import verify_webhook_signature
from backend.models.invoice import Invoice
from backend.tasks.payment import confirm_payment

logger = structlog.get_logger("duebot.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ALLOWED_SETTLEMENT_EVENTS = frozenset(
    {"payment_link.paid", "payment.captured", "order.paid"}
)


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_razorpay_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    """Process incoming Razorpay webhook events with HMAC-SHA256 verification.

    1. Enforces cryptographic signature verification on the raw request body (fails closed).
    2. Filters specifically for settlement events (payment_link.paid / payment.captured).
    3. Locates the invoice via standard nested Razorpay payload entities.
    4. Handles idempotent webhook retries safely if the invoice is already RECOVERED.
    5. Applies the deterministic PAYMENT_CONFIRMED lifecycle transition.
    """
    raw_body = await request.body()

    # 1. HMAC-SHA256 Signature Verification (fail closed if secret is not configured)
    secret = settings.razorpay_webhook_secret
    if not secret:
        logger.error("webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay webhook secret not configured",
        )

    if not x_razorpay_signature or not verify_webhook_signature(
        raw_body, x_razorpay_signature, secret
    ):
        logger.warning(
            "webhook_signature_verification_failed",
            signature_present=bool(x_razorpay_signature),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Razorpay-Signature header",
        )

    # 2. JSON Payload & Event Parsing
    try:
        body: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        logger.warning("invalid_webhook_json", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    event = body.get("event")
    logger.info(
        "webhook_received",
        webhook_event=event,
        verified=True,
    )

    # 3. Filter for settlement events only
    if event not in ALLOWED_SETTLEMENT_EVENTS:
        logger.info(
            "webhook_event_ignored_non_settlement",
            webhook_event=event,
        )
        return {
            "status": "ignored",
            "event": event,
            "reason": "non_settlement_event",
        }

    # 4. Extract target invoice from authentic Razorpay payload structures
    invoice: Invoice | None = None
    payload = body.get("payload")
    if isinstance(payload, dict):
        # A. Check payment_link entity
        pl_entity = payload.get("payment_link", {}).get("entity")
        if isinstance(pl_entity, dict):
            plink_id = pl_entity.get("id")
            if plink_id:
                res = await session.execute(
                    select(Invoice).where(Invoice.payment_link_id == str(plink_id))
                )
                invoice = res.scalar_one_or_none()

            if not invoice:
                notes = pl_entity.get("notes")
                if isinstance(notes, dict) and "invoice_id" in notes:
                    res = await session.execute(
                        select(Invoice).where(Invoice.invoice_id == str(notes["invoice_id"]))
                    )
                    invoice = res.scalar_one_or_none()

        # B. Check payment entity
        if not invoice:
            pay_entity = payload.get("payment", {}).get("entity")
            if isinstance(pay_entity, dict):
                notes = pay_entity.get("notes")
                if isinstance(notes, dict) and "invoice_id" in notes:
                    res = await session.execute(
                        select(Invoice).where(Invoice.invoice_id == str(notes["invoice_id"]))
                    )
                    invoice = res.scalar_one_or_none()

    if invoice is None:
        logger.warning("webhook_invoice_not_found", webhook_event=event)
        return {
            "status": "ignored",
            "event": event,
            "reason": "invoice_not_found",
        }

    # 5. Idempotent Retry Guard: If already RECOVERED, return 200 without duplicate transitions
    if invoice.state == InvoiceState.RECOVERED.value:
        logger.info(
            "webhook_invoice_already_recovered",
            invoice_id=invoice.invoice_id,
            webhook_event=event,
        )
        return {
            "status": "already_recovered",
            "event": event,
            "invoice_id": invoice.invoice_id,
            "state": invoice.state,
        }

    # 6. Apply deterministic state machine transition
    updated = await confirm_payment(session, invoice)
    await session.commit()
    logger.info(
        "webhook_payment_confirmed",
        invoice_id=updated.invoice_id,
        new_state=updated.state,
    )
    return {
        "status": "ok",
        "event": event,
        "invoice_id": updated.invoice_id,
        "state": updated.state,
    }
