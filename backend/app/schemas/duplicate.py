"""Duplicate-detection and clarification API schemas."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ClarificationStatus, DuplicateDecision


class DuplicateCandidate(BaseModel):
    """A possible duplicate. Deliberately excludes reporter PII."""

    model_config = ConfigDict(from_attributes=True)

    link_id: int
    candidate_complaint_id: int
    candidate_tracking_code: str
    candidate_title: str
    candidate_status: str
    similarity: float
    combined_score: float
    evidence: dict[str, Any]
    decision: DuplicateDecision


class DuplicateDecisionIn(BaseModel):
    decision: Literal["confirm", "reject"]
    reviewer: str = Field(default="staff", max_length=80)
    note: str | None = None


class ClarificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    field: str
    question: str
    answer: str | None
    status: ClarificationStatus
    created_at: dt.datetime
    answered_at: dt.datetime | None


class ClarificationAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class PublicClarification(BaseModel):
    """Clarification view for residents — no internal metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    field: str
    question: str
    status: ClarificationStatus
