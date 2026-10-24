"""Tests for the clarification loop and resumable persistence."""

from __future__ import annotations

from httpx import AsyncClient

from app.db.session import async_session_factory
from app.models.complaint import Complaint
from app.models.enums import ClarificationStatus
from app.services.clarification_service import ClarificationService

API = "/api"


async def test_detects_missing_location_and_detail(make_complaint) -> None:
    # Valid at creation (>=3 title, >=10 desc) but below the 40-char detail
    # threshold and with no location -> both "location" and "detail" missing.
    cid = await make_complaint(title="Problem", description="It is broken now.")
    async with async_session_factory() as session:
        created = await ClarificationService(session).generate_for_complaint(cid)
    fields = {c.field for c in created}
    assert "location" in fields
    assert "detail" in fields


async def test_no_questions_when_complete(make_complaint) -> None:
    cid = await make_complaint(
        title="Detailed report",
        description="A large and dangerous pothole has formed on the road near "
        "the intersection and it keeps growing every day.",
    )
    # Give it a location.
    async with async_session_factory() as session:
        c = await session.get(Complaint, cid)
        c.location_text = "Main St & 1st Ave"
        await session.commit()
    async with async_session_factory() as session:
        created = await ClarificationService(session).generate_for_complaint(cid)
    assert created == []


async def test_generate_is_idempotent_while_pending(make_complaint) -> None:
    cid = await make_complaint(title="Issue", description="broken thing")
    async with async_session_factory() as session:
        first = await ClarificationService(session).generate_for_complaint(cid)
    async with async_session_factory() as session:
        second = await ClarificationService(session).generate_for_complaint(cid)
    # No duplicate pending questions created on the second call.
    assert len(first) >= 1
    assert second == []


async def test_answer_persists_and_fills_location(make_complaint) -> None:
    cid = await make_complaint(title="Issue", description="broken thing")
    async with async_session_factory() as session:
        created = await ClarificationService(session).generate_for_complaint(cid)
    loc_q = next(c for c in created if c.field == "location")

    async with async_session_factory() as session:
        answered = await ClarificationService(session).answer(
            loc_q.id, "123 Beacon St, near the park"
        )
    assert answered.status == ClarificationStatus.ANSWERED
    assert answered.answer == "123 Beacon St, near the park"

    # Location answer stored as resident-provided TEXT (no coordinates invented).
    async with async_session_factory() as session:
        c = await session.get(Complaint, cid)
    assert c.location_text == "123 Beacon St, near the park"
    assert c.latitude is None and c.longitude is None


async def test_public_answer_flow_over_http(
    client: AsyncClient, make_complaint
) -> None:
    cid = await make_complaint(title="Issue", description="broken thing")
    # Generate via the service (admin path).
    async with async_session_factory() as session:
        await ClarificationService(session).generate_for_complaint(cid)
        c = await session.get(Complaint, cid)
        code = c.tracking_code

    # Resident lists pending questions by tracking code.
    listed = await client.get(f"{API}/clarifications/track/{code}")
    assert listed.status_code == 200
    questions = listed.json()
    assert len(questions) >= 1
    # Public view exposes no internal metadata beyond id/field/question/status.
    assert set(questions[0].keys()) == {"id", "field", "question", "status"}

    qid = questions[0]["id"]
    answered = await client.post(
        f"{API}/clarifications/{qid}/answer", json={"answer": "More detail here."}
    )
    assert answered.status_code == 200
    assert answered.json()["status"] == "answered"


async def test_answer_rejects_empty(make_complaint) -> None:
    import pytest

    from app.services.errors import ValidationError

    cid = await make_complaint(title="Issue", description="broken thing here")
    async with async_session_factory() as session:
        created = await ClarificationService(session).generate_for_complaint(cid)
    qid = created[0].id
    async with async_session_factory() as session:
        with pytest.raises(ValidationError):
            await ClarificationService(session).answer(qid, "   ")
