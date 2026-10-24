"""Tests for human review of AI recommendations."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.agent import AgentRecommendation
from app.models.complaint import Complaint
from app.models.enums import ComplaintPriority, RecommendationStatus
from app.services.agent_service import AgentService
from app.services.errors import ValidationError
from app.services.review_service import ReviewService
from tests.fakes import ScriptedProvider


async def _recommendation_for(cid: int) -> int:
    async with async_session_factory() as session:
        await AgentService(session, llm=ScriptedProvider()).run_triage(cid)
    async with async_session_factory() as session:
        rec = await session.scalar(
            select(AgentRecommendation).where(AgentRecommendation.complaint_id == cid)
        )
        return rec.id


async def test_approve_applies_ai_values_to_complaint(make_complaint) -> None:
    cid = await make_complaint()
    rec_id = await _recommendation_for(cid)

    async with async_session_factory() as session:
        svc = ReviewService(session)
        rec = await svc.decide(rec_id, decision="approve", reviewer="alice")

    assert rec.status == RecommendationStatus.APPROVED
    assert rec.reviewer == "alice"

    async with async_session_factory() as session:
        complaint = await session.get(Complaint, cid)
        # Now the approved values are applied to the complaint.
        assert complaint.category == "Pothole"
        assert complaint.priority == ComplaintPriority.HIGH
        assert complaint.department_id is not None
        assert complaint.status.value == "triaged"


async def test_override_applies_corrected_values(make_complaint) -> None:
    cid = await make_complaint()
    rec_id = await _recommendation_for(cid)

    async with async_session_factory() as session:
        svc = ReviewService(session)
        rec = await svc.decide(
            rec_id,
            decision="override",
            reviewer="bob",
            category="Sidewalk",
            priority=ComplaintPriority.MEDIUM,
            department_slug="public-works",
            note="Reclassified after inspection",
        )

    assert rec.status == RecommendationStatus.OVERRIDDEN
    assert rec.final_category == "Sidewalk"
    assert rec.final_priority == ComplaintPriority.MEDIUM

    async with async_session_factory() as session:
        complaint = await session.get(Complaint, cid)
        assert complaint.category == "Sidewalk"
        assert complaint.priority == ComplaintPriority.MEDIUM


async def test_reject_does_not_touch_complaint(make_complaint) -> None:
    cid = await make_complaint()
    rec_id = await _recommendation_for(cid)

    async with async_session_factory() as session:
        rec = await ReviewService(session).decide(
            rec_id, decision="reject", reviewer="carol", note="duplicate of nearby case"
        )
    assert rec.status == RecommendationStatus.REJECTED

    async with async_session_factory() as session:
        complaint = await session.get(Complaint, cid)
        assert complaint.category is None
        assert complaint.status.value == "submitted"


async def test_double_decision_is_rejected(make_complaint) -> None:
    cid = await make_complaint()
    rec_id = await _recommendation_for(cid)

    async with async_session_factory() as session:
        await ReviewService(session).decide(rec_id, decision="approve", reviewer="x")

    async with async_session_factory() as session:
        with pytest.raises(ValidationError):
            await ReviewService(session).decide(rec_id, decision="approve", reviewer="x")


async def test_override_unknown_department_rejected(make_complaint) -> None:
    cid = await make_complaint()
    rec_id = await _recommendation_for(cid)

    async with async_session_factory() as session:
        with pytest.raises(ValidationError):
            await ReviewService(session).decide(
                rec_id,
                decision="override",
                reviewer="x",
                department_slug="nonexistent-dept",
            )


async def test_review_queue_lists_pending(make_complaint) -> None:
    cid = await make_complaint(
        title="Dark street light", description="The street light is out, very dark."
    )
    await _recommendation_for(cid)

    async with async_session_factory() as session:
        items, total = await ReviewService(session).list_pending()
    assert total >= 1
    assert all(r.status == RecommendationStatus.PENDING for r in items)
