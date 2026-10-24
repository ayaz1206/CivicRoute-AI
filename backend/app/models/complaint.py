"""Complaint model — the central domain entity.

Live resident complaints and historical 311 imports share this table but are
discriminated by ``source``. The live submission path only ever writes
``source = web``; a check constraint and the service layer guard against the
historical source leaking into the live workflow. Operational/list queries
filter to live complaints by default.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ComplaintPriority, ComplaintSource, ComplaintStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agent import AgentRecommendation, AgentRun
    from app.models.city import City
    from app.models.department import Department
    from app.models.duplicate import Clarification, ComplaintEmbedding
    from app.models.status_history import StatusHistory


class Complaint(Base, TimestampMixin):
    __tablename__ = "complaints"
    __table_args__ = (
        # Fast operational lookups: live complaints for a city by status.
        Index("ix_complaints_city_status", "city_id", "status"),
        Index("ix_complaints_city_source", "city_id", "source"),
        # Defense in depth: the enum already constrains values; this documents
        # that source must be one of the known values at the DB level.
        CheckConstraint(
            "source in ('web', '311_import')",
            name="ck_complaints_source_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Public, user-facing reference code for tracking (e.g. CR-AB12CD34).
    tracking_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    source: Mapped[ComplaintSource] = mapped_column(
        SAEnum(
            ComplaintSource,
            name="complaint_source",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ComplaintSource.WEB,
    )
    status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(
            ComplaintStatus,
            name="complaint_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ComplaintStatus.SUBMITTED,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Reporter contact (optional; no auth in M1).
    reporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Location: free-text plus optional coordinates.
    location_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Classification / routing — nullable in M1. Staff may set manually now;
    # the classification and routing agents populate these in a later milestone.
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    priority: Mapped[ComplaintPriority | None] = mapped_column(
        SAEnum(
            ComplaintPriority,
            name="complaint_priority",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )

    resolved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    city: Mapped[City] = relationship(back_populates="complaints")
    department: Mapped[Department | None] = relationship(back_populates="complaints")
    status_history: Mapped[list[StatusHistory]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="StatusHistory.created_at",
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="AgentRun.id",
    )
    recommendations: Mapped[list[AgentRecommendation]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="AgentRecommendation.id",
    )
    embedding: Mapped[ComplaintEmbedding | None] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        uselist=False,
    )
    clarifications: Mapped[list[Clarification]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="Clarification.id",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Complaint id={self.id} code={self.tracking_code!r} status={self.status}>"
