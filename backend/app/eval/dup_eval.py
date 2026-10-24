"""Real-embedding duplicate-detection evaluation (M5 migration).

Submits labeled positive (true duplicate) and negative (unrelated) complaint
pairs, embeds them with the configured provider (OpenAI for this run), and
reports the pairwise cosine similarity for each. Prints a suggested threshold
derived from the gap between positive and negative similarity distributions.

This creates LIVE complaints in a throwaway city ("dup-eval") so it never
pollutes Boston demo data, and cleans them up afterwards. Historical records are
untouched.

Usage:
    python -m app.eval.dup_eval
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, select

from app.db.session import async_session_factory
from app.embeddings.factory import get_embedding_provider
from app.models.city import City
from app.models.complaint import Complaint
from app.models.duplicate import ComplaintEmbedding
from app.models.enums import ComplaintSource, ComplaintStatus

# (label, text_a, text_b, is_duplicate)
PAIRS = [
    ("pothole/pothole-same-spot",
     "Large deep pothole on Dorchester Ave near the bus stop, cars swerving to avoid it.",
     "Big dangerous pothole on Dorchester Avenue by the bus stop damaging car tires.",
     True),
    ("streetlight/streetlight-same",
     "The street light at the Blue Hill Ave crosswalk has been dark for a week, unsafe at night.",
     "Street light out on Blue Hill Ave by the crosswalk, very dark after sunset.",
     True),
    ("trash/trash-same",
     "Trash barrels overflowing with garbage spilling onto the sidewalk in the South End.",
     "Overflowing public trash cans on the South End sidewalk, garbage everywhere.",
     True),
    ("graffiti/graffiti-paraphrase",
     "Someone spray-painted graffiti across the brick wall at the playground.",
     "The playground wall has fresh graffiti tags sprayed all over it.",
     True),
    ("pothole/noise-unrelated",
     "Large deep pothole on Dorchester Ave near the bus stop.",
     "Neighbors playing extremely loud music past midnight every weekend.",
     False),
    ("streetlight/tax-unrelated",
     "Street light out on Blue Hill Ave, the block is very dark.",
     "I have a question about the amount on my quarterly property tax bill.",
     False),
    ("trash/tree-unrelated",
     "Trash barrels overflowing onto the sidewalk in the South End.",
     "A large fallen tree branch is blocking the sidewalk on Elm Street.",
     False),
    ("pothole/pothole-different-topic-far",
     "Pothole damaging cars on Dorchester Ave.",
     "Broken playground swing set is unsafe for children at the park.",
     False),
]


async def _cosine(session, emb_a, emb_b) -> float:
    # Use pgvector to compute cosine distance between two stored vectors.
    row = await session.execute(
        select(1 - ComplaintEmbedding.embedding.cosine_distance(emb_b.embedding)).where(
            ComplaintEmbedding.id == emb_a.id
        )
    )
    return float(row.scalar())


async def main() -> None:
    embedder = get_embedding_provider()
    print("=" * 72)
    print(f"Embedding provider: {embedder.name} / {embedder.model} (dim={embedder.dim})")
    print("=" * 72)

    async with async_session_factory() as session:
        city = await session.scalar(select(City).where(City.slug == "dup-eval"))
        if city is None:
            city = City(name="Dup Eval", slug="dup-eval", timezone="UTC")
            session.add(city)
            await session.flush()
        # Clean any previous eval complaints for idempotency.
        ids = [
            c.id
            for c in await session.scalars(
                select(Complaint).where(Complaint.city_id == city.id)
            )
        ]
        if ids:
            await session.execute(delete(Complaint).where(Complaint.id.in_(ids)))
            await session.commit()

        from app.services.duplicate_service import DuplicateService

        svc = DuplicateService(session, embedder=embedder)
        positives: list[float] = []
        negatives: list[float] = []
        rows_out = []

        for i, (label, ta, tb, is_dup) in enumerate(PAIRS):
            ca = Complaint(
                tracking_code=f"DE-{i:02d}-A",
                city_id=city.id, source=ComplaintSource.WEB,
                status=ComplaintStatus.SUBMITTED, title=label + " A",
                description=ta,
            )
            cb = Complaint(
                tracking_code=f"DE-{i:02d}-B",
                city_id=city.id, source=ComplaintSource.WEB,
                status=ComplaintStatus.SUBMITTED, title=label + " B",
                description=tb,
            )
            session.add_all([ca, cb])
            await session.flush()
            ea = await svc.embed_complaint(ca)
            eb = await svc.embed_complaint(cb)
            await session.flush()
            sim = await _cosine(session, ea, eb)
            (positives if is_dup else negatives).append(sim)
            rows_out.append((label, is_dup, sim))

        await session.rollback()  # discard throwaway complaints

    print(f"\n{'pair':40s} {'label':10s} similarity")
    for label, is_dup, sim in rows_out:
        print(f"{label:40s} {'DUP' if is_dup else 'unrelated':10s} {sim:.4f}")

    print("\n--- distributions ---")
    print(f"positives: min={min(positives):.4f} max={max(positives):.4f} "
          f"mean={sum(positives)/len(positives):.4f}")
    print(f"negatives: min={min(negatives):.4f} max={max(negatives):.4f} "
          f"mean={sum(negatives)/len(negatives):.4f}")

    lo_pos = min(positives)
    hi_neg = max(negatives)
    gap_mid = round((lo_pos + hi_neg) / 2, 3)
    print("\n--- threshold recommendation ---")
    print(f"lowest positive  : {lo_pos:.4f}")
    print(f"highest negative : {hi_neg:.4f}")
    if lo_pos > hi_neg:
        print(f"CLEAN SEPARATION. Recommended threshold ~= {gap_mid} "
              f"(midpoint of the gap). Separates all {len(positives)} positives "
              f"from all {len(negatives)} negatives in this set.")
    else:
        print(f"OVERLAP between positives and negatives (lowest pos {lo_pos:.4f} "
              f"<= highest neg {hi_neg:.4f}). No perfectly separating threshold; "
              f"consider ~{gap_mid} and expect some false pos/neg.")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
