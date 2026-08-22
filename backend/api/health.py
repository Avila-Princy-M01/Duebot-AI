"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas.common import SuccessEnvelope

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> SuccessEnvelope[dict[str, str]]:
    """Liveness probe."""
    return SuccessEnvelope(data={"status": "ok"})
