"""StatusHistory model — append-only timeline of complaint status changes.

Every status transition writes a row here. This powers the resident-facing
tracking timeline and, later, auditing. Rows are never updated or deleted
(except via cascade when a complaint is removed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ComplaintStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint import Complaint


class StatusHistory(Base, TimestampMixin):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Null `from_status` marks the initial creation event.
    from_status: Mapped[ComplaintStatus | None] = mapped_column(
        SAEnum(ComplaintStatus, name="complaint_status", create_type=False,
               values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    to_status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, name="complaint_status", create_type=False,
               values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    # Who/what made the change. In M1 this is a free-text actor label (e.g.
    # "resident", "staff"); becomes a user reference once auth lands.
    actor: Mapped[str] = mapped_column(String(80), nullable=False, default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    complaint: Mapped[Complaint] = relationship(back_populates="status_history")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<StatusHistory complaint_id={self.complaint_id} "
            f"{self.from_status}->{self.to_status}>"
        )
