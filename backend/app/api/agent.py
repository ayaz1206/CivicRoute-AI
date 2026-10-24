"""Agent + human-review endpoints (admin-gated).

- Trigger triage for a complaint.
- Inspect agent runs, steps, evidence, and confidence (admin inspection UI).
- List the human review queue and approve/override/reject recommendations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_agent_service,
    get_review_service,
    require_admin,
)
from app.db.session import get_session
from app.models.agent import AgentRun
from app.schemas.agent import (
    AgentRunDetail,
    AgentRunRead,
    RecommendationRead,
    ReviewDecision,
)
from app.schemas.common import Page
from app.services.agent_service import AgentService
from app.services.review_service import ReviewService

router = APIRouter(
    prefix="/agent", tags=["agent"], dependencies=[Depends(require_admin)]
)


@router.post(
    "/complaints/{complaint_id}/triage",
    response_model=AgentRunDetail,
    summary="Run AI triage for a complaint",
)
async def run_triage(
    complaint_id: int,
    service: AgentService = Depends(get_agent_service),
    session: AsyncSession = Depends(get_session),
) -> AgentRunDetail:
    run = await service.run_triage(complaint_id)
    # Reload with steps + recommendation for the response.
    full = await session.scalar(
        select(AgentRun)
        .where(AgentRun.id == run.id)
        .options(
            selectinload(AgentRun.steps),
            selectinload(AgentRun.recommendation),
        )
    )
    return AgentRunDetail.model_validate(full)


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunDetail,
    summary="Inspect an agent run (steps, evidence, confidence)",
)
async def get_run(
    run_id: int,
    session: AsyncSession = Depends(get_session),
) -> AgentRunDetail:
    from fastapi import HTTPException

    run = await session.scalar(
        select(AgentRun)
        .where(AgentRun.id == run_id)
        .options(
            selectinload(AgentRun.steps),
            selectinload(AgentRun.recommendation),
        )
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRunDetail.model_validate(run)


@router.get(
    "/runs",
    response_model=Page[AgentRunRead],
    summary="List recent agent runs",
)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> Page[AgentRunRead]:
    from sqlalchemy import func

    total = await session.scalar(select(func.count()).select_from(AgentRun))
    rows = await session.scalars(
        select(AgentRun).order_by(AgentRun.id.desc()).limit(limit).offset(offset)
    )
    return Page[AgentRunRead](
        items=[AgentRunRead.model_validate(r) for r in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/review-queue",
    response_model=Page[RecommendationRead],
    summary="List pending AI recommendations awaiting human review",
)
async def review_queue(
    city_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ReviewService = Depends(get_review_service),
) -> Page[RecommendationRead]:
    items, total = await service.list_pending(
        city_id=city_id, limit=limit, offset=offset
    )
    return Page[RecommendationRead](
        items=[RecommendationRead.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/recommendations/{recommendation_id}/decision",
    response_model=RecommendationRead,
    summary="Approve, override, or reject a recommendation (staff)",
)
async def decide(
    recommendation_id: int,
    payload: ReviewDecision,
    service: ReviewService = Depends(get_review_service),
) -> RecommendationRead:
    rec = await service.decide(
        recommendation_id,
        decision=payload.decision,
        reviewer=payload.reviewer,
        category=payload.category,
        priority=payload.priority,
        department_slug=payload.department_slug,
        note=payload.note,
    )
    return RecommendationRead.model_validate(rec)
