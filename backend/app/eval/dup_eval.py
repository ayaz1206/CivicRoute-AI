"""Real-embedding, location-aware duplicate-detection evaluation (M5).

Evaluates the FULL duplicate decision — semantic similarity + category +
location evidence + status, gated on the combined score — via the production
`DuplicateService.find_candidates`, with the configured provider (OpenAI here).

Pair types:
  - identical / paraphrase true duplicates (same place)
  - differently-worded addresses for the SAME place (should match)
  - nearby intersections (ambiguous-ish; reported)
  - coordinate-based: same spot, and clearly-far coordinates
  - missing location on one/both (unknown -> must not penalize)
  - same issue on DIFFERENT streets (should NOT be flagged)
  - same category, different incident (should NOT be flagged)
  - unrelated categories (should NOT be flagged)

Each pair: B is the existing complaint, A the new one. We embed both, run the
real decision, and tally TP/FP/TN/FN plus precision/recall. Uses a throwaway
"dup-eval" city and rolls everything back; historical data is untouched.

Usage:
    python -m app.eval.dup_eval
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.embeddings.factory import get_embedding_provider
from app.models.city import City
from app.models.complaint import Complaint
from app.models.duplicate import ComplaintEmbedding
from app.models.enums import ComplaintSource, ComplaintStatus
from app.services.duplicate_service import DuplicateService


@dataclass
class Pair:
    label: str
    kind: str
    a_desc: str
    a_loc: str | None
    a_lat: float | None
    a_lng: float | None
    b_desc: str
    b_loc: str | None
    b_lat: float | None
    b_lng: float | None
    is_duplicate: bool


def P(label, kind, a_desc, b_desc, is_dup, *, a_loc=None, b_loc=None,
      a_lat=None, a_lng=None, b_lat=None, b_lng=None) -> Pair:
    return Pair(label, kind, a_desc, a_loc, a_lat, a_lng,
                b_desc, b_loc, b_lat, b_lng, is_dup)


PAIRS: list[Pair] = [
    # identical / paraphrase, same place (text)
    P("pothole-identical", "identical",
      "Large deep pothole on Dorchester Ave near the bus stop, cars swerving.",
      "Deep dangerous pothole on Dorchester Avenue by the bus stop damaging tires.",
      True, a_loc="Dorchester Ave bus stop", b_loc="Dorchester Avenue, by the bus stop"),
    # The previously observed FALSE NEGATIVE: paraphrase, same place.
    P("graffiti-paraphrase-FN", "paraphrase",
      "Someone spray-painted graffiti across the brick wall at the playground.",
      "The park wall by the swings got covered in spray-paint tags overnight.",
      True, a_loc="Ringer Park playground", b_loc="Ringer Park, by the swings"),
    # Differently-worded address, same place (abbrev vs full + extra words).
    P("addr-worded-diff", "addr_variant",
      "Pothole on Mass Ave near the corner of Boylston.",
      "Large pothole at Massachusetts Avenue and Boylston Street intersection.",
      True, a_loc="Mass Ave & Boylston", b_loc="Massachusetts Avenue / Boylston St"),
    # Nearby intersection, same street — arguably same issue (reported).
    P("nearby-intersection", "nearby",
      "Broken street light on Beacon St at Arlington.",
      "Street light out on Beacon Street near Berkeley.",
      True, a_loc="Beacon St at Arlington", b_loc="Beacon St near Berkeley"),
    # Coordinates: same spot (~40m apart).
    P("coord-same-spot", "coord_match",
      "Pothole causing damage in the roadway.",
      "Deep pothole in the road, cars hitting it.",
      True, a_lat=42.3426, a_lng=-71.0971, b_lat=42.3429, b_lng=-71.0972),
    # Coordinates: clearly far apart (~3km) — same issue, different place.
    P("coord-far", "coord_mismatch",
      "Pothole causing damage in the roadway.",
      "Deep pothole in the road, cars hitting it.",
      False, a_lat=42.3426, a_lng=-71.0971, b_lat=42.3188, b_lng=-71.0846),
    # The previously observed FALSE POSITIVE: same issue, different streets.
    P("pothole-diff-street-FP", "diff_street",
      "Deep pothole on Dorchester Ave damaging cars near the bus stop.",
      "Deep pothole on Beacon St damaging cars near the corner.",
      False, a_loc="Dorchester Ave", b_loc="Beacon St"),
    P("streetlight-diff-street", "diff_street",
      "A street light is out and the area is very dark at night.",
      "A street light is out and the area is very dark at night.",
      False, a_loc="Washington St downtown", b_loc="Dudley Sq, Roxbury"),
    # Missing location on one side -> unknown, must NOT be penalized into a FN
    # when the text is otherwise a clear duplicate.
    P("missing-loc-one-side", "missing_loc",
      "Overflowing trash barrels with garbage spilling onto the sidewalk.",
      "Trash bins overflowing, refuse scattered across the pavement.",
      True, a_loc=None, b_loc="South End"),
    # Missing location on both -> unknown; clear textual dup should still flag.
    P("missing-loc-both", "missing_loc",
      "Water main break, water gushing and flooding the street.",
      "A water main has burst and water is flooding across the roadway.",
      True, a_loc=None, b_loc=None),
    # Same category, genuinely different incident (no location overlap).
    P("pothole-same-cat-diff", "same_cat_diff",
      "A pothole on my street keeps popping tires, getting bigger each week.",
      "After the storm a new pothole opened near the school crossing.",
      False, a_loc="Elm St", b_loc="Washington St near the school"),
    # Unrelated categories.
    P("pothole-vs-noise", "unrelated",
      "Deep pothole on Dorchester Ave near the bus stop.",
      "Neighbors throwing loud parties with music until 3am.",
      False, a_loc="Dorchester Ave", b_loc="Dorchester Ave"),
    P("trash-vs-tax", "unrelated",
      "Trash barrels overflowing onto the sidewalk in the South End.",
      "I have a question about the amount on my quarterly property tax bill.",
      False, a_loc="South End", b_loc=None),
]


async def _raw_sim(session, ca_id, cb_id) -> float | None:
    ea = await session.scalar(
        select(ComplaintEmbedding).where(ComplaintEmbedding.complaint_id == ca_id)
    )
    eb = await session.scalar(
        select(ComplaintEmbedding).where(ComplaintEmbedding.complaint_id == cb_id)
    )
    if ea is None or eb is None:
        return None
    raw = await session.scalar(
        select(1 - ComplaintEmbedding.embedding.cosine_distance(eb.embedding)).where(
            ComplaintEmbedding.id == ea.id
        )
    )
    return float(raw) if raw is not None else None


async def _run_pairs() -> list[tuple]:
    embedder = get_embedding_provider()
    rows = []
    async with async_session_factory() as session:
        city = await session.scalar(select(City).where(City.slug == "dup-eval"))
        if city is None:
            city = City(name="Dup Eval", slug="dup-eval", timezone="UTC")
            session.add(city)
            await session.flush()
        old = [
            c.id for c in await session.scalars(
                select(Complaint).where(Complaint.city_id == city.id)
            )
        ]
        if old:
            await session.execute(delete(Complaint).where(Complaint.id.in_(old)))
            await session.commit()

        svc = DuplicateService(session, embedder=embedder)
        for i, p in enumerate(PAIRS):
            cb = Complaint(
                tracking_code=f"DE-{i:02d}-B", city_id=city.id,
                source=ComplaintSource.WEB, status=ComplaintStatus.SUBMITTED,
                title=p.label + " B", description=p.b_desc,
                location_text=p.b_loc, latitude=p.b_lat, longitude=p.b_lng,
            )
            session.add(cb)
            await session.flush()
            await svc.embed_complaint(cb)
            ca = Complaint(
                tracking_code=f"DE-{i:02d}-A", city_id=city.id,
                source=ComplaintSource.WEB, status=ComplaintStatus.SUBMITTED,
                title=p.label + " A", description=p.a_desc,
                location_text=p.a_loc, latitude=p.a_lat, longitude=p.a_lng,
            )
            session.add(ca)
            await session.flush()
            await svc.embed_complaint(ca)
            await session.flush()

            raw = await _raw_sim(session, ca.id, cb.id)
            links = await svc.find_candidates(ca.id)
            match = next(
                (link for link in links if link.candidate_complaint_id == cb.id), None
            )
            flagged = match is not None
            combined = match.combined_score if match else None
            loc_verdict = (match.evidence.get("location", {}).get("verdict")
                           if match else None)
            rows.append((p, flagged, raw, combined, loc_verdict))

            await session.execute(
                delete(Complaint).where(Complaint.id.in_([ca.id, cb.id]))
            )
            await session.flush()
        await session.rollback()
    return rows


def _report(rows) -> None:
    threshold = get_settings().duplicate_similarity_threshold
    print(f"Decision uses COMBINED score vs threshold {threshold} "
          f"(retrieval floor {get_settings().duplicate_retrieval_floor})")
    print(f"\n{'pair':28s} {'kind':14s} {'truth':5s} {'flag':4s} "
          f"{'raw':6s} {'comb':6s} locverdict")
    tp = tn = fp = fn = 0
    for p, flagged, raw, combined, locv in rows:
        truth = "DUP" if p.is_duplicate else "no"
        r = f"{raw:.3f}" if raw is not None else "  -  "
        c = f"{combined:.3f}" if combined is not None else "  -  "
        mark = ""
        if p.is_duplicate and flagged:
            tp += 1
        elif p.is_duplicate and not flagged:
            fn += 1
            mark = "  <-- FALSE NEGATIVE"
        elif not p.is_duplicate and flagged:
            fp += 1
            mark = "  <-- FALSE POSITIVE"
        else:
            tn += 1
        print(f"{p.label:28s} {p.kind:14s} {truth:5s} "
              f"{'YES' if flagged else 'no':4s} {r:6s} {c:6s} {locv or '-'}{mark}")
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    print(f"\nTP={tp} TN={tn} FP={fp} FN={fn} (n={len(rows)})")
    print(f"Precision={prec:.3f}  Recall={rec:.3f}  F1={f1:.3f}")


async def main() -> None:
    embedder = get_embedding_provider()
    print("=" * 84)
    print(f"Embedding: {embedder.name}/{embedder.model} (dim={embedder.dim})")
    print("=" * 84)
    rows = await _run_pairs()
    _report(rows)
    print("=" * 84)


if __name__ == "__main__":
    asyncio.run(main())
