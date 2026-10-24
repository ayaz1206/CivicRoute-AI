"""City model — the multi-tenant root. Boston is the first city."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint import Complaint
    from app.models.department import Department


class City(Base, TimestampMixin):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    # Per-city configuration (categories, SLA thresholds). Free-form in M1.
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    departments: Mapped[list[Department]] = relationship(
        back_populates="city",
        cascade="all, delete-orphan",
    )
    complaints: Mapped[list[Complaint]] = relationship(back_populates="city")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<City id={self.id} slug={self.slug!r}>"
