"""Shared state for the triage graph."""

from __future__ import annotations

from typing import Any, TypedDict


class StepRecord(TypedDict):
    node_name: str
    input: dict[str, Any]
    output: dict[str, Any]
    confidence: float | None
    latency_ms: int | None


class TriageState(TypedDict, total=False):
    # Inputs
    complaint_id: int
    city_id: int
    title: str
    description: str

    # Accumulated node outputs
    extracted: dict[str, Any]
    category: str | None
    category_confidence: float | None
    priority: str | None
    priority_confidence: float | None
    priority_rationale: str | None
    department_slug: str | None
    department_confidence: float | None
    routing_evidence: dict[str, Any]
    overall_confidence: float | None
    requires_review: bool
    review_severity: str | None
    review_reason: str | None

    # Audit + error channels
    steps: list[StepRecord]
    error: str | None
