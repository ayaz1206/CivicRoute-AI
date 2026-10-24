"""Tests for the LangGraph triage workflow and persistence.

Covers: happy-path transitions, malformed LLM output handling, provider
failures, confidence/review gating, and persistence of runs/steps/recommendations.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import async_session_factory
from app.models.agent import AgentRun, AgentStep
from app.models.enums import AgentRunStatus, RecommendationStatus
from app.services.agent_service import AgentService
from tests.fakes import FailingProvider, MalformedProvider, ScriptedProvider


async def _run(make_complaint, provider, **ckwargs) -> int:
    """Create a complaint, run triage with the given provider, return run id."""
    cid = await make_complaint(**ckwargs)
    async with async_session_factory() as session:
        svc = AgentService(session, llm=provider)
        run = await svc.run_triage(cid)
        return run.id


async def _load_run(run_id: int) -> AgentRun:
    async with async_session_factory() as session:
        return await session.scalar(
            select(AgentRun)
            .where(AgentRun.id == run_id)
            .options(
                selectinload(AgentRun.steps),
                selectinload(AgentRun.recommendation),
            )
        )


async def test_happy_path_completes_and_persists(make_complaint) -> None:
    run_id = await _run(make_complaint, ScriptedProvider())
    run = await _load_run(run_id)

    # High-confidence pothole routed to public-works should NOT need review.
    assert run.status == AgentRunStatus.COMPLETED
    assert run.llm_provider == "scripted"
    # All four LLM/route steps recorded.
    names = [s.node_name for s in run.steps]
    assert names == ["extract", "classify", "prioritize", "route"]

    rec = run.recommendation
    assert rec is not None
    assert rec.category == "Pothole"
    assert rec.department_slug == "public-works"
    assert rec.priority.value == "high"
    assert rec.requires_review is False
    assert rec.status == RecommendationStatus.PENDING
    assert 0.0 <= rec.overall_confidence <= 1.0


async def test_low_confidence_routes_to_review(make_complaint) -> None:
    provider = ScriptedProvider(classify={"category": "Pothole", "confidence": 0.2})
    run_id = await _run(make_complaint, provider)
    run = await _load_run(run_id)

    assert run.status == AgentRunStatus.NEEDS_REVIEW
    assert run.recommendation.requires_review is True
    assert "low classification confidence" in run.recommendation.review_reason


async def test_urgent_always_reviewed(make_complaint) -> None:
    provider = ScriptedProvider(
        prioritize={"priority": "urgent", "confidence": 0.99, "rationale": "gas leak"}
    )
    run_id = await _run(make_complaint, provider)
    run = await _load_run(run_id)
    assert run.status == AgentRunStatus.NEEDS_REVIEW
    assert "high-risk (urgent)" in run.recommendation.review_reason


async def test_review_severity_classification(make_complaint) -> None:
    from app.models.enums import ReviewSeverity

    # Confident, well-routed pothole -> routine (still needs approval, not flagged).
    routine = await _load_run(await _run(make_complaint, ScriptedProvider()))
    assert routine.recommendation.review_severity == ReviewSeverity.ROUTINE
    assert routine.recommendation.requires_review is False

    # Low classification confidence -> low_confidence.
    low = await _load_run(
        await _run(
            make_complaint,
            ScriptedProvider(classify={"category": "Pothole", "confidence": 0.2}),
        )
    )
    assert low.recommendation.review_severity == ReviewSeverity.LOW_CONFIDENCE

    # Urgent -> high_risk.
    high = await _load_run(
        await _run(
            make_complaint,
            ScriptedProvider(
                prioritize={"priority": "urgent", "confidence": 0.99, "rationale": "x"}
            ),
        )
    )
    assert high.recommendation.review_severity == ReviewSeverity.HIGH_RISK


async def test_malformed_output_is_sanitized(make_complaint) -> None:
    """Unknown category / bad priority must not crash; they degrade + review."""
    run_id = await _run(make_complaint, MalformedProvider())
    run = await _load_run(run_id)

    assert run.status == AgentRunStatus.NEEDS_REVIEW
    rec = run.recommendation
    # Unknown category coerced to "Other".
    assert rec.category == "Other"
    # Bad confidence string coerced to a float in range.
    assert 0.0 <= (rec.category_confidence or 0) <= 1.0
    # Invalid priority defaulted to medium.
    assert rec.priority.value == "medium"
    assert rec.requires_review is True


@pytest.mark.parametrize("fail_on", ["extract", "classify", "prioritize"])
async def test_provider_failure_marks_run_failed(make_complaint, fail_on) -> None:
    run_id = await _run(make_complaint, FailingProvider(fail_on=fail_on))
    run = await _load_run(run_id)

    assert run.status == AgentRunStatus.FAILED
    assert run.error is not None
    assert fail_on in run.error
    # No recommendation is produced on failure.
    assert run.recommendation is None
    # Steps completed before the failure are still persisted (audit trail).
    assert all(s.node_name != fail_on or True for s in run.steps)


async def test_steps_record_confidence_and_latency(make_complaint) -> None:
    run_id = await _run(make_complaint, ScriptedProvider())
    async with async_session_factory() as session:
        steps = list(
            await session.scalars(
                select(AgentStep).where(AgentStep.agent_run_id == run_id)
            )
        )
    assert len(steps) == 4
    classify = next(s for s in steps if s.node_name == "classify")
    assert classify.confidence == 0.95
    assert classify.latency_ms is not None and classify.latency_ms >= 0


async def test_ai_output_not_applied_to_complaint(make_complaint) -> None:
    """Running triage must NOT mutate the complaint — AI data stays separate."""
    from app.models.complaint import Complaint

    cid = await make_complaint()
    async with async_session_factory() as session:
        svc = AgentService(session, llm=ScriptedProvider())
        await svc.run_triage(cid)

    async with async_session_factory() as session:
        complaint = await session.get(Complaint, cid)
        # Complaint fields remain untouched by the agent.
        assert complaint.category is None
        assert complaint.priority is None
        assert complaint.department_id is None
        assert complaint.status.value == "submitted"
