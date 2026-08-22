"""Promise routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.dependencies import get_db
from backend.exceptions import NotFoundError
from backend.models.promise import Promise
from backend.schemas.common import Meta, SuccessEnvelope
from backend.schemas.promise import PromiseDetail, PromiseOut

router = APIRouter(prefix="/promises", tags=["promises"])


@router.get("")
async def list_promises(
    status: str | None = None,
    invoice_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[list[PromiseOut]]:
    """Filterable promises."""
    stmt = select(Promise)
    count_stmt = select(func.count()).select_from(Promise)
    if status:
        stmt = stmt.where(Promise.status == status)
        count_stmt = count_stmt.where(Promise.status == status)
    if invoice_id:
        stmt = stmt.where(Promise.invoice_id == invoice_id)
        count_stmt = count_stmt.where(Promise.invoice_id == invoice_id)
    total = await session.scalar(count_stmt)
    rows = await session.execute(stmt.offset(offset).limit(limit))
    return SuccessEnvelope(
        data=[PromiseOut.model_validate(p) for p in rows.scalars()],
        meta=Meta(total_count=int(total or 0)),
    )


@router.get("/{promise_id}")
async def get_promise(
    promise_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[PromiseDetail]:
    """Promise plus source interaction."""
    stmt = (
        select(Promise)
        .where(Promise.id == promise_id)
        .options(selectinload(Promise.source_interaction))
    )
    promise = (await session.execute(stmt)).scalar_one_or_none()
    if promise is None:
        raise NotFoundError(f"promise {promise_id} not found")
    return SuccessEnvelope(data=PromiseDetail.model_validate(promise))
