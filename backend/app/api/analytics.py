"""Analytics endpoints over historical Boston 311 data (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.analytics import (
    AnalyticsOverview,
    CountItem,
    Summary,
    TrendPoint,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _service(session: AsyncSession = Depends(get_session)) -> AnalyticsService:
    return AnalyticsService(session)


async def _resolve_city(service: AnalyticsService, city: str) -> int:
    city_id = await service._city_id(city)
    if city_id is None:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    return city_id


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Historical 311 analytics overview for a city",
)
async def overview(
    city: str = Query(default="boston"),
    trend_days: int = Query(default=30, ge=1, le=365),
    service: AnalyticsService = Depends(_service),
) -> AnalyticsOverview:
    city_id = await _resolve_city(service, city)
    summary = await service.summary(city_id)
    return AnalyticsOverview(
        city=city,
        summary=Summary(**summary),
        by_category=[CountItem(**r) for r in await service.by_category(city_id)],
        by_neighborhood=[
            CountItem(**r) for r in await service.by_neighborhood(city_id)
        ],
        by_department=[CountItem(**r) for r in await service.by_department(city_id)],
        by_status=[CountItem(**r) for r in await service.by_status(city_id)],
        trend=[TrendPoint(**r) for r in await service.trend(city_id, trend_days)],
    )
