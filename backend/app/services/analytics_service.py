"""Analytics over historical Boston 311 data.

All queries run against the dedicated ``historical_311_requests`` table — the
analytics surface is historical/reference data and never touches live
complaints. Scoped by city (Boston) so the design stays multi-city.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.city import City
from app.models.historical_request import Historical311Request as H


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _city_id(self, slug: str = "boston") -> int | None:
        return await self.session.scalar(select(City.id).where(City.slug == slug))

    async def summary(self, city_id: int) -> dict:
        total = await self.session.scalar(
            select(func.count()).select_from(H).where(H.city_id == city_id)
        )
        open_count = await self.session.scalar(
            select(func.count())
            .select_from(H)
            .where(H.city_id == city_id, func.lower(H.case_status) == "open")
        )
        closed_count = await self.session.scalar(
            select(func.count())
            .select_from(H)
            .where(H.city_id == city_id, func.lower(H.case_status) == "closed")
        )
        # Average resolution time in hours for closed cases with both timestamps.
        avg_hours = await self.session.scalar(
            select(
                func.avg(
                    cast(func.extract("epoch", H.closed_at - H.opened_at), Integer)
                    / 3600.0
                )
            ).where(
                H.city_id == city_id,
                H.closed_at.is_not(None),
                H.opened_at.is_not(None),
            )
        )
        return {
            "total": int(total or 0),
            "open": int(open_count or 0),
            "closed": int(closed_count or 0),
            "avg_resolution_hours": round(float(avg_hours), 1) if avg_hours else None,
        }

    async def _group_count(
        self, city_id: int, column, limit: int
    ) -> list[dict]:
        rows = await self.session.execute(
            select(column, func.count().label("count"))
            .where(H.city_id == city_id, column.is_not(None))
            .group_by(column)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [{"key": key, "count": int(count)} for key, count in rows.all()]

    async def by_category(self, city_id: int, limit: int = 15) -> list[dict]:
        # Boston's "reason" is the most useful category-like dimension.
        return await self._group_count(city_id, H.reason, limit)

    async def by_neighborhood(self, city_id: int, limit: int = 15) -> list[dict]:
        return await self._group_count(city_id, H.neighborhood, limit)

    async def by_department(self, city_id: int, limit: int = 15) -> list[dict]:
        return await self._group_count(city_id, H.department, limit)

    async def by_status(self, city_id: int, limit: int = 10) -> list[dict]:
        return await self._group_count(city_id, H.case_status, limit)

    async def trend(self, city_id: int, days: int = 30) -> list[dict]:
        """Daily counts of opened cases over the last `days` days present in
        the data (relative to the most recent opened_at)."""
        latest = await self.session.scalar(
            select(func.max(H.opened_at)).where(H.city_id == city_id)
        )
        if latest is None:
            return []
        start = latest - dt.timedelta(days=days)
        day = func.date_trunc("day", H.opened_at).label("day")
        rows = await self.session.execute(
            select(day, func.count().label("count"))
            .where(
                H.city_id == city_id,
                H.opened_at.is_not(None),
                H.opened_at >= start,
            )
            .group_by(day)
            .order_by(day)
        )
        return [
            {"date": d.date().isoformat(), "count": int(c)} for d, c in rows.all()
        ]
