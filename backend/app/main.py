"""FastAPI application factory for CivicRoute AI (M0 foundation)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.core.config import get_settings


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

    # Health/readiness endpoints live outside the versioned API prefix.
    app.include_router(health_router)

    return app


app = create_app()
