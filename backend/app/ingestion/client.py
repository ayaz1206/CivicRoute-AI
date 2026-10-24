"""HTTP client for the Boston 311 CKAN datastore API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings


class Boston311Client:
    """Fetches recent 311 records via CKAN ``datastore_search``.

    Records are returned most-recent-first (sorted by ``open_dt`` descending)
    and streamed page by page so large pulls stay memory-bounded.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        resource_id: str | None = None,
        page_size: int | None = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.boston_311_base_url
        self.resource_id = resource_id or settings.boston_311_resource_id
        self.page_size = page_size or settings.boston_311_page_size
        self.timeout = timeout

    async def iter_records(self, max_records: int) -> AsyncIterator[dict[str, Any]]:
        """Yield up to ``max_records`` records, newest first."""
        fetched = 0
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            while fetched < max_records:
                page = min(self.page_size, max_records - fetched)
                params = {
                    "resource_id": self.resource_id,
                    "limit": page,
                    "offset": fetched,
                    "sort": "open_dt desc",
                }
                resp = await http.get(self.base_url, params=params)
                resp.raise_for_status()
                payload = resp.json()
                if not payload.get("success"):
                    raise RuntimeError("Boston 311 API returned success=false")
                records = payload["result"]["records"]
                if not records:
                    break
                for rec in records:
                    yield rec
                    fetched += 1
                    if fetched >= max_records:
                        break
                if len(records) < page:
                    break  # reached the end of the dataset
