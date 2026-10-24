"""Evaluation harness: run the triage workflow over representative Boston
complaints with the *configured* LLM provider and report telemetry.

Reports per complaint: category, priority, department, confidences, review
decision, latency, and (for real providers) token usage + an approximate cost.

Usage:
    # Offline (deterministic fake provider) — proves the harness + workflow:
    python -m app.agent.evaluate

    # Real provider (requires credentials in the environment; never printed):
    LLM_PROVIDER=openai LLM_MODEL=gpt-4o-mini LLM_API_KEY=... \
        python -m app.agent.evaluate

API keys are read from the environment via settings and are NEVER logged.
"""

from __future__ import annotations

import asyncio
import time

from app.agent.graph import build_triage_graph
from app.agent.state import TriageState
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.llm.base import LLMError
from app.llm.factory import get_llm_provider

# Representative, synthetic Boston-style complaints (no real resident PII).
SAMPLE_COMPLAINTS = [
    {
        "title": "Huge pothole on Dorchester Ave",
        "description": "Deep pothole near the bus stop on Dorchester Ave; cars "
        "are swerving into oncoming traffic to avoid it. Dangerous.",
    },
    {
        "title": "Street light out for a week",
        "description": "The street light at the corner of Blue Hill Ave has "
        "been dark for over a week. It's very dark and feels unsafe at night.",
    },
    {
        "title": "Overflowing trash barrels",
        "description": "Trash barrels on the sidewalk have been overflowing for "
        "days with garbage spilling onto the street in the South End.",
    },
    {
        "title": "Smell of gas near the school",
        "description": "There is a strong smell of gas near the elementary "
        "school entrance this morning. Seems like it could be a safety hazard.",
    },
    {
        "title": "Graffiti on the park wall",
        "description": "Someone spray-painted graffiti across the wall at the "
        "playground. It's cosmetic but should be cleaned up.",
    },
    {
        "title": "Not sure who to call",
        "description": "Something is wrong outside my building and I don't know "
        "what department handles it. Please help.",
    },
]

# Rough public per-1K-token prices (USD) for a cost ESTIMATE only. Update as
# needed; these are approximate and may be out of date.
_PRICES = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "claude-3-5-haiku-latest": (0.0008, 0.004),
}


def _estimate_cost(model: str | None, prompt_tok: int, completion_tok: int) -> float | None:
    if not model:
        return None
    price = _PRICES.get(model)
    if price is None:
        return None
    pin, pout = price
    return round(prompt_tok / 1000 * pin + completion_tok / 1000 * pout, 6)


async def main() -> None:
    settings = get_settings()
    try:
        llm = get_llm_provider()
    except LLMError as exc:
        print(f"Could not initialize provider '{settings.llm_provider}': {exc}")
        return

    print("=" * 72)
    print(f"Provider : {llm.name}")
    print(f"Model    : {getattr(llm, 'model', None)}")
    real = llm.name in ("openai", "anthropic")
    print(f"Mode     : {'REAL model' if real else 'deterministic fake (offline)'}")
    print("=" * 72)

    totals = {"prompt": 0, "completion": 0, "cost": 0.0, "errors": 0}
    # A DB session is needed only for the routing node's historical lookup.
    async with async_session_factory() as session:
        graph = build_triage_graph(llm, session)
        # city_id 1 == Boston after seeding; routing tolerates no history.
        for i, c in enumerate(SAMPLE_COMPLAINTS, 1):
            state: TriageState = {
                "complaint_id": 0,
                "city_id": 1,
                "title": c["title"],
                "description": c["description"],
                "steps": [],
            }
            started = time.perf_counter()
            try:
                final = await graph.ainvoke(state)
            except Exception as exc:  # noqa: BLE001 - report, don't crash harness
                totals["errors"] += 1
                print(f"\n[{i}] {c['title']!r}\n   ERROR: {exc}")
                continue
            latency_ms = int((time.perf_counter() - started) * 1000)

            usage = getattr(llm, "last_usage", {}) or {}
            ptok = usage.get("prompt_tokens", 0)
            ctok = usage.get("completion_tokens", 0)
            totals["prompt"] += ptok
            totals["completion"] += ctok
            cost = _estimate_cost(getattr(llm, "model", None), ptok, ctok)
            if cost:
                totals["cost"] += cost

            err = final.get("error")
            print(f"\n[{i}] {c['title']!r}")
            if err:
                totals["errors"] += 1
                print(f"   agent error: {err}")
            print(
                f"   category={final.get('category')} "
                f"(conf={final.get('category_confidence')})"
            )
            print(
                f"   priority={final.get('priority')} "
                f"(conf={final.get('priority_confidence')})"
            )
            print(
                f"   department={final.get('department_slug')} "
                f"(conf={final.get('department_confidence')})"
            )
            print(
                f"   overall_confidence={final.get('overall_confidence')} "
                f"needs_review={final.get('requires_review')}"
            )
            if final.get("review_reason"):
                print(f"   review_reason: {final['review_reason']}")
            print(f"   latency_ms={latency_ms}")
            if real:
                print(
                    f"   tokens: prompt={ptok} completion={ctok} "
                    f"cost~=${cost if cost is not None else 'n/a'}"
                )

    print("\n" + "=" * 72)
    print("TOTALS")
    print(f"  complaints: {len(SAMPLE_COMPLAINTS)}  errors: {totals['errors']}")
    if real:
        print(
            f"  tokens: prompt={totals['prompt']} completion={totals['completion']} "
            f"approx_cost=${round(totals['cost'], 4)}"
        )
    else:
        print("  (fake provider: no tokens/cost; run with a real LLM_PROVIDER for costs)")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
