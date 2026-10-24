"""Deterministic, offline LLM provider.

Produces plausible structured output from simple keyword heuristics so the
agent workflow runs end-to-end without network access or API keys. This is the
default provider and is what the test suite uses.
"""

from __future__ import annotations

from typing import Any

# Keyword -> category heuristics (categories mirror SUPPORTED_CATEGORIES).
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Pothole", ("pothole", "road surface", "crater")),
    ("Street Light", ("streetlight", "street light", "lamp", "dark street")),
    ("Trash & Recycling", ("trash", "garbage", "recycling", "dumping", "litter")),
    ("Graffiti", ("graffiti", "tagging", "vandal")),
    ("Tree Maintenance", ("tree", "branch", "limb")),
    ("Parking", ("parking", "parked", "abandoned vehicle")),
    ("Water & Sewer", ("water", "sewer", "flood", "hydrant", "leak")),
    ("Noise", ("noise", "loud", "music")),
    ("Sidewalk", ("sidewalk", "curb", "pavement")),
    ("Traffic Signal", ("signal", "traffic light", "sign")),
]

_URGENT = ("gas", "fire", "injury", "injured", "exposed wire", "sinkhole", "hazard")
_HIGH = ("dangerous", "unsafe", "blocking", "accident", "flood", "safety")
_LOW = ("cosmetic", "minor", "small", "faded")


class FakeLLMProvider:
    name = "fake"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "fake-deterministic-1"

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        text = user.lower()
        keys = set(schema_hint.keys())

        # Extraction node.
        if "issue_summary" in keys:
            return {
                "issue_summary": user.strip()[:160],
                "location_hint": self._find_location(user),
                "entities": self._entities(text),
            }

        # Classification node.
        if "category" in keys and "priority" not in keys:
            category, conf = self._classify(text)
            return {"category": category, "confidence": conf}

        # Prioritization node.
        if "priority" in keys:
            priority, conf, rationale = self._prioritize(text)
            return {
                "priority": priority,
                "confidence": conf,
                "rationale": rationale,
            }

        # Fallback: echo an empty object matching the hint.
        return {k: None for k in keys}

    def _classify(self, text: str) -> tuple[str, float]:
        for category, kws in _CATEGORY_KEYWORDS:
            if any(k in text for k in kws):
                return category, 0.9
        return "Other", 0.4  # low confidence -> likely needs review

    def _prioritize(self, text: str) -> tuple[str, float, str]:
        if any(k in text for k in _URGENT):
            return "urgent", 0.92, "Mentions a life-safety hazard."
        if any(k in text for k in _HIGH):
            return "high", 0.82, "Describes an unsafe or blocking condition."
        if any(k in text for k in _LOW):
            return "low", 0.8, "Appears cosmetic or minor."
        return "medium", 0.6, "No strong urgency signals detected."

    def _find_location(self, user: str) -> str | None:
        # Naive: return the first chunk that looks like "<something> St/Ave/Rd".
        import re

        m = re.search(r"\b([\w\s]+\b(?:St|Street|Ave|Avenue|Rd|Road|Blvd))\b", user)
        return m.group(1).strip() if m else None

    def _entities(self, text: str) -> list[str]:
        found = []
        for _, kws in _CATEGORY_KEYWORDS:
            for k in kws:
                if k in text:
                    found.append(k)
        return sorted(set(found))
