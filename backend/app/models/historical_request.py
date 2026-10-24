"""Historical Boston 311 request model.

This is a DEDICATED table for historical/reference 311 data, physically
separate from the live ``complaints`` table. It exists so historical records
can never be read or mutated through the live complaint APIs — those APIs only
ever touch ``complaints``. This table is append/refresh-only via the idempotent
ingestion job (M2); no runtime API mutates it.

Fields mirror the Boston 311 Open Data schema, keeping only what the analytics
and (later) duplicate-detection features need.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.city import City


class Historical311Request(Base, TimestampMixin):
    __tablename__ = "historical_311_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Tenant scoping (Boston for now), consistent with the rest of the schema.
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Boston 311 natural key. Unique so ingestion is idempotent (upsert on this).
    case_enquiry_id: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, index=True
    )

    # Core descriptive fields from 311.
    case_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    case_type: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    queue: Mapped[str | None] = mapped_column(String(160), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    # Status: Boston uses "Open"/"Closed"; store raw plus a normalized flag.
    case_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location.
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    location_street: Mapped[str | None] = mapped_column(String(300), nullable=True)
    zipcode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps from the source dataset (distinct from row created/updated).
    opened_at: Mapped[dt.datetime | None] = mapped_column(nullable=True, index=True)
    closed_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    source: Mapped[str] = mapped_column(String(40), nullable=False, default="boston_311")

    city: Mapped[City] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Historical311Request case={self.case_enquiry_id!r} status={self.case_status!r}>"
