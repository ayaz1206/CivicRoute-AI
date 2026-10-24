"""Duplicate-detection and clarification endpoints.

Duplicate detection + clarification *management* are admin-gated. Residents
answer clarification questions via a separate public, read/answer-only route
keyed by the complaint's tracking code (no PII, no browsing of other cases).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_clarification_service,
    get_duplicate_service,
    require_admin,
)
from app.db.session import get_session
from app.models.complaint import Complaint
from app.models.duplicate import DuplicateLink
from app.schemas.duplicate import (
    ClarificationAnswer,
    ClarificationRead,
    DuplicateCandidate,
    DuplicateDecisionIn,
    PublicClarification,
)
from app.services.clarification_service import ClarificationService
from app.services.duplicate_service import DuplicateService

# ---- Admin: duplicates + clarification management ----
admin_router = APIRouter(
    prefix="/duplicates", tags=["duplicates"], dependencies=[Depends(require_admin)]
)


async def _candidate_view(
    session: AsyncSession, links: list[DuplicateLink]
) -> list[DuplicateCandidate]:
    """Attach candidate complaint metadata (PII-free) to each link."""
    out: list[DuplicateCandidate] = []
    for link in links:
        cand = await session.get(Complaint, link.candidate_complaint_id)
        if cand is None:
            continue
        out.append(
            DuplicateCandidate(
                link_id=link.id,
                candidate_complaint_id=cand.id,
                candidate_tracking_code=cand.tracking_code,
                candidate_title=cand.title,
                candidate_status=cand.status.value,
                similarity=link.similarity,
                combined_score=link.combined_score,
                evidence=link.evidence,
                decision=link.decision,
            )
        )
    return out


@admin_router.post(
    "/complaints/{complaint_id}/detect",
    response_model=list[DuplicateCandidate],
    summary="Run semantic duplicate detection for a complaint",
)
async def detect(
    complaint_id: int,
    service: DuplicateService = Depends(get_duplicate_service),
    session: AsyncSession = Depends(get_session),
) -> list[DuplicateCandidate]:
    links = await service.find_candidates(complaint_id)
    return await _candidate_view(session, links)


@admin_router.get(
    "/complaints/{complaint_id}/candidates",
    response_model=list[DuplicateCandidate],
    summary="List possible-duplicate candidates for a complaint",
)
async def candidates(
    complaint_id: int,
    service: DuplicateService = Depends(get_duplicate_service),
    session: AsyncSession = Depends(get_session),
) -> list[DuplicateCandidate]:
    links = await service.list_candidates(complaint_id)
    return await _candidate_view(session, links)


@admin_router.post(
    "/links/{link_id}/decision",
    response_model=DuplicateCandidate,
    summary="Confirm or reject a possible duplicate (never auto-merges)",
)
async def decide_duplicate(
    link_id: int,
    payload: DuplicateDecisionIn,
    service: DuplicateService = Depends(get_duplicate_service),
    session: AsyncSession = Depends(get_session),
) -> DuplicateCandidate:
    link = await service.decide(
        link_id, decision=payload.decision, reviewer=payload.reviewer, note=payload.note
    )
    view = await _candidate_view(session, [link])
    return view[0]


@admin_router.post(
    "/complaints/{complaint_id}/clarifications/generate",
    response_model=list[ClarificationRead],
    summary="Generate clarification questions for missing info",
)
async def generate_clarifications(
    complaint_id: int,
    service: ClarificationService = Depends(get_clarification_service),
) -> list[ClarificationRead]:
    created = await service.generate_for_complaint(complaint_id)
    return [ClarificationRead.model_validate(c) for c in created]


@admin_router.get(
    "/complaints/{complaint_id}/clarifications",
    response_model=list[ClarificationRead],
    summary="List clarifications for a complaint (staff view)",
)
async def list_clarifications(
    complaint_id: int,
    service: ClarificationService = Depends(get_clarification_service),
) -> list[ClarificationRead]:
    items = await service.list_for_complaint(complaint_id)
    return [ClarificationRead.model_validate(c) for c in items]


# ---- Public: residents answer clarifications by tracking code ----
public_router = APIRouter(prefix="/clarifications", tags=["clarifications"])


@public_router.get(
    "/track/{tracking_code}",
    response_model=list[PublicClarification],
    summary="List a complaint's pending clarification questions (resident)",
)
async def public_list(
    tracking_code: str,
    service: ClarificationService = Depends(get_clarification_service),
    session: AsyncSession = Depends(get_session),
) -> list[PublicClarification]:
    complaint = await session.scalar(
        select(Complaint).where(Complaint.tracking_code == tracking_code.strip().upper())
    )
    if complaint is None:
        raise HTTPException(status_code=404, detail="No complaint for that code")
    items = await service.list_for_complaint(complaint.id, pending_only=True)
    return [PublicClarification.model_validate(c) for c in items]


@public_router.post(
    "/{clarification_id}/answer",
    response_model=PublicClarification,
    summary="Answer a clarification question (resident)",
)
async def public_answer(
    clarification_id: int,
    payload: ClarificationAnswer,
    service: ClarificationService = Depends(get_clarification_service),
) -> PublicClarification:
    clar = await service.answer(clarification_id, payload.answer)
    return PublicClarification.model_validate(clar)
