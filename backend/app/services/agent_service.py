"""Run the triage graph for a complaint and persist auditable results.

AI output is written ONLY to agent_* tables; the complaint row is never touched
here. Applying a recommendation to the complaint happens in the review service
after human approval.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import GRAPH_VERSION, build_triage_graph
from app.agent.state import TriageState
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.models.agent import AgentRecommendation, AgentRun, AgentStep
from app.models.complaint import Complaint
from app.models.enums import (
    AgentRunStatus,
    ComplaintPriority,
    RecommendationStatus,
    ReviewSeverity,
)
from app.services.errors import NotFoundError


class AgentService:
    def __init__(self, session: AsyncSession, llm: LLMProvider | None = None) -> None:
        self.session = session
        self.llm = llm or get_llm_provider()

    async def run_triage(self, complaint_id: int) -> AgentRun:
        complaint = await self.session.get(Complaint, complaint_id)
        if complaint is None:
            raise NotFoundError(f"Complaint {complaint_id} not found")

        run = AgentRun(
            complaint_id=complaint.id,
            graph_version=GRAPH_VERSION,
            status=AgentRunStatus.RUNNING,
            llm_provider=self.llm.name,
            llm_model=getattr(self.llm, "model", None),
        )
        self.session.add(run)
        await self.session.flush()  # assign run.id

        initial: TriageState = {
            "complaint_id": complaint.id,
            "city_id": complaint.city_id,
            "title": complaint.title,
            "description": complaint.description,
            "steps": [],
        }

        graph = build_triage_graph(self.llm, self.session)
        final: TriageState = await graph.ainvoke(initial)

        # Persist step audit records.
        for s in final.get("steps", []):
            self.session.add(
                AgentStep(
                    agent_run_id=run.id,
                    node_name=s["node_name"],
                    input=s.get("input") or {},
                    output=s.get("output") or {},
                    confidence=s.get("confidence"),
                    latency_ms=s.get("latency_ms"),
                )
            )

        if final.get("error"):
            run.status = AgentRunStatus.FAILED
            run.error = final["error"]
            run.finished_at = dt.datetime.now(dt.UTC)
            await self.session.commit()
            await self.session.refresh(run)
            return run

        priority = _as_priority(final.get("priority"))
        requires_review = bool(final.get("requires_review", True))

        rec = AgentRecommendation(
            agent_run_id=run.id,
            complaint_id=complaint.id,
            extracted=final.get("extracted") or {},
            category=final.get("category"),
            category_confidence=final.get("category_confidence"),
            priority=priority,
            priority_confidence=final.get("priority_confidence"),
            priority_rationale=final.get("priority_rationale"),
            department_slug=final.get("department_slug"),
            department_confidence=final.get("department_confidence"),
            routing_evidence=final.get("routing_evidence") or {},
            overall_confidence=final.get("overall_confidence"),
            status=RecommendationStatus.PENDING,
            requires_review=requires_review,
            review_severity=ReviewSeverity(final.get("review_severity") or "routine"),
            review_reason=final.get("review_reason"),
        )
        self.session.add(rec)

        run.status = (
            AgentRunStatus.NEEDS_REVIEW if requires_review else AgentRunStatus.COMPLETED
        )
        run.finished_at = dt.datetime.now(dt.UTC)

        await self.session.commit()
        await self.session.refresh(run)
        return run


def _as_priority(value: str | None) -> ComplaintPriority | None:
    if value is None:
        return None
    try:
        return ComplaintPriority(value)
    except ValueError:
        return None
