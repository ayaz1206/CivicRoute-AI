"""API-level tests for agent + review endpoints (HTTP + admin gating)."""

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


async def _submit(client: AsyncClient, city_id: int) -> int:
    resp = await client.post(
        f"{API}/complaints",
        json={
            "city_id": city_id,
            "title": "Streetlight out on Elm",
            "description": "The street light has been dark for a week; unsafe at night.",
        },
    )
    return resp.json()["id"]


async def test_triage_and_review_flow(client: AsyncClient, boston_city_id: int) -> None:
    cid = await _submit(client, boston_city_id)

    # Run triage (dev mode -> admin allowed).
    triage = await client.post(f"{API}/agent/complaints/{cid}/triage")
    assert triage.status_code == 200
    body = triage.json()
    assert body["status"] in ("completed", "needs_review")
    assert body["recommendation"] is not None
    assert len(body["steps"]) == 4  # extract, classify, prioritize, route
    rec_id = body["recommendation"]["id"]

    # Inspect the run (admin inspection endpoint).
    run_id = body["id"]
    run = await client.get(f"{API}/agent/runs/{run_id}")
    assert run.status_code == 200
    assert "routing_evidence" in run.json()["recommendation"]

    # Approve via the review endpoint.
    decision = await client.post(
        f"{API}/agent/recommendations/{rec_id}/decision",
        json={"decision": "approve", "reviewer": "tester"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"


async def test_agent_endpoints_blocked_in_prod(prod_client: AsyncClient) -> None:
    assert (await prod_client.post(f"{API}/agent/complaints/1/triage")).status_code == 403
    assert (await prod_client.get(f"{API}/agent/runs/1")).status_code == 403
    assert (await prod_client.get(f"{API}/agent/review-queue")).status_code == 403
    assert (
        await prod_client.post(
            f"{API}/agent/recommendations/1/decision",
            json={"decision": "approve"},
        )
    ).status_code == 403
