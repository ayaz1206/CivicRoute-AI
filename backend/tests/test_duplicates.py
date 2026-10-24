"""Tests for semantic duplicate detection."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.embeddings.base import EmbeddingError
from app.models.complaint import Complaint
from app.models.duplicate import ComplaintEmbedding
from app.models.enums import DuplicateDecision
from app.services.duplicate_service import DuplicateService
from app.services.errors import NotFoundError


@pytest.fixture(autouse=True)
def _fake_threshold(monkeypatch):
    """The deterministic fake embedder has a lower similarity scale than real
    sentence embeddings; pin a fake-appropriate threshold so ranking/filtering
    logic is tested independently of the OpenAI-calibrated production default."""
    settings = get_settings()
    monkeypatch.setattr(settings, "duplicate_similarity_threshold", 0.3)
    yield


async def _embed_all(cids: list[int]) -> None:
    async with async_session_factory() as session:
        svc = DuplicateService(session)
        for cid in cids:
            c = await session.get(Complaint, cid)
            await svc.embed_complaint(c)
        await session.commit()


async def test_embedding_persisted_with_metadata(make_complaint) -> None:
    cid = await make_complaint(
        title="Pothole on Main St",
        description="Deep pothole in the road on Main St causing damage.",
    )
    async with async_session_factory() as session:
        emb = await session.scalar(
            select(ComplaintEmbedding).where(ComplaintEmbedding.complaint_id == cid)
        )
    # Submission auto-embeds (best-effort) with the configured provider. The
    # test suite forces the deterministic fake provider at 1536 dims (matching
    # the migrated DB column).
    assert emb is not None
    assert emb.provider == "fake"
    assert emb.dim == 1536
    assert emb.model


async def test_similar_complaints_ranked_above_threshold(make_complaint) -> None:
    base = await make_complaint(
        title="Large pothole on Dorchester Ave",
        description="There is a large dangerous pothole on Dorchester Ave near "
        "the bus stop damaging cars.",
    )
    similar = await make_complaint(
        title="Pothole Dorchester Ave",
        description="Big pothole on Dorchester Ave by the bus stop, cars are "
        "getting damaged, very dangerous.",
    )
    unrelated = await make_complaint(
        title="Loud music at night",
        description="Neighbors playing extremely loud music late at night every "
        "weekend disturbing everyone.",
    )
    await _embed_all([base, similar, unrelated])

    async with async_session_factory() as session:
        links = await DuplicateService(session).find_candidates(base)

    assert len(links) >= 1
    top = links[0]
    # The near-identical pothole complaint should be the top candidate.
    assert top.candidate_complaint_id == similar
    assert top.similarity >= 0.6
    # Unrelated noise complaint should not outrank the similar one.
    cand_ids = [link.candidate_complaint_id for link in links]
    if unrelated in cand_ids:
        assert cand_ids.index(similar) < cand_ids.index(unrelated)


async def test_threshold_filters_dissimilar(make_complaint) -> None:
    a = await make_complaint(
        title="Broken playground swing",
        description="The swing set at the playground is broken and unsafe for kids.",
    )
    b = await make_complaint(
        title="Tax billing question",
        description="I have a question about my quarterly property tax bill amount.",
    )
    await _embed_all([a, b])

    async with async_session_factory() as session:
        links = await DuplicateService(session).find_candidates(a)
    # Unrelated complaint should fall below the similarity threshold.
    assert all(link.candidate_complaint_id != b for link in links)


async def test_missing_location_reported_not_invented(make_complaint) -> None:
    a = await make_complaint(
        title="Graffiti on wall",
        description="Someone painted graffiti on the brick wall by the lot.",
    )
    b = await make_complaint(
        title="Graffiti on the wall",
        description="Graffiti was painted on a brick wall near the empty lot.",
    )
    await _embed_all([a, b])
    async with async_session_factory() as session:
        links = await DuplicateService(session).find_candidates(a)

    assert links, "expected at least one candidate"
    loc = links[0].evidence["location"]
    # Neither complaint has coordinates or location_text -> evidence says so,
    # no address/coordinates are fabricated, and missing data is treated as
    # UNKNOWN (never as a mismatch).
    assert loc["type"] == "none"
    assert loc["verdict"] == "unknown"
    assert "no location evidence" in loc["note"]


async def test_location_verdicts(make_complaint) -> None:
    """Location evidence classifies match / mismatch / unknown correctly and
    missing data never counts as a mismatch."""
    from app.models.complaint import Complaint
    from app.services.duplicate_service import DuplicateService

    async with async_session_factory() as session:
        svc = DuplicateService(session)

        def c(**kw):
            return Complaint(tracking_code="x", city_id=1, title="t",
                             description="d", **kw)

        # Coordinates ~40m apart -> match.
        near = svc._location_evidence(
            c(latitude=42.3426, longitude=-71.0971),
            c(latitude=42.3429, longitude=-71.0972),
        )
        assert near["verdict"] == "match"

        # Coordinates ~3km apart -> mismatch.
        far = svc._location_evidence(
            c(latitude=42.3426, longitude=-71.0971),
            c(latitude=42.3188, longitude=-71.0846),
        )
        assert far["verdict"] == "mismatch"

        # Same street (different filler words) -> text match.
        same_street = svc._location_evidence(
            c(location_text="Dorchester Ave near the bus stop"),
            c(location_text="Dorchester Avenue, by the bus stop"),
        )
        assert same_street["verdict"] == "match"

        # Different streets -> text mismatch.
        diff_street = svc._location_evidence(
            c(location_text="Dorchester Ave"),
            c(location_text="Beacon St"),
        )
        assert diff_street["verdict"] == "mismatch"

        # Missing on one side -> unknown, NOT mismatch.
        one_missing = svc._location_evidence(
            c(location_text=None),
            c(location_text="South End"),
        )
        assert one_missing["verdict"] == "unknown"


async def test_human_confirmation_no_auto_merge(make_complaint) -> None:
    a = await make_complaint(
        title="Pothole A",
        description="Pothole on Elm Street, deep and dangerous to cyclists here.",
    )
    b = await make_complaint(
        title="Pothole Elm",
        description="Deep dangerous pothole on Elm Street, a hazard to cyclists.",
    )
    await _embed_all([a, b])
    async with async_session_factory() as session:
        links = await DuplicateService(session).find_candidates(a)
        link_id = links[0].id

    async with async_session_factory() as session:
        link = await DuplicateService(session).decide(
            link_id, decision="confirm", reviewer="staff", note="same pothole"
        )
    assert link.decision == DuplicateDecision.CONFIRMED

    # Confirming must NOT merge/close either complaint.
    async with async_session_factory() as session:
        ca = await session.get(Complaint, a)
        cb = await session.get(Complaint, b)
    assert ca.status.value == "submitted"
    assert cb.status.value == "submitted"


async def test_historical_source_rejected(make_complaint) -> None:
    """Duplicate detection must refuse non-live (historical) complaints."""
    cid = await make_complaint()
    async with async_session_factory() as session:
        c = await session.get(Complaint, cid)
        from app.models.enums import ComplaintSource

        c.source = ComplaintSource.IMPORT_311
        await session.commit()

    async with async_session_factory() as session:
        with pytest.raises(NotFoundError):
            await DuplicateService(session).find_candidates(cid)


class _FailingEmbedder:
    name = "failing"
    model = "x"
    dim = 384

    async def embed(self, texts):
        raise EmbeddingError("simulated embedding provider failure")


async def test_embedding_provider_failure_propagates(make_complaint) -> None:
    cid = await make_complaint()
    async with async_session_factory() as session:
        svc = DuplicateService(session, embedder=_FailingEmbedder())
        with pytest.raises(EmbeddingError):
            c = await session.get(Complaint, cid)
            await svc.embed_complaint(c)


async def test_submission_survives_embedding_failure(monkeypatch, make_complaint) -> None:
    """A failing embedder at submit time must not break complaint creation."""
    from app.schemas.complaint import ComplaintCreate
    from app.services import duplicate_service as dup_mod
    from app.services.complaint_service import ComplaintService

    async def boom(self, complaint):
        raise EmbeddingError("boom")

    # Force the embedding step used inside create() to fail.
    monkeypatch.setattr(dup_mod.DuplicateService, "embed_complaint", boom)

    # Resolve Boston-test city id via a fresh complaint through the fixture's city.
    base_cid = await make_complaint()
    async with async_session_factory() as session:
        city_id = (await session.get(Complaint, base_cid)).city_id

    async with async_session_factory() as session:
        svc = ComplaintService(session)
        complaint = await svc.create(
            ComplaintCreate(
                city_id=city_id,
                title="Resilient complaint",
                description="This complaint should persist even if embedding fails.",
            )
        )
        new_id = complaint.id

    # The complaint persists despite the embedding failure.
    async with async_session_factory() as session:
        c = await session.get(Complaint, new_id)
    assert c is not None
    assert c.title == "Resilient complaint"
