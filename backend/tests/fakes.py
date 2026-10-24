"""Test doubles for the LLM provider."""

from __future__ import annotations

from typing import Any

from app.llm.base import LLMError


class ScriptedProvider:
    """Returns canned outputs keyed by the schema hint of each node.

    Lets tests drive the agent down specific paths deterministically.
    """

    name = "scripted"

    def __init__(self, *, extract=None, classify=None, prioritize=None):
        self.model = "scripted-1"
        self._extract = extract or {
            "issue_summary": "summary",
            "location_hint": None,
            "entities": [],
        }
        self._classify = classify or {"category": "Pothole", "confidence": 0.95}
        self._prioritize = prioritize or {
            "priority": "high",
            "confidence": 0.9,
            "rationale": "unsafe",
        }

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        keys = set(schema_hint.keys())
        if "issue_summary" in keys:
            return dict(self._extract)
        if "category" in keys and "priority" not in keys:
            return dict(self._classify)
        if "priority" in keys:
            return dict(self._prioritize)
        return {}


class MalformedProvider:
    """Returns structurally wrong output (bad types / unknown values)."""

    name = "malformed"
    model = "malformed-1"

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        keys = set(schema_hint.keys())
        if "issue_summary" in keys:
            return {"issue_summary": "ok", "entities": "not-a-list"}
        if "category" in keys and "priority" not in keys:
            # Unknown category + non-numeric confidence.
            return {"category": "Teleportation Malfunction", "confidence": "high"}
        if "priority" in keys:
            return {"priority": "SUPER-URGENT", "confidence": None, "rationale": 42}
        return {}


class FailingProvider:
    """Always raises LLMError (simulates provider/network/auth failure)."""

    name = "failing"
    model = None

    def __init__(self, fail_on: str = "extract"):
        self.fail_on = fail_on

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        keys = set(schema_hint.keys())
        where = (
            "extract"
            if "issue_summary" in keys
            else "classify"
            if "category" in keys and "priority" not in keys
            else "prioritize"
        )
        if where == self.fail_on:
            raise LLMError(f"simulated failure in {where}")
        # Otherwise return minimal valid output.
        if where == "extract":
            return {"issue_summary": "x", "entities": []}
        if where == "classify":
            return {"category": "Pothole", "confidence": 0.9}
        return {"priority": "medium", "confidence": 0.8, "rationale": "ok"}
