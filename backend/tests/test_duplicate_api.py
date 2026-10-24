"""API-level tests for duplicate detection: privacy and admin gating."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app

API = "/api"


@pytest.fixture
async def prod_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, app_env="production"
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://prod") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _submit(client: AsyncClient, city_id: int, title: str, desc: str) -> dict:
    return (
        await client.post(
            f"{API}/complaints",
            json={
                "city_id": city_id,
                "title": title,
                "description": desc,
                "reporter_name": "Jane Private",
                "reporter_email": "jane.private@example.com",
            },
        )
    ).json()


async def test_duplicate_candidates_exclude_pii(
    client: AsyncClient, boston_city_id: int
) -> None:
    a = await _submit(
        client,
        boston_city_id,
        "Large pothole on Dorchester Ave",
        "Dangerous deep pothole on Dorchester Ave near the bus stop damaging cars.",
    )
    await _submit(
        client,
        boston_city_id,
        "Pothole Dorchester Ave bus stop",
        "Big dangerous pothole on Dorchester Ave at the bus stop, cars damaged.",
    )

    resp = await client.post(f"{API}/duplicates/complaints/{a['id']}/detect")
    assert resp.status_code == 200
    candidates = resp.json()
    assert len(candidates) >= 1
    for c in candidates:
        # No reporter PII fields anywhere in the candidate payload.
        flat = str(c)
        assert "reporter" not in flat
        assert "jane.private@example.com" not in flat
        assert "Jane Private" not in flat
        assert set(c.keys()) == {
            "link_id",
            "candidate_complaint_id",
            "candidate_tracking_code",
            "candidate_title",
            "candidate_status",
            "similarity",
            "combined_score",
            "evidence",
            "decision",
        }


async def test_duplicate_endpoints_blocked_in_prod(prod_client: AsyncClient) -> None:
    assert (
        await prod_client.post(f"{API}/duplicates/complaints/1/detect")
    ).status_code == 403
    assert (
        await prod_client.get(f"{API}/duplicates/complaints/1/candidates")
    ).status_code == 403
    assert (
        await prod_client.post(
            f"{API}/duplicates/links/1/decision",
            json={"decision": "confirm"},
        )
    ).status_code == 403
