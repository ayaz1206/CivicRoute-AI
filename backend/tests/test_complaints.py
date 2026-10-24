"""API tests for the M1 complaint lifecycle.

These exercise the full HTTP path against the real (Dockerized) database, so the
DB must be running and migrated. The `boston_city_id` fixture seeds a clean
tenant and clears live complaints between tests.
"""

from __future__ import annotations

from httpx import AsyncClient

API = "/api"


async def _submit(client: AsyncClient, city_id: int, **overrides) -> dict:
    payload = {
        "city_id": city_id,
        "title": "Large pothole on Main St",
        "description": "There is a deep pothole near the crosswalk that is a hazard.",
        "reporter_name": "Jane Resident",
        "reporter_email": "jane@example.com",
        "location_text": "Main St & 1st Ave",
    }
    payload.update(overrides)
    resp = await client.post(f"{API}/complaints", json=payload)
    return resp


async def test_submit_complaint_returns_tracking_code(
    client: AsyncClient, boston_city_id: int
) -> None:
    resp = await _submit(client, boston_city_id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["tracking_code"].startswith("CR-")
    assert body["status"] == "submitted"


async def test_submit_rejects_short_title(
    client: AsyncClient, boston_city_id: int
) -> None:
    resp = await _submit(client, boston_city_id, title="x")
    assert resp.status_code == 422  # pydantic validation


async def test_submit_unknown_city_is_404(client: AsyncClient) -> None:
    resp = await _submit(client, 999999)
    assert resp.status_code == 404


async def test_track_by_code_includes_timeline(
    client: AsyncClient, boston_city_id: int
) -> None:
    code = (await _submit(client, boston_city_id)).json()["tracking_code"]
    resp = await client.get(f"{API}/complaints/track/{code}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracking_code"] == code
    # Initial creation event is recorded.
    assert len(body["status_history"]) == 1
    assert body["status_history"][0]["to_status"] == "submitted"
    assert body["status_history"][0]["from_status"] is None


async def test_track_response_excludes_resident_pii(
    client: AsyncClient, boston_city_id: int
) -> None:
    """The public tracking endpoint must not leak reporter name/email."""
    code = (await _submit(client, boston_city_id)).json()["tracking_code"]
    body = (await client.get(f"{API}/complaints/track/{code}")).json()
    assert "reporter_name" not in body
    assert "reporter_email" not in body


async def test_track_unknown_code_is_404(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/complaints/track/CR-NOPE0000")
    assert resp.status_code == 404


async def test_status_transition_valid_and_recorded(
    client: AsyncClient, boston_city_id: int
) -> None:
    cid = (await _submit(client, boston_city_id)).json()["id"]

    r1 = await client.post(
        f"{API}/complaints/{cid}/status",
        json={"status": "triaged", "note": "Routing to Public Works"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "triaged"

    r2 = await client.post(f"{API}/complaints/{cid}/status", json={"status": "in_progress"})
    assert r2.status_code == 200

    r3 = await client.post(f"{API}/complaints/{cid}/status", json={"status": "resolved"})
    assert r3.status_code == 200
    body = r3.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None
    # submitted -> triaged -> in_progress -> resolved = 1 initial + 3 changes
    assert len(body["status_history"]) == 4


async def test_illegal_status_transition_is_409(
    client: AsyncClient, boston_city_id: int
) -> None:
    cid = (await _submit(client, boston_city_id)).json()["id"]
    # submitted -> resolved is not allowed (must pass through in_progress).
    resp = await client.post(f"{API}/complaints/{cid}/status", json={"status": "resolved"})
    assert resp.status_code == 409


async def test_manual_assignment(client: AsyncClient, boston_city_id: int) -> None:
    cid = (await _submit(client, boston_city_id)).json()["id"]
    # Fetch the seeded department.
    depts = (await client.get(f"{API}/cities/{boston_city_id}/departments")).json()
    dept_id = depts[0]["id"]

    resp = await client.patch(
        f"{API}/complaints/{cid}/assignment",
        json={"category": "pothole", "priority": "high", "department_id": dept_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "pothole"
    assert body["priority"] == "high"
    assert body["department_id"] == dept_id


async def test_list_returns_only_live_and_paginates(
    client: AsyncClient, boston_city_id: int
) -> None:
    for _ in range(3):
        await _submit(client, boston_city_id)

    resp = await client.get(f"{API}/complaints", params={"city_id": boston_city_id, "limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    # All listed complaints are live web submissions (311 imports excluded).
    assert all(item["source"] == "web" for item in body["items"])


async def test_list_filter_by_status(client: AsyncClient, boston_city_id: int) -> None:
    cid = (await _submit(client, boston_city_id)).json()["id"]
    await _submit(client, boston_city_id)
    await client.post(f"{API}/complaints/{cid}/status", json={"status": "triaged"})

    resp = await client.get(
        f"{API}/complaints", params={"city_id": boston_city_id, "status": "triaged"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "triaged"
