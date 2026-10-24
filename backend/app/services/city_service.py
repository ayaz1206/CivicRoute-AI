"""City/Department read service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.city import City
from app.models.department import Department
from app.services.errors import NotFoundError


class CityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_cities(self) -> list[City]:
        rows = await self.session.scalars(select(City).order_by(City.name))
        return list(rows)

    async def get_city(self, city_id: int) -> City:
        city = await self.session.get(City, city_id)
        if city is None:
            raise NotFoundError(f"City {city_id} not found")
        return city

    async def list_departments(self, city_id: int) -> list[Department]:
        await self.get_city(city_id)
        rows = await self.session.scalars(
            select(Department)
            .where(Department.city_id == city_id)
            .order_by(Department.name)
        )
        return list(rows)
