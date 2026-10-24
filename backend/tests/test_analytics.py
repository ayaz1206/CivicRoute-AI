"""Tests for the analytics API over historical 311 data."""

from __future__ import annotations

import datetime as dt

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.db.session import async_session_factory
from app.models.historical_request import Historical311Request

API = "/api"


@pytest.fixture
async def seeded_historical(boston_city_id: int):
    """Seed a small, deterministic set of historical rows for Boston.

    Note: analytics resolves the city by slug 'boston'; the boston_city_id
    fixture provides 'boston-test', so we look up / rely on the real Boston
    seed. Here we insert against the test city and query by its slug.
    """
    async with async_session_factory() as session:
        await session.execute(delete(Historical311Request))
        base = dt.datetime(2025, 6, 1, 12, 0, 0)
        rows = [
            Historical311Request(
                city_id=boston_city_id,
                case_enquiry_id=f"a-{i}",
                reason="Street Cleaning" if i % 2 == 0 else "Pothole",
                department="PWDx",
                neighborhood="Fenway" if i < 3 else "Dorchester",
                case_status="Closed" if i % 2 == 0 else "Open",
                opened_at=base + dt.timedelta(days=i),
                closed_at=(base + dt.timedelta(days=i, hours=5)) if i % 2 == 0 else None,
            )
            for i in range(6)
        ]
        session.add_all(rows)
        await session.commit()
    yield boston_city_id
    async with async_session_factory() as session:
        await session.execute(delete(Historical311Request))
        await session.commit()


async def test_overview_unknown_city_404(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/analytics/overview", params={"city": "atlantis"})
    assert resp.status_code == 404


async def test_overview_aggregates(
    client: AsyncClient, seeded_historical: int
) -> None:
    # The seeded rows are attached to the 'boston-test' city slug.
    resp = await client.get(
        f"{API}/analytics/overview", params={"city": "boston-test", "trend_days": 365}
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["summary"]["total"] == 6
    assert body["summary"]["open"] == 3
    assert body["summary"]["closed"] == 3
    assert body["summary"]["avg_resolution_hours"] == 5.0

    reasons = {item["key"]: item["count"] for item in body["by_category"]}
    assert reasons["Street Cleaning"] == 3
    assert reasons["Pothole"] == 3

    neighborhoods = {i["key"]: i["count"] for i in body["by_neighborhood"]}
    assert neighborhoods["Fenway"] == 3
    assert neighborhoods["Dorchester"] == 3

    # Trend has one point per distinct opened day.
    assert len(body["trend"]) == 6
