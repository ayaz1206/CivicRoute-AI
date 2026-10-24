"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest

# Force hermetic, offline providers for the whole test suite BEFORE settings is
# first constructed. Tests must never depend on real API credentials or the
# developer's local .env (which may point at OpenAI). The fake providers are
# deterministic; the embedding dim is set to 1536 to match the migrated DB
# column (vector(1536)).
os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["EMBEDDING_DIM"] = "1536"

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import async_session_factory, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.city import City  # noqa: E402
from app.models.complaint import Complaint  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.status_history import StatusHistory  # noqa: E402

# Ensure the cached Settings picks up the overrides above.
get_settings.cache_clear()


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


@pytest.fixture
async def make_complaint(boston_city_id: int):
    """Factory that creates a live complaint and returns its id."""
    from app.schemas.complaint import ComplaintCreate
    from app.services.complaint_service import ComplaintService

    async def _make(
        title: str = "Large pothole on Main St",
        description: str = "Deep pothole near the crosswalk, a real hazard to cars.",
    ) -> int:
        async with async_session_factory() as session:
            svc = ComplaintService(session)
            complaint = await svc.create(
                ComplaintCreate(
                    city_id=boston_city_id, title=title, description=description
                )
            )
            return complaint.id

    return _make
