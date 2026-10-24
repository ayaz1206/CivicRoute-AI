"""Idempotent ingestion of Boston 311 records into the historical table."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.client import Boston311Client
from app.ingestion.parser import ParseError, parse_record
from app.models.city import City
from app.models.historical_request import Historical311Request


@dataclass
class IngestionResult:
    requested: int = 0
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "fetched": self.fetched,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "error_count": len(self.errors),
        }


# Columns updated on conflict (everything except the natural key and id).
_UPDATE_COLS = (
    "case_title",
    "subject",
    "reason",
    "case_type",
    "queue",
    "department",
    "case_status",
    "closure_reason",
    "neighborhood",
    "location_street",
    "zipcode",
    "latitude",
    "longitude",
    "opened_at",
    "closed_at",
    "source",
    "city_id",
)


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _boston_city_id(self) -> int:
        city = await self.session.scalar(select(City).where(City.slug == "boston"))
        if city is None:
            raise RuntimeError(
                "Boston city not found. Run `python -m app.seed` first."
            )
        return city.id

    async def _upsert_batch(self, rows: list[dict[str, Any]]) -> tuple[int, int]:
        """Upsert a batch on case_enquiry_id. Returns (inserted, updated)."""
        if not rows:
            return 0, 0
        # Pre-count which keys already exist so we can report inserted vs updated.
        keys = [r["case_enquiry_id"] for r in rows]
        existing = set(
            await self.session.scalars(
                select(Historical311Request.case_enquiry_id).where(
                    Historical311Request.case_enquiry_id.in_(keys)
                )
            )
        )
        stmt = pg_insert(Historical311Request).values(rows)
        update_set = {c: getattr(stmt.excluded, c) for c in _UPDATE_COLS}
        stmt = stmt.on_conflict_do_update(
            index_elements=["case_enquiry_id"], set_=update_set
        )
        await self.session.execute(stmt)
        updated = sum(1 for k in keys if k in existing)
        return len(rows) - updated, updated

    async def ingest_records(
        self, raw_records: Iterable[dict[str, Any]], *, city_id: int
    ) -> IngestionResult:
        """Parse and upsert an iterable of raw records (used by CLI and tests)."""
        result = IngestionResult()
        batch: list[dict[str, Any]] = []
        seen: set[str] = set()

        for raw in raw_records:
            result.fetched += 1
            try:
                parsed = parse_record(raw, city_id=city_id)
            except ParseError as exc:
                result.skipped += 1
                result.errors.append(str(exc))
                continue
            # De-dupe within the same run (CKAN can rarely repeat on paging).
            key = parsed["case_enquiry_id"]
            if key in seen:
                result.skipped += 1
                continue
            seen.add(key)
            batch.append(parsed)
            if len(batch) >= 500:
                ins, upd = await self._upsert_batch(batch)
                result.inserted += ins
                result.updated += upd
                batch.clear()

        if batch:
            ins, upd = await self._upsert_batch(batch)
            result.inserted += ins
            result.updated += upd

        await self.session.commit()
        return result

    async def ingest_from_api(
        self, *, max_records: int, client: Boston311Client | None = None
    ) -> IngestionResult:
        """Fetch recent records from the Boston 311 API and ingest them."""
        city_id = await self._boston_city_id()
        client = client or Boston311Client()
        raw: list[dict[str, Any]] = [r async for r in client.iter_records(max_records)]
        result = await self.ingest_records(raw, city_id=city_id)
        result.requested = max_records
        return result
