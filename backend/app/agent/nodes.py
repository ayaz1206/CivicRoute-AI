"""Graph node implementations.

Each node is a coroutine ``(state) -> partial_state``. Nodes that call the LLM
record an audit step and convert any LLMError into a terminal error on the
state so the graph can short-circuit to a safe failure instead of crashing.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.categories import SUPPORTED_CATEGORIES, is_supported_category
from app.agent.routing import resolve_department
from app.agent.state import TriageState
from app.llm.base import LLMError, LLMProvider
from app.models.enums import ComplaintPriority

_VALID_PRIORITIES = {p.value for p in ComplaintPriority}


def _step(
    name: str,
    inp: dict[str, Any],
    out: dict[str, Any],
    confidence: float | None,
    started: float,
) -> dict[str, Any]:
    return {
        "node_name": name,
        "input": inp,
        "output": out,
        "confidence": confidence,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def _append_step(state: TriageState, step: dict[str, Any]) -> list:
    steps = list(state.get("steps", []))
    steps.append(step)
    return steps


class TriageNodes:
    """Bundles the provider + db session the nodes need."""

    def __init__(self, llm: LLMProvider, session: AsyncSession) -> None:
        self.llm = llm
        self.session = session

    async def extract(self, state: TriageState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        started = time.perf_counter()
        user = f"Title: {state['title']}\nDescription: {state['description']}"
        hint = {"issue_summary": "", "location_hint": "", "entities": []}
        try:
            out = await self.llm.complete_json(
                system="You extract structured details from a city complaint.",
                user=user,
                schema_hint=hint,
            )
        except LLMError as exc:
            return {"error": f"extract: {exc}"}
        extracted = {
            "issue_summary": out.get("issue_summary"),
            "location_hint": out.get("location_hint"),
            "entities": out.get("entities") or [],
        }
        return {
            "extracted": extracted,
            "steps": _append_step(
                state, _step("extract", {"text": user}, extracted, None, started)
            ),
        }

    async def classify(self, state: TriageState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        started = time.perf_counter()
        summary = (state.get("extracted") or {}).get("issue_summary") or state[
            "description"
        ]
        hint = {"category": "", "confidence": 0.0}
        try:
            out = await self.llm.complete_json(
                system=(
                    "Classify the complaint into exactly one of: "
                    + ", ".join(SUPPORTED_CATEGORIES)
                    + ". Return the category and a confidence in [0,1]."
                ),
                user=summary,
                schema_hint=hint,
            )
        except LLMError as exc:
            return {"error": f"classify: {exc}"}

        category = out.get("category")
        confidence = _coerce_conf(out.get("confidence"))
        # Validate against the allowlist; unknown -> "Other" with low confidence.
        if not is_supported_category(category):
            category, confidence = "Other", min(confidence, 0.3)
        return {
            "category": category,
            "category_confidence": confidence,
            "steps": _append_step(
                state,
                _step("classify", {"summary": summary},
                      {"category": category, "confidence": confidence},
                      confidence, started),
            ),
        }

    async def prioritize(self, state: TriageState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        started = time.perf_counter()
        user = (
            f"Category: {state.get('category')}\n"
            f"Complaint: {state['description']}"
        )
        hint = {"priority": "", "confidence": 0.0, "rationale": ""}
        try:
            out = await self.llm.complete_json(
                system=(
                    "You assign a triage priority to a city complaint using this "
                    "rubric. Choose exactly one level:\n"
                    "- urgent: an immediate threat to life or safety requiring a "
                    "same-day emergency response. Examples: gas leak or gas odor, "
                    "active flooding or water main break, downed or exposed "
                    "electrical wire, sinkhole, fire hazard, injury hazard that is "
                    "actively endangering people right now.\n"
                    "- high: unsafe or significantly disruptive but NOT an "
                    "immediate life-threatening emergency; should be handled "
                    "promptly. Examples: a deep pothole cars must swerve around, a "
                    "street light out at a dark crosswalk, a fallen branch "
                    "blocking a sidewalk, a traffic signal malfunction.\n"
                    "- medium: a real problem that degrades service or is a "
                    "moderate hazard but is not dangerous day-to-day. Examples: a "
                    "pothole damaging tires, overflowing trash, an abandoned "
                    "vehicle, a cracked/uneven sidewalk, persistent nighttime "
                    "noise.\n"
                    "- low: minor, cosmetic, or routine with little safety "
                    "impact. Examples: graffiti, a flickering or single light "
                    "out on a non-critical street, a missed recycling pickup, "
                    "faded paint.\n"
                    "Do NOT inflate priority out of caution: reserve 'urgent' for "
                    "immediate safety threats as defined above. When a complaint "
                    "is merely unpleasant or inconvenient, prefer medium or low. "
                    "Return the priority, a short rationale, and a confidence in "
                    "[0,1]."
                ),
                user=user,
                schema_hint=hint,
            )
        except LLMError as exc:
            return {"error": f"prioritize: {exc}"}

        priority = str(out.get("priority") or "").lower()
        confidence = _coerce_conf(out.get("confidence"))
        rationale = out.get("rationale")
        rationale = str(rationale) if rationale is not None else None
        if priority not in _VALID_PRIORITIES:
            # Malformed priority -> safe default + force review.
            priority, confidence = "medium", min(confidence, 0.3)
            rationale = (rationale or "") + " [defaulted: invalid priority]"
        return {
            "priority": priority,
            "priority_confidence": confidence,
            "priority_rationale": rationale,
            "steps": _append_step(
                state,
                _step("prioritize", {"text": user},
                      {"priority": priority, "confidence": confidence,
                       "rationale": rationale},
                      confidence, started),
            ),
        }

    async def route(self, state: TriageState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        started = time.perf_counter()
        category = state.get("category") or "Other"
        slug, confidence, evidence = await resolve_department(
            self.session, state["city_id"], category
        )
        return {
            "department_slug": slug,
            "department_confidence": confidence,
            "routing_evidence": evidence,
            "steps": _append_step(
                state,
                _step("route", {"category": category},
                      {"department_slug": slug, "confidence": confidence,
                       "evidence": evidence},
                      confidence, started),
            ),
        }

    async def gate(self, state: TriageState) -> dict[str, Any]:
        """Decide whether the recommendation needs human review.

        Uses the provided threshold and hard rules (urgent priority, 'Other'
        category, or no department always go to review).
        """
        from app.core.config import get_settings

        threshold = get_settings().agent_review_threshold

        confs = [
            state.get("category_confidence") or 0.0,
            state.get("priority_confidence") or 0.0,
            state.get("department_confidence") or 0.0,
        ]
        overall = round(sum(confs) / len(confs), 3)

        reasons = []
        low_confidence = False
        high_risk = False
        if state.get("error"):
            reasons.append("agent error")
            high_risk = True
        if (state.get("category_confidence") or 0) < threshold:
            reasons.append("low classification confidence")
            low_confidence = True
        if (state.get("department_confidence") or 0) < threshold:
            reasons.append("low routing confidence")
            low_confidence = True
        if state.get("category") == "Other":
            reasons.append("uncategorized")
            high_risk = True
        if state.get("priority") == "urgent":
            reasons.append("high-risk (urgent)")
            high_risk = True
        if not state.get("department_slug"):
            reasons.append("no department resolved")
            high_risk = True

        # `requires_review` marks a recommendation as FLAGGED (needs attention
        # beyond routine approval). Note: staff approval is mandatory for ALL
        # recommendations regardless — nothing is auto-applied to a complaint.
        # `severity` lets the UI separate flagged items from routine ones.
        flagged = bool(reasons)
        if high_risk:
            severity = "high_risk"
        elif low_confidence:
            severity = "low_confidence"
        else:
            severity = "routine"

        return {
            "overall_confidence": overall,
            "requires_review": flagged,
            "review_severity": severity,
            "review_reason": "; ".join(reasons) if reasons else None,
        }


def _coerce_conf(value: Any) -> float:
    """Coerce a model-provided confidence into [0,1]; default 0.0 on garbage."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))
