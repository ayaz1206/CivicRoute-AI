"""Realistic positive/negative duplicate-pair evaluation (M5).

Verifies the detector ranks genuine duplicate pairs above the similarity
threshold and keeps clearly-unrelated pairs below it, using the configured
(default fake) embedder.
"""

from __future__ import annotations

import pytest

from app.db.session import async_session_factory
from app.models.complaint import Complaint
from app.services.duplicate_service import DuplicateService

# (title_a, desc_a, title_b, desc_b, expected_duplicate)
PAIRS = [
    (
        "Pothole on Dorchester Ave",
        "Large deep pothole on Dorchester Ave near the bus stop damaging cars.",
        "Dorchester Ave pothole by bus stop",
        "Deep dangerous pothole on Dorchester Ave at the bus stop, cars damaged.",
        True,
    ),
    (
        "Street light out on Elm",
        "The street light on Elm Street has been out and dark for a week.",
        "Dark street light Elm Street",
        "Street light on Elm Street is not working, the block is very dark.",
        True,
    ),
    (
        "Overflowing trash on Beacon",
        "Trash barrels overflowing with garbage on Beacon Street sidewalk.",
        "Loud party next door",
        "Neighbors throwing a loud party with music until 3am every weekend.",
        False,
    ),
    (
        "Broken playground swing",
        "The swing set at the park playground is broken and unsafe for children.",
        "Pothole downtown",
        "A pothole has formed in the downtown road causing traffic problems.",
        False,
    ),
]


@pytest.mark.parametrize("ta,da,tb,db,expect_dup", PAIRS)
async def test_duplicate_pair(make_complaint, ta, da, tb, db, expect_dup) -> None:
    a = await make_complaint(title=ta, description=da)
    b = await make_complaint(title=tb, description=db)

    async with async_session_factory() as session:
        svc = DuplicateService(session)
        for cid in (a, b):
            c = await session.get(Complaint, cid)
            await svc.embed_complaint(c)
        await session.commit()

    async with async_session_factory() as session:
        links = await DuplicateService(session).find_candidates(a)

    matched = any(link.candidate_complaint_id == b for link in links)
    if expect_dup:
        assert matched, f"expected {tb!r} to be flagged as a duplicate of {ta!r}"
    else:
        assert not matched, f"did not expect {tb!r} to be flagged as duplicate of {ta!r}"
