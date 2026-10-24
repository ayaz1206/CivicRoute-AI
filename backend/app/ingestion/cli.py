"""CLI for Boston 311 ingestion.

Usage:
    python -m app.ingestion.cli            # ingest default max (5000) recent
    python -m app.ingestion.cli --max 1000 # ingest 1000 recent records

Idempotent: safe to re-run; existing records are updated, not duplicated.
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.ingestion.service import IngestionService


async def _run(max_records: int) -> None:
    async with async_session_factory() as session:
        service = IngestionService(session)
        print(f"Ingesting up to {max_records} recent Boston 311 records…")
        result = await service.ingest_from_api(max_records=max_records)
        print("Done:")
        for k, v in result.as_dict().items():
            print(f"  {k}: {v}")
        if result.errors:
            print(f"  first errors: {result.errors[:3]}")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest Boston 311 data")
    parser.add_argument(
        "--max",
        type=int,
        default=settings.boston_311_max_records,
        help="maximum number of recent records to ingest",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.max))


if __name__ == "__main__":
    main()
