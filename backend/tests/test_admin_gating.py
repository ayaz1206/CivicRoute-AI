"""Tests that staff/admin mutation endpoints are gated outside development.

The resident-facing endpoints (submit, track) must remain available; only the
staff listing and mutation endpoints are disabled when admin access is off.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app

API = "/api"


@pytest.fixture
async def prod_client() -> AsyncGenerator[AsyncClient, None]:
    """A client whose app behaves as a non-development deployment."""
    app = create_app()

    def _prod_settings() -> Settings:
        # Simulate production: admin endpoints disabled by default.
        return Settings(_env_file=None, app_env="production")

    app.dependency_overrides[get_settings] = _prod_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://prod") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_admin_list_blocked_in_prod(prod_client: AsyncClient) -> None:
    resp = await prod_client.get(f"{API}/complaints", params={"city_id": 1})
    assert resp.status_code == 403


async def test_admin_status_update_blocked_in_prod(prod_client: AsyncClient) -> None:
    resp = await prod_client.post(f"{API}/complaints/1/status", json={"status": "triaged"})
    assert resp.status_code == 403


async def test_admin_assignment_blocked_in_prod(prod_client: AsyncClient) -> None:
    resp = await prod_client.patch(
        f"{API}/complaints/1/assignment", json={"category": "pothole"}
    )
    assert resp.status_code == 403


async def test_admin_detail_blocked_in_prod(prod_client: AsyncClient) -> None:
    resp = await prod_client.get(f"{API}/complaints/1")
    assert resp.status_code == 403


async def test_tracking_remains_public_in_prod(
    prod_client: AsyncClient, boston_city_id: int
) -> None:
    """Resident tracking stays available even when admin is disabled."""
    # Submission is a resident action and must also remain available.
    submit = await prod_client.post(
        f"{API}/complaints",
        json={
            "city_id": boston_city_id,
            "title": "Broken bench in the park",
            "description": "A park bench is broken and has sharp edges.",
        },
    )
    assert submit.status_code == 201
    code = submit.json()["tracking_code"]

    track = await prod_client.get(f"{API}/complaints/track/{code}")
    assert track.status_code == 200
    assert "reporter_email" not in track.json()


def test_settings_admin_gate_defaults() -> None:
    assert Settings(_env_file=None, app_env="development").admin_endpoints_enabled is True
    assert Settings(_env_file=None, app_env="production").admin_endpoints_enabled is False
    # Explicit override wins over APP_ENV.
    forced = Settings(_env_file=None, app_env="production", allow_unauthenticated_admin=True)
    assert forced.admin_endpoints_enabled is True
