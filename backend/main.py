"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import get_settings
from backend.db import Base, create_engine, session_factory
from backend.exceptions import DueBotError, NotFoundError, PolicyBlockedError
from backend.logging_util import configure_logging
from backend.schemas.common import ErrorBody, ErrorEnvelope


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the engine and (for SQLite/dev) create tables."""
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = session_factory(engine)
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Build the DueBot API."""
    settings = get_settings()
    app = FastAPI(title="DueBot", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.api.assistant import router as assistant_router
    from backend.api.audit import router as audit_router
    from backend.api.buyers import router as buyers_router
    from backend.api.health import router as health_router
    from backend.api.inbox import router as inbox_router
    from backend.api.invoices import router as invoices_router
    from backend.api.merchants import router as merchants_router
    from backend.api.metrics import router as metrics_router
    from backend.api.nudge import router as nudge_router
    from backend.api.promises import router as promises_router
    from backend.api.seed import router as seed_router
    from backend.api.webhooks import router as webhooks_router

    app.include_router(health_router, prefix="/api")
    app.include_router(assistant_router, prefix="/api")
    app.include_router(merchants_router, prefix="/api")
    app.include_router(buyers_router, prefix="/api")
    app.include_router(invoices_router, prefix="/api")
    app.include_router(promises_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    app.include_router(inbox_router, prefix="/api")
    app.include_router(metrics_router, prefix="/api")
    app.include_router(nudge_router, prefix="/api")
    app.include_router(seed_router, prefix="/api")
    app.include_router(webhooks_router, prefix="/api")

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        body = ErrorEnvelope(error=ErrorBody(code="not_found", message=str(exc)))
        return JSONResponse(status_code=404, content=body.model_dump(mode="json"))

    @app.exception_handler(PolicyBlockedError)
    async def policy_handler(_request: Request, exc: PolicyBlockedError) -> JSONResponse:
        body = ErrorEnvelope(error=ErrorBody(code="policy_blocked", message=str(exc)))
        return JSONResponse(status_code=409, content=body.model_dump(mode="json"))

    @app.exception_handler(DueBotError)
    async def domain_handler(_request: Request, exc: DueBotError) -> JSONResponse:
        body = ErrorEnvelope(error=ErrorBody(code="duebot_error", message=str(exc)))
        return JSONResponse(status_code=400, content=body.model_dump(mode="json"))

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        body = ErrorEnvelope(
            error=ErrorBody(
                code="http_error", message=str(exc.detail), details={"status": exc.status_code}
            )
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        body = ErrorEnvelope(
            error=ErrorBody(
                code="validation_error",
                message="Request validation failed",
                details={"errors": exc.errors()},
            )
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    return app


app = create_app()
