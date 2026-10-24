"""Run the labeled evaluation and print metrics (M5).

Measures, over the SYNTHETIC labeled set, with the *configured* provider:
  - classification accuracy
  - priority accuracy (exact + within-one-level)
  - department routing accuracy
  - confidence calibration (Brier score + reliability bins)
  - latency (per case)
  - estimated inference cost (real providers only)

Also runs a routing sanity check against genuine Boston 311 historical labels
(kept strictly separate from the synthetic set).

Usage:
    python -m app.eval.run              # offline (fake) or configured provider
    LLM_PROVIDER=openai LLM_API_KEY=... python -m app.eval.run
"""

from __future__ import annotations

import asyncio
import time

from app.agent.graph import build_triage_graph
from app.agent.state import TriageState
from app.db.session import async_session_factory
from app.eval.dataset import SYNTHETIC_CASES
from app.eval.metrics import accuracy, brier_score, reliability_bins
from app.llm.factory import get_llm_provider

_PRICES = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "claude-3-5-haiku-latest": (0.0008, 0.004),
}
_PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def _cost(model, p, c) -> float | None:
    price = _PRICES.get(model or "")
    if not price:
        return None
    return round(p / 1000 * price[0] + c / 1000 * price[1], 6)


async def main() -> None:
    llm = get_llm_provider()
    real = llm.name in ("openai", "anthropic")
    print("=" * 72)
    print(f"Provider: {llm.name}  model: {getattr(llm, 'model', None)}")
    print(f"Mode    : {'REAL model' if real else 'deterministic fake (offline)'}")
    if not real:
        print("NOTE: these are FAKE-provider results, NOT real-model accuracy.")
    print("=" * 72)

    cat_correct = pri_correct = pri_within1 = dept_correct = 0
    latencies: list[int] = []
    cal_pairs: list[tuple[float, bool]] = []
    tok_p = tok_c = 0
    n = len(SYNTHETIC_CASES)

    async with async_session_factory() as session:
        graph = build_triage_graph(llm, session)
        for case in SYNTHETIC_CASES:
            state: TriageState = {
                "complaint_id": 0,
                "city_id": 1,
                "title": case.title,
                "description": case.description,
                "steps": [],
            }
            t0 = time.perf_counter()
            final = await graph.ainvoke(state)
            latencies.append(int((time.perf_counter() - t0) * 1000))

            pred_cat = final.get("category")
            pred_pri = final.get("priority")
            pred_dept = final.get("department_slug")
            cat_ok = pred_cat == case.category
            cat_correct += int(cat_ok)
            if pred_pri == case.priority:
                pri_correct += 1
            if (
                pred_pri in _PRIORITY_ORDER
                and abs(_PRIORITY_ORDER[pred_pri] - _PRIORITY_ORDER[case.priority]) <= 1
            ):
                pri_within1 += 1
            dept_correct += int(pred_dept == case.department_slug)

            conf = final.get("category_confidence")
            if conf is not None:
                cal_pairs.append((float(conf), cat_ok))

            usage = getattr(llm, "last_usage", {}) or {}
            tok_p += usage.get("prompt_tokens", 0)
            tok_c += usage.get("completion_tokens", 0)

    print(f"\nSynthetic labeled cases: {n}")
    print(f"  classification accuracy : {accuracy(cat_correct, n)}")
    print(f"  priority accuracy (exact): {accuracy(pri_correct, n)}")
    print(f"  priority within-1-level  : {accuracy(pri_within1, n)}")
    print(f"  routing accuracy         : {accuracy(dept_correct, n)}")
    print("\nConfidence calibration (classification):")
    print(f"  Brier score (lower=better): {brier_score(cal_pairs)}")
    for b in reliability_bins(cal_pairs):
        print(
            f"    conf {b['range']}: n={b['n']} "
            f"mean_conf={b['mean_confidence']} acc={b['accuracy']}"
        )
    avg_lat = int(sum(latencies) / len(latencies)) if latencies else 0
    print(f"\nLatency: avg={avg_lat}ms min={min(latencies)}ms max={max(latencies)}ms")
    if real:
        cost = _cost(getattr(llm, "model", None), tok_p, tok_c)
        print(f"Tokens: prompt={tok_p} completion={tok_c} approx_cost=${cost}")
        per = round((cost or 0) / n, 6) if n else 0
        print(f"Approx cost per complaint: ${per}")
    else:
        print("Tokens/cost: n/a (fake provider)")

    # Routing sanity check on genuine historical 311 labels (separate source).
    await _routing_check(session_factory=async_session_factory)
    print("=" * 72)


async def _routing_check(session_factory) -> None:
    """Check our category->department mapping against genuine Boston 311
    department labels for a few well-known reasons. Uses ONLY historical data,
    never mixing it with the synthetic set."""
    from sqlalchemy import func, select

    from app.agent.categories import BOSTON_DEPT_CODE_TO_SLUG, CATEGORY_TO_DEPARTMENT
    from app.models.historical_request import Historical311Request as H

    probes = [("Pothole", "pothole"), ("Street Light", "street light"),
              ("Graffiti", "graffiti")]
    print("\nRouting check vs. genuine Boston 311 labels (historical, separate):")
    async with session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(H))
        if not total:
            print("  (no historical data ingested; run app.ingestion.cli)")
            return
        for category, term in probes:
            row = await session.execute(
                select(H.department, func.count().label("n"))
                .where(func.lower(H.reason).like(f"%{term}%"), H.department.is_not(None))
                .group_by(H.department)
                .order_by(func.count().desc())
                .limit(1)
            )
            top = row.first()
            if not top:
                print(f"  {category}: no matching historical records")
                continue
            dept_code, cnt = top
            observed_slug = BOSTON_DEPT_CODE_TO_SLUG.get(dept_code)
            mapped = CATEGORY_TO_DEPARTMENT.get(category)
            match = "OK" if observed_slug == mapped else "DIFF"
            print(
                f"  {category}: mapping={mapped} vs 311 top={dept_code}"
                f"->{observed_slug} (n={cnt}) [{match}]"
            )


if __name__ == "__main__":
    asyncio.run(main())
