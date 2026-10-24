"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.db.session import async_session_factory, engine
from app.main import create_app
from app.models.city import City
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.status_history import StatusHistory


@pytest.fixture(autouse=True)
async def _dispose_engine() -> AsyncGenerator[None, None]:
    """Dispose the shared async engine after each test.

    pytest-asyncio runs each test on its own event loop. The module-level engine
    pools connections bound to the loop that first used them, so without disposal
    a pooled connection outlives its loop and asyncpg raises "Event loop is
    closed" during teardown. Disposing after each test keeps connections
    loop-local.
    """
    yield
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """An httpx client wired to the FastAPI app via ASGI transport.

    Uses in-process ASGI transport so no network server is needed.
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def boston_city_id() -> int:
    """Ensure a clean Boston city with one department exists for the test.

    Clears live complaint data first so tests are isolated. Requires the DB to
    be running and migrated (see docs/SETUP.md).
    """
    async with async_session_factory() as session:
        # Clean dependent data between tests (status_history cascades).
        await session.execute(delete(StatusHistory))
        await session.execute(delete(Complaint))
        await session.commit()

        city = await session.scalar(select(City).where(City.slug == "boston-test"))
        if city is None:
            city = City(name="Boston (test)", slug="boston-test", timezone="America/New_York")
            session.add(city)
            await session.flush()
            session.add(
                Department(
                    city_id=city.id,
                    name="Public Works",
                    slug="public-works",
                    category_tags=["pothole"],
                )
            )
            await session.commit()
        return city.id
