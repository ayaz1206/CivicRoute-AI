"""Semantic duplicate detection + clarification models (M4).

- ``ComplaintEmbedding`` — pgvector embedding for a LIVE complaint, with model
  and version metadata. Historical 311 data is never embedded here, preserving
  the live/historical separation.
- ``DuplicateLink`` — a possible-duplicate relationship between two live
  complaints, with similarity score and supporting evidence. Links are created
  as candidates and only CONFIRMED by a human; complaints are never auto-merged.
- ``Clarification`` — a targeted question posed to a resident about a complaint,
  plus their answer. Persisted so the workflow can resume safely.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base
from app.models.enums import ClarificationStatus, DuplicateDecision
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint import Complaint

_EMBED_DIM = get_settings().embedding_dim


def _enum(enum_cls, name):
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class ComplaintEmbedding(Base, TimestampMixin):
    __tablename__ = "complaint_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBED_DIM), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)

    complaint: Mapped[Complaint] = relationship(back_populates="embedding")


class DuplicateLink(Base, TimestampMixin):
    __tablename__ = "duplicate_links"
    __table_args__ = (
        # One link per ordered pair; (source, candidate) is unique.
        UniqueConstraint(
            "complaint_id", "candidate_complaint_id", name="uq_duplicate_pair"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The newer complaint whose potential duplicates we searched for.
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # An existing complaint that may be the same issue.
    candidate_complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )

    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    combined_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    decision: Mapped[DuplicateDecision] = mapped_column(
        _enum(DuplicateDecision, "duplicate_decision"),
        nullable=False,
        default=DuplicateDecision.PENDING,
        index=True,
    )
    reviewer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Clarification(Base, TimestampMixin):
    __tablename__ = "clarifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    # What the question is about, e.g. "location", "severity", "timing".
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClarificationStatus] = mapped_column(
        _enum(ClarificationStatus, "clarification_status"),
        nullable=False,
        default=ClarificationStatus.PENDING,
        index=True,
    )
    answered_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    complaint: Mapped[Complaint] = relationship(back_populates="clarifications")
