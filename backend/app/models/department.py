"""Department model — routing targets, scoped to a city."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.city import City
    from app.models.complaint import Complaint


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("city_id", "slug", name="uq_departments_city_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)

    # Category tags this department handles. Used by the routing agent later;
    # in M1 it documents intended ownership and powers manual assignment.
    category_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    city: Mapped[City] = relationship(back_populates="departments")
    complaints: Mapped[list[Complaint]] = relationship(back_populates="department")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Department id={self.id} city_id={self.city_id} slug={self.slug!r}>"
