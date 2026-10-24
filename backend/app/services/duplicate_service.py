"""Semantic duplicate detection over LIVE complaints.

Pipeline:
1. Embed the complaint text with the configured provider and store the vector
   with model/version metadata.
2. KNN search (pgvector cosine) over OTHER live complaints in the same city.
3. Blend semantic similarity with category compatibility, location evidence,
   and status into a combined score; keep candidates above threshold.
4. Persist ranked candidate links (PENDING). Never auto-merge.

Privacy: candidate results never include reporter name/email.
Location: evidence uses only provided coordinates/text; no addresses are
invented. Candidates with no location data are reported as "no location
evidence", not fabricated.
"""

from __future__ import annotations

import math
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.models.complaint import Complaint
from app.models.duplicate import ComplaintEmbedding, DuplicateLink
from app.models.enums import ComplaintSource, ComplaintStatus, DuplicateDecision
from app.services.errors import NotFoundError

_OPEN_STATUSES = {
    ComplaintStatus.SUBMITTED,
    ComplaintStatus.TRIAGED,
    ComplaintStatus.IN_PROGRESS,
}

# Filler tokens ignored when comparing location text so that
# "Dorchester Ave near the bus stop" and "Dorchester Avenue" still align on the
# meaningful street token. Street-type synonyms are normalized separately.
_LOC_STOPWORDS = {
    "the", "near", "at", "by", "on", "corner", "of", "and", "a", "to",
    "street", "st", "ave", "avenue", "rd", "road", "blvd", "boulevard",
    "sq", "square", "ln", "lane", "dr", "drive", "ct", "court", "pl", "place",
    "bus", "stop", "between", "front", "side",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def _haversine_m(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _normalize_location_tokens(text: str) -> set[str]:
    """Lowercase, strip punctuation/street-type/filler words -> content tokens
    (typically the distinctive street/place names)."""
    toks = _WORD_RE.findall(text.lower())
    return {t for t in toks if t not in _LOC_STOPWORDS}


def _complaint_text(c: Complaint) -> str:
    """Text used for the SEMANTIC embedding — the issue itself (title +
    description) only. Location is deliberately excluded here and handled
    separately as structured location evidence, so a shared street name does
    not inflate semantic similarity (which would double-count location once in
    the vector and again in the location boost)."""
    parts = [c.title, c.description]
    return "\n".join(p for p in parts if p)


class DuplicateService:
    def __init__(
        self, session: AsyncSession, embedder: EmbeddingProvider | None = None
    ) -> None:
        self.session = session
        self.embedder = embedder or get_embedding_provider()
        self.settings = get_settings()

    async def embed_complaint(self, complaint: Complaint) -> ComplaintEmbedding:
        """Create or replace the embedding for a complaint."""
        [vec] = await self.embedder.embed([_complaint_text(complaint)])
        existing = await self.session.scalar(
            select(ComplaintEmbedding).where(
                ComplaintEmbedding.complaint_id == complaint.id
            )
        )
        if existing is None:
            existing = ComplaintEmbedding(complaint_id=complaint.id)
            self.session.add(existing)
        existing.embedding = vec
        existing.provider = self.embedder.name
        existing.model = self.embedder.model
        existing.model_version = getattr(self.embedder, "model_version", None)
        existing.dim = self.embedder.dim
        return existing

    def _location_evidence(self, src: Complaint, cand: Complaint) -> dict:
        """Compare two complaints' locations and return evidence with a verdict.

        verdict is one of:
          - "match"     : confidently the same place (boost)
          - "mismatch"  : confidently different places (penalize)
          - "ambiguous" : some signal but not decisive (neutral)
          - "unknown"   : no usable location data on one/both (neutral)

        Only provided coordinates/text are used; no location is invented, and
        missing data is treated as unknown, never as a mismatch.
        """
        s = self.settings
        dist = _haversine_m(src.latitude, src.longitude, cand.latitude, cand.longitude)
        if dist is not None:
            if dist <= s.duplicate_location_radius_m:
                verdict = "match"
            elif dist >= s.duplicate_location_mismatch_m:
                verdict = "mismatch"
            else:
                verdict = "ambiguous"
            return {
                "type": "coordinates",
                "distance_m": round(dist, 1),
                "verdict": verdict,
            }

        # No coordinates on one/both — compare normalized location text if BOTH
        # have it. If either is missing, location is unknown (not a mismatch).
        if src.location_text and cand.location_text:
            a = _normalize_location_tokens(src.location_text)
            b = _normalize_location_tokens(cand.location_text)
            if not a or not b:
                # Location text was all filler/street-types -> not decisive.
                return {"type": "text", "jaccard": None, "verdict": "unknown"}
            jaccard = round(len(a & b) / len(a | b), 2)
            if jaccard >= s.duplicate_location_text_match:
                verdict = "match"
            elif jaccard <= s.duplicate_location_text_mismatch:
                verdict = "mismatch"
            else:
                verdict = "ambiguous"
            return {
                "type": "text",
                "jaccard": jaccard,
                "shared": sorted(a & b),
                "verdict": verdict,
            }

        return {"type": "none", "verdict": "unknown",
                "note": "no location evidence available"}

    @staticmethod
    def _category_compatible(src: Complaint, cand: Complaint) -> bool | None:
        if src.category is None or cand.category is None:
            return None  # unknown — neither boosts nor penalizes
        return src.category == cand.category

    def _combined_score(
        self, similarity: float, category_compat: bool | None, loc: dict, cand: Complaint
    ) -> float:
        """Blend semantic similarity with category, location, and status.

        Location is the key disambiguator between "same issue here" and "same
        kind of issue elsewhere": a confident location match boosts, a confident
        mismatch penalizes, and unknown/ambiguous locations are neutral.
        """
        score = similarity
        if category_compat is True:
            score += 0.1
        elif category_compat is False:
            score -= 0.15

        verdict = loc.get("verdict", "unknown")
        if verdict == "match":
            # Location corroborates — but only boost when the text is ALREADY
            # near the decision threshold, so a shared street cannot carry a
            # clearly sub-threshold (semantically different) pair over the line.
            if similarity >= self.settings.duplicate_similarity_threshold - 0.03:
                score += 0.08
        elif verdict == "mismatch":
            score -= 0.35  # clearly different place -> distinct incident
        # "ambiguous" and "unknown" -> no location adjustment (neutral)

        # NOTE: candidate status (open vs closed) is intentionally NOT part of
        # the gate score — a weak signal must not push a sub-threshold pair over
        # the line. Ranking is by combined score; ties are acceptable.
        return max(0.0, min(1.0, round(score, 4)))

    async def find_candidates(
        self, complaint_id: int, *, top_k: int = 5
    ) -> list[DuplicateLink]:
        """Embed the complaint, search for duplicates, persist ranked links."""
        complaint = await self.session.get(Complaint, complaint_id)
        if complaint is None:
            raise NotFoundError(f"Complaint {complaint_id} not found")
        if complaint.source != ComplaintSource.WEB:
            # Historical records are never part of live duplicate detection.
            raise NotFoundError("Only live complaints support duplicate detection")

        emb = await self.embed_complaint(complaint)
        await self.session.flush()

        # KNN over OTHER live complaints in the same city that have embeddings.
        threshold = self.settings.duplicate_similarity_threshold
        retrieval_floor = self.settings.duplicate_retrieval_floor
        distance = ComplaintEmbedding.embedding.cosine_distance(emb.embedding)
        rows = await self.session.execute(
            select(Complaint, distance.label("dist"))
            .join(ComplaintEmbedding, ComplaintEmbedding.complaint_id == Complaint.id)
            .where(
                Complaint.city_id == complaint.city_id,
                Complaint.source == ComplaintSource.WEB,
                Complaint.id != complaint.id,
            )
            .order_by(distance)
            .limit(top_k)
        )

        links: list[DuplicateLink] = []
        for cand, dist in rows.all():
            similarity = 1.0 - float(dist)  # cosine distance -> similarity
            # Retrieval floor keeps obvious noise out but still admits
            # borderline cases so location/category evidence can decide them.
            if similarity < retrieval_floor:
                continue
            category_compat = self._category_compatible(complaint, cand)
            loc = self._location_evidence(complaint, cand)
            combined = self._combined_score(similarity, category_compat, loc, cand)
            # DECISION uses the location-aware combined score, not raw cosine.
            if combined < threshold:
                continue

            link = await self.session.scalar(
                select(DuplicateLink).where(
                    DuplicateLink.complaint_id == complaint.id,
                    DuplicateLink.candidate_complaint_id == cand.id,
                )
            )
            evidence = {
                "similarity": round(similarity, 4),
                "category": {
                    "source": complaint.category,
                    "candidate": cand.category,
                    "compatible": category_compat,
                },
                "location": loc,
                "candidate_status": cand.status.value,
            }
            if link is None:
                link = DuplicateLink(
                    complaint_id=complaint.id,
                    candidate_complaint_id=cand.id,
                    decision=DuplicateDecision.PENDING,
                )
                self.session.add(link)
            # Refresh scores/evidence only while still pending (don't overwrite
            # a human decision).
            if link.decision == DuplicateDecision.PENDING:
                link.similarity = round(similarity, 4)
                link.combined_score = combined
                link.evidence = evidence
            links.append(link)

        await self.session.commit()
        links.sort(key=lambda link_obj: link_obj.combined_score, reverse=True)
        return links

    async def decide(
        self,
        link_id: int,
        *,
        decision: str,
        reviewer: str,
        note: str | None = None,
    ) -> DuplicateLink:
        import datetime as dt

        link = await self.session.get(DuplicateLink, link_id)
        if link is None:
            raise NotFoundError(f"Duplicate link {link_id} not found")
        if decision not in ("confirm", "reject"):
            from app.services.errors import ValidationError

            raise ValidationError("decision must be 'confirm' or 'reject'")
        link.decision = (
            DuplicateDecision.CONFIRMED
            if decision == "confirm"
            else DuplicateDecision.REJECTED
        )
        link.reviewer = reviewer
        link.reviewed_at = dt.datetime.now(dt.UTC)
        link.review_note = note
        # NOTE: confirming a duplicate records the relationship for staff; it
        # does NOT merge or close either complaint automatically.
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def list_candidates(self, complaint_id: int) -> list[DuplicateLink]:
        rows = await self.session.scalars(
            select(DuplicateLink)
            .where(DuplicateLink.complaint_id == complaint_id)
            .order_by(DuplicateLink.combined_score.desc())
        )
        return list(rows)
