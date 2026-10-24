"""Health and readiness endpoints.

- `/health` is a liveness probe: it returns OK if the process is running.
- `/health/ready` is a readiness probe: it verifies database connectivity.

Both live outside the versioned API prefix so infra probes have a stable path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
async def health() -> dict[str, str]:
    """Return basic liveness information."""
    return {"status": "ok", "version": __version__}


@router.get("/health/ready", summary="Readiness check (verifies DB)")
async def readiness(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Verify the database is reachable.

    Returns 200 when the database responds, 503 otherwise. The endpoint never
    raises; it reports the dependency status in the response body.
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report any failure as not-ready
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable", "detail": str(exc)},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "database": "ok"},
    )
