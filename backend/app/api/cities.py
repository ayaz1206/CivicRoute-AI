"""City and department read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_city_service
from app.schemas.city import CityRead, DepartmentRead
from app.services.city_service import CityService

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=list[CityRead], summary="List cities")
async def list_cities(service: CityService = Depends(get_city_service)) -> list[CityRead]:
    cities = await service.list_cities()
    return [CityRead.model_validate(c) for c in cities]


@router.get(
    "/{city_id}/departments",
    response_model=list[DepartmentRead],
    summary="List a city's departments",
)
async def list_departments(
    city_id: int, service: CityService = Depends(get_city_service)
) -> list[DepartmentRead]:
    departments = await service.list_departments(city_id)
    return [DepartmentRead.model_validate(d) for d in departments]
