"""Tests for the health and readiness endpoints.

The liveness test needs no database. The readiness test asserts the endpoint
returns a well-formed response and never raises, whether or not a DB is present.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_liveness(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_readiness_shape(client: AsyncClient) -> None:
    resp = await client.get("/health/ready")
    # 200 when a DB is reachable, 503 when not — both are valid, well-formed.
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "status" in body
    assert "database" in body
    if resp.status_code == 200:
        assert body["status"] == "ready"
        assert body["database"] == "ok"
    else:
        assert body["status"] == "not_ready"


async def test_config_defaults() -> None:
    from app.core.config import Settings

    # CORS_ORIGINS provided as a comma-separated string is split into a list.
    # Disable .env loading so the test is hermetic and asserts the parser only.
    settings = Settings(
        _env_file=None,
        cors_origins_raw="http://a.com, http://b.com",
    )
    assert settings.cors_origins == ["http://a.com", "http://b.com"]
    assert settings.is_development is True
