"""Department routing using historical 311 patterns + validated mappings.

Strategy:
1. Start from the curated CATEGORY_TO_DEPARTMENT mapping (validated allowlist).
2. Look at historical 311 records whose `reason`/`case_type` resemble the
   category to see which Boston department handled them most often, as
   corroborating evidence (and a tie-breaker for ambiguous categories).
3. Always validate the final slug against the city's real departments.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.categories import (
    BOSTON_DEPT_CODE_TO_SLUG,
    CATEGORY_TO_DEPARTMENT,
)
from app.models.department import Department
from app.models.historical_request import Historical311Request as H


async def _valid_department_slugs(session: AsyncSession, city_id: int) -> set[str]:
    rows = await session.scalars(
        select(Department.slug).where(Department.city_id == city_id)
    )
    return set(rows)


async def historical_department_hint(
    session: AsyncSession, city_id: int, category: str
) -> tuple[str | None, list[dict]]:
    """Return (department_slug_hint, evidence) from historical 311 data.

    Matches historical rows whose reason/case_type contain the category words
    and tallies the most common Boston department code, mapped to our slug.
    """
    # Use the most distinctive word of the category for a LIKE match.
    term = category.split()[0].lower()
    pattern = f"%{term}%"
    rows = await session.execute(
        select(H.department, func.count().label("n"))
        .where(
            H.city_id == city_id,
            H.department.is_not(None),
            (func.lower(H.reason).like(pattern))
            | (func.lower(H.case_type).like(pattern)),
        )
        .group_by(H.department)
        .order_by(func.count().desc())
        .limit(3)
    )
    evidence = [{"boston_department": d, "count": int(n)} for d, n in rows.all()]
    hint: str | None = None
    for item in evidence:
        slug = BOSTON_DEPT_CODE_TO_SLUG.get(item["boston_department"])
        if slug:
            hint = slug
            break
    return hint, evidence


async def resolve_department(
    session: AsyncSession, city_id: int, category: str
) -> tuple[str | None, float, dict]:
    """Resolve a validated department slug for a category.

    Returns (slug_or_None, confidence, evidence_dict). The slug is guaranteed to
    be one of the city's real departments or None.
    """
    valid = await _valid_department_slugs(session, city_id)
    mapped = CATEGORY_TO_DEPARTMENT.get(category)
    hist_hint, hist_evidence = await historical_department_hint(
        session, city_id, category
    )

    evidence = {
        "mapping_slug": mapped,
        "historical_hint": hist_hint,
        "historical_top": hist_evidence,
    }

    # Prefer the curated mapping; corroborate/raise confidence with history.
    chosen = mapped or hist_hint
    if chosen not in valid:
        chosen = hist_hint if hist_hint in valid else None

    if chosen is None:
        return None, 0.0, evidence

    confidence = 0.75
    if mapped and hist_hint and mapped == hist_hint:
        confidence = 0.95  # mapping and history agree
    elif mapped and not hist_hint:
        confidence = 0.8
    elif not mapped and hist_hint:
        confidence = 0.6  # only historical signal
    return chosen, confidence, evidence
