"""Agent/review API schemas."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AgentRunStatus,
    ComplaintPriority,
    RecommendationStatus,
    ReviewSeverity,
)


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_name: str
    input: dict[str, Any]
    output: dict[str, Any]
    confidence: float | None
    latency_ms: int | None


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_run_id: int
    complaint_id: int
    extracted: dict[str, Any]
    category: str | None
    category_confidence: float | None
    priority: ComplaintPriority | None
    priority_confidence: float | None
    priority_rationale: str | None
    department_slug: str | None
    department_confidence: float | None
    routing_evidence: dict[str, Any]
    overall_confidence: float | None
    status: RecommendationStatus
    requires_review: bool
    review_severity: ReviewSeverity
    review_reason: str | None
    reviewer: str | None
    reviewed_at: dt.datetime | None
    final_category: str | None
    final_priority: ComplaintPriority | None
    final_department_slug: str | None
    review_note: str | None
    created_at: dt.datetime


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    graph_version: str
    status: AgentRunStatus
    llm_provider: str
    llm_model: str | None
    error: str | None
    created_at: dt.datetime
    finished_at: dt.datetime | None


class AgentRunDetail(AgentRunRead):
    steps: list[AgentStepRead] = []
    recommendation: RecommendationRead | None = None


class ReviewDecision(BaseModel):
    """Staff decision on a recommendation."""

    decision: Literal["approve", "override", "reject"]
    reviewer: str = Field(default="staff", max_length=80)
    note: str | None = None
    # Override-only fields (ignored for approve/reject).
    category: str | None = Field(default=None, max_length=120)
    priority: ComplaintPriority | None = None
    department_slug: str | None = Field(default=None, max_length=80)
