"""Append-only audit log viewer."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.models.audit_log import AuditLog
from backend.schemas.audit import AuditEntryOut
from backend.schemas.common import Meta, SuccessEnvelope

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit(
    invoice_id: str | None = None,
    actor: str | None = None,
    from_state: str | None = None,
    to_state: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[AuditEntryOut]]:
    """Filterable audit log. There is no update or delete endpoint by design."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    if invoice_id:
        stmt = stmt.where(AuditLog.invoice_id == invoice_id)
        count_stmt = count_stmt.where(AuditLog.invoice_id == invoice_id)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
        count_stmt = count_stmt.where(AuditLog.actor == actor)
    if from_state:
        stmt = stmt.where(AuditLog.from_state == from_state)
        count_stmt = count_stmt.where(AuditLog.from_state == from_state)
    if to_state:
        stmt = stmt.where(AuditLog.to_state == to_state)
        count_stmt = count_stmt.where(AuditLog.to_state == to_state)
    if date_from:
        stmt = stmt.where(AuditLog.occurred_at >= date_from)
        count_stmt = count_stmt.where(AuditLog.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.occurred_at <= date_to)
        count_stmt = count_stmt.where(AuditLog.occurred_at <= date_to)
    total = await session.scalar(count_stmt)
    rows = await session.execute(
        stmt.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
    )
    return SuccessEnvelope(
        data=[AuditEntryOut.model_validate(row) for row in rows.scalars()],
        meta=Meta(total_count=int(total or 0)),
    )
