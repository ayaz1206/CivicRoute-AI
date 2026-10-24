"""Seed a reliable end-to-end demo scenario (M5).

Creates (idempotently) in the Boston city:
  - a demo admin user (demo@civicroute.ai / demo-password-123)
  - several resident complaints, including a near-duplicate pair and a sparse
    complaint that will trigger clarification

All complaints are LIVE (web) resident submissions — no historical 311 data is
created here. Run `python -m app.ingestion.cli` separately for 311 analytics.

Usage:
    python -m app.demo
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.city import City
from app.models.enums import UserRole
from app.schemas.complaint import ComplaintCreate
from app.services.auth_service import AuthService
from app.services.complaint_service import ComplaintService

DEMO_ADMIN_EMAIL = "demo@civicroute.ai"
DEMO_ADMIN_PASSWORD = "demo-password-123"

DEMO_COMPLAINTS = [
    {
        "title": "Large pothole on Dorchester Ave",
        "description": "A deep, dangerous pothole has opened on Dorchester Ave "
        "near the bus stop. Cars are swerving to avoid it.",
        "location_text": "Dorchester Ave near the bus stop",
    },
    {
        "title": "Pothole at Dorchester Ave bus stop",
        "description": "Big pothole on Dorchester Avenue right by the bus stop, "
        "it keeps damaging car tires and is a hazard.",
        "location_text": "Dorchester Ave bus stop",
    },
    {
        "title": "Street light out on Blue Hill Ave",
        "description": "The street light at the Blue Hill Ave crosswalk has been "
        "dark for a week and it feels unsafe at night.",
        "location_text": "Blue Hill Ave crosswalk",
    },
    {
        "title": "Something is wrong",
        "description": "There is a problem outside.",  # sparse -> clarification
    },
]


async def main() -> None:
    async with async_session_factory() as session:
        boston = await session.scalar(select(City).where(City.slug == "boston"))
        if boston is None:
            print("Boston city not found. Run `python -m app.seed` first.")
            return

        auth = AuthService(session)
        try:
            await auth.create_user(
                city_id=boston.id,
                email=DEMO_ADMIN_EMAIL,
                password=DEMO_ADMIN_PASSWORD,
                role=UserRole.ADMIN,
                full_name="Demo Admin",
            )
            print(f"Created demo admin: {DEMO_ADMIN_EMAIL} / {DEMO_ADMIN_PASSWORD}")
        except Exception as exc:  # noqa: BLE001 - idempotent re-runs
            print(f"Demo admin: {exc}")

        svc = ComplaintService(session)
        codes = []
        for c in DEMO_COMPLAINTS:
            complaint = await svc.create(
                ComplaintCreate(city_id=boston.id, **c)
            )
            codes.append((complaint.tracking_code, c["title"]))
        print("\nCreated demo complaints (tracking codes):")
        for code, title in codes:
            print(f"  {code}  {title}")

    print(
        "\nDemo ready. Sign in at /login with the demo admin, then follow "
        "docs/DEMO.md."
    )


if __name__ == "__main__":
    asyncio.run(main())
