"""Human review of AI recommendations.

Staff approve (accept the AI proposal as-is), override (supply corrected
values), or reject (discard). Only on approve/override are values applied to the
complaint — this is the single point where AI-derived data crosses into final
complaint data, and it always carries a human actor.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import AgentRecommendation
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.enums import ComplaintPriority, ComplaintStatus, RecommendationStatus
from app.models.status_history import StatusHistory
from app.services.errors import NotFoundError, ValidationError


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_pending(
        self, *, city_id: int | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[AgentRecommendation], int]:
        from sqlalchemy import func

        base = (
            select(AgentRecommendation)
            .join(Complaint, Complaint.id == AgentRecommendation.complaint_id)
            .where(AgentRecommendation.status == RecommendationStatus.PENDING)
        )
        if city_id is not None:
            base = base.where(Complaint.city_id == city_id)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = await self.session.scalars(
            base.order_by(AgentRecommendation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows), int(total or 0)

    async def get(self, recommendation_id: int) -> AgentRecommendation:
        rec = await self.session.scalar(
            select(AgentRecommendation)
            .where(AgentRecommendation.id == recommendation_id)
            .options(selectinload(AgentRecommendation.run))
        )
        if rec is None:
            raise NotFoundError(f"Recommendation {recommendation_id} not found")
        return rec

    async def _department_id(self, city_id: int, slug: str | None) -> int | None:
        if slug is None:
            return None
        dept_id = await self.session.scalar(
            select(Department.id).where(
                Department.city_id == city_id, Department.slug == slug
            )
        )
        if dept_id is None:
            raise ValidationError(f"Unknown department slug '{slug}' for this city")
        return dept_id

    async def decide(
        self,
        recommendation_id: int,
        *,
        decision: str,
        reviewer: str,
        category: str | None = None,
        priority: ComplaintPriority | None = None,
        department_slug: str | None = None,
        note: str | None = None,
    ) -> AgentRecommendation:
        rec = await self.get(recommendation_id)
        if rec.status != RecommendationStatus.PENDING:
            raise ValidationError(
                f"Recommendation already {rec.status.value}"
            )

        if decision == "reject":
            rec.status = RecommendationStatus.REJECTED
            rec.reviewer = reviewer
            rec.reviewed_at = dt.datetime.now(dt.UTC)
            rec.review_note = note
            await self.session.commit()
            await self.session.refresh(rec)
            return rec

        if decision not in ("approve", "override"):
            raise ValidationError("decision must be approve, override, or reject")

        # Resolve final values: approve uses AI proposal; override uses provided.
        if decision == "approve":
            final_category = rec.category
            final_priority = rec.priority
            final_slug = rec.department_slug
            rec.status = RecommendationStatus.APPROVED
        else:  # override
            final_category = category if category is not None else rec.category
            final_priority = priority if priority is not None else rec.priority
            final_slug = (
                department_slug if department_slug is not None else rec.department_slug
            )
            rec.status = RecommendationStatus.OVERRIDDEN

        complaint = await self.session.scalar(
            select(Complaint)
            .where(Complaint.id == rec.complaint_id)
            .options(selectinload(Complaint.status_history))
        )
        if complaint is None:
            raise NotFoundError("Complaint for recommendation no longer exists")

        dept_id = await self._department_id(complaint.city_id, final_slug)

        # Apply final (human-approved) values to the complaint.
        complaint.category = final_category
        complaint.priority = final_priority
        complaint.department_id = dept_id
        if complaint.status == ComplaintStatus.SUBMITTED:
            complaint.status = ComplaintStatus.TRIAGED
            complaint.status_history.append(
                StatusHistory(
                    from_status=ComplaintStatus.SUBMITTED,
                    to_status=ComplaintStatus.TRIAGED,
                    actor=reviewer,
                    note=f"AI recommendation {decision}d",
                )
            )

        # Record the final approved values on the recommendation (audit).
        rec.reviewer = reviewer
        rec.reviewed_at = dt.datetime.now(dt.UTC)
        rec.final_category = final_category
        rec.final_priority = final_priority
        rec.final_department_slug = final_slug
        rec.review_note = note

        await self.session.commit()
        await self.session.refresh(rec)
        return rec
