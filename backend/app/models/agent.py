"""Agent decision models (M3).

These tables hold AI-generated decisions and are kept strictly SEPARATE from
final complaint data. The agent never writes classification/priority/department
onto the ``complaints`` row directly — it writes an ``AgentRecommendation``.
Only after a human approves or overrides it does the (possibly edited) value
get applied to the complaint by the review service.

- ``AgentRun``    — one pass of a complaint through the LangGraph workflow.
- ``AgentStep``   — per-node audit record (input/output/confidence/latency).
- ``AgentRecommendation`` — the consolidated proposal for a complaint, with its
  review state and the final human-approved values.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    AgentRunStatus,
    ComplaintPriority,
    RecommendationStatus,
    ReviewSeverity,
)
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint import Complaint


def _enum(enum_cls, name):
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    graph_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")
    status: Mapped[AgentRunStatus] = mapped_column(
        _enum(AgentRunStatus, "agent_run_status"),
        nullable=False,
        default=AgentRunStatus.RUNNING,
    )
    llm_provider: Mapped[str] = mapped_column(String(40), nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    complaint: Mapped[Complaint] = relationship(back_populates="agent_runs")
    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.id",
    )
    recommendation: Mapped[AgentRecommendation | None] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AgentStep(Base, TimestampMixin):
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_name: Mapped[str] = mapped_column(String(60), nullable=False)
    # Structured input/output for full auditability of each node.
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped[AgentRun] = relationship(back_populates="steps")


class AgentRecommendation(Base, TimestampMixin):
    __tablename__ = "agent_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # --- AI proposal (never applied to the complaint until approved) ---
    extracted: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[ComplaintPriority | None] = mapped_column(
        _enum(ComplaintPriority, "complaint_priority"), nullable=True
    )
    priority_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    department_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    routing_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Review state ---
    status: Mapped[RecommendationStatus] = mapped_column(
        _enum(RecommendationStatus, "recommendation_status"),
        nullable=False,
        default=RecommendationStatus.PENDING,
        index=True,
    )
    requires_review: Mapped[bool] = mapped_column(nullable=False, default=True)
    review_severity: Mapped[ReviewSeverity] = mapped_column(
        _enum(ReviewSeverity, "review_severity"),
        nullable=False,
        default=ReviewSeverity.ROUTINE,
        index=True,
    )
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Final human-approved values (what actually gets applied) ---
    reviewer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    final_priority: Mapped[ComplaintPriority | None] = mapped_column(
        _enum(ComplaintPriority, "complaint_priority"), nullable=True
    )
    final_department_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[AgentRun] = relationship(back_populates="recommendation")
    complaint: Mapped[Complaint] = relationship(back_populates="recommendations")
