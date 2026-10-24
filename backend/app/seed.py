"""Seed reference data for local development.

Creates the Boston city and a starter set of departments. This is reference
configuration only — it does NOT create any complaints and does NOT import any
historical Boston 311 data (that is a later milestone, kept strictly separate
from live complaints).

Usage:
    python -m app.seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.city import City
from app.models.department import Department

BOSTON_DEPARTMENTS = [
    ("Public Works", "public-works", ["pothole", "street", "sidewalk", "streetlight"]),
    ("Sanitation", "sanitation", ["trash", "recycling", "illegal-dumping"]),
    ("Parks & Recreation", "parks-rec", ["park", "tree", "playground"]),
    ("Transportation", "transportation", ["parking", "signal", "sign", "traffic"]),
    ("Water & Sewer", "water-sewer", ["water", "sewer", "flooding", "hydrant"]),
    ("Code Enforcement", "code-enforcement", ["noise", "building", "permit"]),
]


async def seed() -> None:
    async with async_session_factory() as session:
        boston = await session.scalar(select(City).where(City.slug == "boston"))
        if boston is None:
            boston = City(
                name="Boston",
                slug="boston",
                timezone="America/New_York",
                config={
                    "note": "Primary demo city. Historical 311 data is kept "
                    "separate from live complaints."
                },
            )
            session.add(boston)
            await session.flush()
            print(f"Created city: Boston (id={boston.id})")
        else:
            print(f"City already exists: Boston (id={boston.id})")

        existing = {
            d.slug
            for d in await session.scalars(
                select(Department).where(Department.city_id == boston.id)
            )
        }
        created = 0
        for name, slug, tags in BOSTON_DEPARTMENTS:
            if slug in existing:
                continue
            session.add(
                Department(
                    city_id=boston.id,
                    name=name,
                    slug=slug,
                    category_tags=tags,
                )
            )
            created += 1

        await session.commit()
        print(f"Departments created: {created} (skipped {len(existing)} existing)")


if __name__ == "__main__":
    asyncio.run(seed())
