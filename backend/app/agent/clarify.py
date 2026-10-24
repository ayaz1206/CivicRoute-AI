"""Clarification question generation.

Identifies missing information on a complaint using deterministic rules, then
asks the LLM to phrase targeted, resident-friendly questions. Rules decide
WHICH fields are missing (so we never hallucinate a need); the LLM only phrases
the question. The LLM is never used to invent the missing values themselves.
"""

from __future__ import annotations

from app.llm.base import LLMError, LLMProvider
from app.models.complaint import Complaint

# Minimum description length below which we ask for more detail.
_MIN_DESCRIPTION_LEN = 40


def detect_missing_fields(complaint: Complaint) -> list[str]:
    """Return the list of fields that need clarification (may be empty)."""
    missing: list[str] = []
    has_coords = complaint.latitude is not None and complaint.longitude is not None
    if not complaint.location_text and not has_coords:
        missing.append("location")
    if not complaint.description or len(complaint.description.strip()) < _MIN_DESCRIPTION_LEN:
        missing.append("detail")
    return missing


# Deterministic fallback questions if the LLM is unavailable.
_FALLBACK = {
    "location": "Where exactly is this issue located? Please share the nearest "
    "street address or cross streets.",
    "detail": "Could you describe the issue in a bit more detail, including how "
    "severe it is and when you noticed it?",
}


async def generate_questions(
    llm: LLMProvider, complaint: Complaint, fields: list[str]
) -> list[dict]:
    """Return [{field, question}] for each missing field.

    Falls back to static questions if the LLM errors — clarification should
    degrade gracefully, never block submission.
    """
    questions: list[dict] = []
    for field in fields:
        text = _FALLBACK[field]
        try:
            out = await llm.complete_json(
                system=(
                    "You help a city collect missing complaint details. Ask ONE "
                    "short, polite question to obtain the missing field. Do NOT "
                    "guess or invent the answer."
                ),
                user=(
                    f"Complaint title: {complaint.title}\n"
                    f"Description: {complaint.description}\n"
                    f"Missing field: {field}"
                ),
                schema_hint={"question": ""},
            )
            q = out.get("question")
            if isinstance(q, str) and q.strip():
                text = q.strip()
        except LLMError:
            pass  # use fallback
        questions.append({"field": field, "question": text})
    return questions
