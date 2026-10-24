"""Persist and resolve clarification questions.

The workflow is resumable: questions are stored with status PENDING; a resident
answers via the public endpoint (ANSWERED). When a location answer is provided
we store it as the complaint's ``location_text`` (plain text the resident
supplied) — we never geocode or invent coordinates.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.clarify import detect_missing_fields, generate_questions
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.models.complaint import Complaint
from app.models.duplicate import Clarification
from app.models.enums import ClarificationStatus
from app.services.errors import NotFoundError, ValidationError


class ClarificationService:
    def __init__(self, session: AsyncSession, llm: LLMProvider | None = None) -> None:
        self.session = session
        self.llm = llm or get_llm_provider()

    async def generate_for_complaint(
        self, complaint_id: int, *, agent_run_id: int | None = None
    ) -> list[Clarification]:
        complaint = await self.session.get(Complaint, complaint_id)
        if complaint is None:
            raise NotFoundError(f"Complaint {complaint_id} not found")

        fields = detect_missing_fields(complaint)
        if not fields:
            return []

        # Avoid duplicating still-pending questions for the same field.
        existing_pending = {
            c.field
            for c in await self.session.scalars(
                select(Clarification).where(
                    Clarification.complaint_id == complaint_id,
                    Clarification.status == ClarificationStatus.PENDING,
                )
            )
        }
        fields = [f for f in fields if f not in existing_pending]
        if not fields:
            return []

        questions = await generate_questions(self.llm, complaint, fields)
        created: list[Clarification] = []
        for q in questions:
            clar = Clarification(
                complaint_id=complaint_id,
                agent_run_id=agent_run_id,
                field=q["field"],
                question=q["question"],
                status=ClarificationStatus.PENDING,
            )
            self.session.add(clar)
            created.append(clar)
        await self.session.commit()
        for c in created:
            await self.session.refresh(c)
        return created

    async def list_for_complaint(
        self, complaint_id: int, *, pending_only: bool = False
    ) -> list[Clarification]:
        stmt = select(Clarification).where(Clarification.complaint_id == complaint_id)
        if pending_only:
            stmt = stmt.where(Clarification.status == ClarificationStatus.PENDING)
        rows = await self.session.scalars(stmt.order_by(Clarification.id))
        return list(rows)

    async def answer(self, clarification_id: int, answer: str) -> Clarification:
        clar = await self.session.get(Clarification, clarification_id)
        if clar is None:
            raise NotFoundError(f"Clarification {clarification_id} not found")
        if clar.status != ClarificationStatus.PENDING:
            raise ValidationError("Clarification is not pending")
        if not answer or not answer.strip():
            raise ValidationError("Answer must not be empty")

        clar.answer = answer.strip()
        clar.status = ClarificationStatus.ANSWERED
        clar.answered_at = dt.datetime.now(dt.UTC)

        # Safely incorporate a location answer as resident-provided TEXT only.
        # We do not geocode or synthesize coordinates from free text.
        if clar.field == "location":
            complaint = await self.session.get(Complaint, clar.complaint_id)
            if complaint is not None and not complaint.location_text:
                complaint.location_text = answer.strip()[:300]

        await self.session.commit()
        await self.session.refresh(clar)
        return clar
