"""Safe re-embedding procedure (M5).

Re-embeds all live complaints with the currently configured embedding provider.
Handles the dimension-change case safely:

- If the configured EMBEDDING_DIM differs from the existing
  ``complaint_embeddings.embedding`` column dimension, the vectors are
  incompatible. Changing the column type requires a migration; this tool
  detects the mismatch and refuses to proceed (rather than corrupting data),
  printing the exact steps.

Usage:
    python -m app.embeddings.reembed            # re-embed with current provider
    python -m app.embeddings.reembed --check    # report dims, make no changes
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select, text

from app.db.session import async_session_factory
from app.embeddings.factory import get_embedding_provider
from app.models.complaint import Complaint
from app.models.enums import ComplaintSource
from app.services.duplicate_service import DuplicateService


async def _column_dim(session) -> int | None:
    """Return the declared dimension of the embedding column, if any rows/typmod."""
    # pgvector stores dimension in atttypmod; query it from the catalog.
    row = await session.execute(
        text(
            "SELECT a.atttypmod FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "WHERE c.relname = 'complaint_embeddings' AND a.attname = 'embedding'"
        )
    )
    val = row.scalar()
    if val is None or val < 0:
        return None
    return int(val)


async def run(check_only: bool) -> None:
    provider = get_embedding_provider()
    configured_dim = provider.dim

    async with async_session_factory() as session:
        col_dim = await _column_dim(session)
        print(f"Configured provider : {provider.name} (model={provider.model})")
        print(f"Configured dim      : {configured_dim}")
        print(f"DB column dim       : {col_dim}")

        if col_dim is not None and col_dim != configured_dim:
            print(
                "\nDIMENSION MISMATCH. The embedding column is "
                f"vector({col_dim}) but the provider produces {configured_dim}-d "
                "vectors. Re-embedding is refused to avoid corrupting data.\n\n"
                "To migrate safely:\n"
                "  1. Create an Alembic migration that ALTERs "
                "complaint_embeddings.embedding to "
                f"vector({configured_dim}) (and drops/recreates the HNSW index).\n"
                "  2. Set EMBEDDING_DIM="
                f"{configured_dim} in your environment.\n"
                "  3. Run `alembic upgrade head`.\n"
                "  4. Re-run this tool to repopulate embeddings.\n"
            )
            return

        if check_only:
            count = await session.scalar(
                select(Complaint.id).where(Complaint.source == ComplaintSource.WEB)
            )
            print(f"\nCheck only — no changes. Live complaints exist: {count is not None}")
            return

        # Re-embed every live complaint.
        svc = DuplicateService(session, embedder=provider)
        complaints = list(
            await session.scalars(
                select(Complaint).where(Complaint.source == ComplaintSource.WEB)
            )
        )
        done = 0
        for c in complaints:
            await svc.embed_complaint(c)
            done += 1
            if done % 100 == 0:
                await session.commit()
                print(f"  re-embedded {done}/{len(complaints)}")
        await session.commit()
        print(f"\nRe-embedded {done} live complaints with {provider.name}/{provider.model}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-embed live complaints")
    parser.add_argument("--check", action="store_true", help="report only")
    args = parser.parse_args()
    asyncio.run(run(args.check))


if __name__ == "__main__":
    main()
