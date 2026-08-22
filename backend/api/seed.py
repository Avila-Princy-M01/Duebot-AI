"""POST /api/seed — load generator output into the database."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.seed import seed_from_generator
from backend.dependencies import get_db
from backend.schemas.common import SuccessEnvelope

router = APIRouter(tags=["seed"])


@router.post("/seed")
async def seed(
    session: AsyncSession = Depends(get_db),
    num_invoices: int = 80,
    seed: int = 42,
) -> SuccessEnvelope[dict[str, int]]:
    """Generate and insert a reproducible synthetic batch."""
    counts = await seed_from_generator(session, num_invoices=num_invoices, seed=seed)
    return SuccessEnvelope(data=counts)
