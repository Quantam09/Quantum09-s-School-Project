"""Learn-and-Reward-LAR API — modular monolith (FastAPI).

Mission B scope implemented here: ``learning`` + ``ai_chat`` modules. The ``core``
package is a clearly-marked placeholder for Developer C's module; coin and RAG
adapters stand in for Developer C's ledger and Developer A's RAG index until those
modules are merged (see app/shared/coin_client.py and app/shared/rag_client.py).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core import router as core_router
from app.modules.learning import seed as learning_seed
from app.shared.config import get_settings
from app.shared.db import Base, get_engine, init_engine, strip_schemas_for_sqlite
from app.shared.errors import AppError, ErrorCode


def _build_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_engine(settings.database_url)
        if settings.database_url.startswith("sqlite"):
            strip_schemas_for_sqlite()
        if settings.auto_create_tables:
            Base.metadata.create_all(get_engine())
        db = Session(bind=get_engine())
        try:
            learning_seed.seed_if_empty(db)
            db.commit()
        finally:
            db.close()
        yield

    fastapi_app = FastAPI(
        title="Learn-and-Reward-LAR API",
        version="0.1.0",
        description=(
            "Modular monolith API. Mission B scope: learning + ai_chat modules "
            "(Developer B). Auth is a placeholder for Developer C's core module."
        ),
        lifespan=lifespan,
    )

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(core_router.router, prefix="/api/v1")
    from app.modules.learning import router as learning_router

    fastapi_app.include_router(learning_router.router, prefix="/api/v1")

    @fastapi_app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @fastapi_app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        error = AppError(
            ErrorCode.VALIDATION_ERROR,
            "Request validation failed.",
            status_code=422,
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=error.to_payload())

    @fastapi_app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    return fastapi_app


app = _build_app()
