"""FastAPI application factory for CivicRoute AI (M0 foundation)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.analytics import router as analytics_router
from app.api.cities import router as cities_router
from app.api.complaints import router as complaints_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.services.errors import NotFoundError, ValidationError


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="CivicRoute AI API",
        version=__version__,
        description=(
            "Agentic AI smart city complaint management platform. "
            "M0 foundation: health checks only."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Map domain errors to HTTP responses so the service layer stays HTTP-agnostic.
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _invalid(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    # Health/readiness endpoints live outside the versioned API prefix.
    app.include_router(health_router)

    # Versioned domain API.
    app.include_router(complaints_router, prefix=settings.api_prefix)
    app.include_router(cities_router, prefix=settings.api_prefix)
    app.include_router(analytics_router, prefix=settings.api_prefix)

    return app


app = create_app()
