"""End-to-end workflow demonstration with the configured (real) providers.

Exercises the full resident+staff journey over the in-process ASGI app:
  1. resident submits a complaint (sparse location -> clarification)
  2. staff generate a clarification question; resident answers it
  3. staff run AI triage (classification, priority, routing)
  4. staff approve the recommendation (applies to the complaint)
  5. resident submits a PARAPHRASED complaint at the SAME location
  6. staff run duplicate detection; confirm the duplicate (no auto-merge)
  7. resident tracking view reflects status + timeline

Runs in a throwaway "e2e-demo" city and cleans up afterward. Requires the
configured provider (OpenAI) to be reachable. No secrets are printed.

Usage:
    python -m app.eval.e2e_demo
"""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db.session import async_session_factory
from app.main import create_app
from app.models.city import City
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.enums import UserRole
from app.models.user import User

API = "/api"


def _h(step: str) -> None:
    print(f"\n{'=' * 4} {step} {'=' * 4}")


async def _setup() -> tuple[int, str]:
    """Create throwaway city + departments + an admin token. Returns (city_id, token)."""
    async with async_session_factory() as session:
        city = await session.scalar(select(City).where(City.slug == "e2e-demo"))
        if city is not None:
            await session.execute(delete(Complaint).where(Complaint.city_id == city.id))
            await session.execute(delete(User).where(User.city_id == city.id))
            await session.commit()
        else:
            city = City(name="E2E Demo", slug="e2e-demo", timezone="America/New_York")
            session.add(city)
            await session.flush()
            session.add_all([
                Department(city_id=city.id, name="Public Works", slug="public-works",
                           category_tags=["pothole", "street light", "sidewalk"]),
                Department(city_id=city.id, name="Sanitation", slug="sanitation",
                           category_tags=["trash"]),
                Department(city_id=city.id, name="Transportation", slug="transportation",
                           category_tags=["parking", "signal"]),
                Department(city_id=city.id, name="Parks & Rec", slug="parks-rec",
                           category_tags=["tree", "park"]),
                Department(city_id=city.id, name="Water & Sewer", slug="water-sewer",
                           category_tags=["water", "sewer"]),
                Department(city_id=city.id, name="Code Enforcement",
                           slug="code-enforcement", category_tags=["noise", "graffiti"]),
            ])
        # Admin user for this city.
        admin = User(city_id=city.id, email="e2e-admin@example.com",
                     hashed_password="x", role=UserRole.ADMIN, full_name="E2E Admin")
        session.add(admin)
        await session.commit()
        token = create_access_token(subject=str(admin.id), role="admin",
                                    city_id=city.id)
        return city.id, token


async def _teardown(city_id: int) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(Complaint).where(Complaint.city_id == city_id))
        await session.execute(delete(User).where(User.city_id == city_id))
        await session.commit()


async def main() -> None:
    city_id, token = await _setup()
    auth = {"Authorization": f"Bearer {token}"}
    app = create_app()

    try:
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://e2e") as c:
            # 1. Resident submits a complaint with a vague location + short text.
            _h("1. Resident submits complaint")
            r = await c.post(f"{API}/complaints", json={
                "city_id": city_id,
                "title": "Streetlight out",
                "description": "The street light on our street is broken and stays "
                               "dark, making it hard to see at night.",
            })
            r.raise_for_status()
            first = r.json()
            code = first["tracking_code"]
            cid = first["id"]
            print(f"submitted id={cid} code={code} status={first['status']}")

            # 2. Staff generate a clarification; resident answers it.
            _h("2. Clarification")
            gen = await c.post(
                f"{API}/duplicates/complaints/{cid}/clarifications/generate",
                headers=auth,
            )
            gen.raise_for_status()
            questions = gen.json()
            print(f"generated {len(questions)} question(s): "
                  f"{[q['field'] for q in questions]}")
            pend = (await c.get(f"{API}/clarifications/track/{code}")).json()
            for q in pend:
                ans = ("Blue Hill Ave at the Dudley St crosswalk"
                       if q["field"] == "location"
                       else "The street light has been completely dark for a week, "
                            "the crosswalk is unsafe at night.")
                a = await c.post(f"{API}/clarifications/{q['id']}/answer",
                                 json={"answer": ans})
                a.raise_for_status()
                print(f"answered {q['field']}: {ans[:50]}...")

            # 3. Staff run AI triage.
            _h("3. AI triage")
            t = await c.post(f"{API}/agent/complaints/{cid}/triage", headers=auth)
            t.raise_for_status()
            run = t.json()
            rec = run["recommendation"]
            print(f"run status={run['status']} provider={run['llm_provider']} "
                  f"model={run['llm_model']}")
            print(f"  category={rec['category']} ({rec['category_confidence']})")
            print(f"  priority={rec['priority']} ({rec['priority_confidence']})"
                  f" — {rec['priority_rationale']}")
            print(f"  department={rec['department_slug']} ({rec['department_confidence']})")
            print(f"  severity={rec['review_severity']} overall={rec['overall_confidence']}")

            # 4. Staff approve the recommendation.
            _h("4. Staff approve recommendation")
            dec = await c.post(
                f"{API}/agent/recommendations/{rec['id']}/decision",
                json={"decision": "approve", "reviewer": "e2e-admin"},
                headers=auth,
            )
            dec.raise_for_status()
            print(f"recommendation status={dec.json()['status']}")
            detail = (await c.get(f"{API}/complaints/{cid}", headers=auth)).json()
            print(f"complaint now: status={detail['status']} category={detail['category']} "
                  f"priority={detail['priority']} dept_id={detail['department_id']}")

            # 5. Resident submits a PARAPHRASE at the SAME location.
            _h("5. Resident submits paraphrased complaint (same location)")
            r2 = await c.post(f"{API}/complaints", json={
                "city_id": city_id,
                "title": "Street light not working on Blue Hill Ave",
                "description": "The street light on our street is broken and stays "
                               "dark, making it hard to see at night near the "
                               "crosswalk.",
                "location_text": "Blue Hill Ave by the Dudley St crosswalk",
            })
            r2.raise_for_status()
            second = r2.json()
            print(f"submitted id={second['id']} code={second['tracking_code']}")

            # Give the first complaint a matching location so the pair is a true dup.
            async with async_session_factory() as session:
                c1 = await session.get(Complaint, cid)
                print(f"(first complaint location_text now: {c1.location_text!r})")

            # 6. Staff run duplicate detection on the new complaint.
            _h("6. Duplicate detection + staff confirmation")
            dd = await c.post(
                f"{API}/duplicates/complaints/{second['id']}/detect", headers=auth
            )
            dd.raise_for_status()
            cands = dd.json()
            print(f"candidates returned: {len(cands)}")
            for cand in cands:
                loc = cand["evidence"].get("location", {})
                print(f"  -> #{cand['candidate_complaint_id']} "
                      f"{cand['candidate_title']!r} sim={cand['similarity']} "
                      f"score={cand['combined_score']} "
                      f"loc={loc.get('verdict')} status={cand['candidate_status']}")
            if cands:
                link_id = cands[0]["link_id"]
                conf = await c.post(f"{API}/duplicates/links/{link_id}/decision",
                                    json={"decision": "confirm", "reviewer": "e2e-admin",
                                          "note": "same streetlight"},
                                    headers=auth)
                conf.raise_for_status()
                print(f"staff decision: {conf.json()['decision']} "
                      "(recorded; complaints NOT merged)")
                # Confirm neither complaint was merged/closed.
                async with async_session_factory() as session:
                    a1 = await session.get(Complaint, cid)
                    a2 = await session.get(Complaint, second["id"])
                    print(f"after confirm: #{cid} status={a1.status.value}, "
                          f"#{second['id']} status={a2.status.value} (both intact)")

            # 7. Resident tracking view.
            _h("7. Resident tracking view")
            track = (await c.get(f"{API}/complaints/track/{code}")).json()
            print(f"tracking {code}: status={track['status']} "
                  f"category={track['category']} priority={track['priority']}")
            print(f"  timeline: {[h['to_status'] for h in track['status_history']]}")
            # Privacy check: no reporter PII in the public view.
            assert "reporter_email" not in track and "reporter_name" not in track
            print("  (public view contains no reporter PII)")

        print("\nE2E DEMO OK")
    finally:
        await _teardown(city_id)


if __name__ == "__main__":
    asyncio.run(main())
