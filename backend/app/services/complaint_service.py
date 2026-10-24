"""Complaint domain service.

Encapsulates business rules so the API layer stays thin:
- tracking-code generation
- live-only creation (source is always WEB here; historical 311 never enters
  through this path)
- status-transition validation and append-only history writes
- operational queries scoped to a city and to live complaints
"""

from __future__ import annotations

import datetime as dt
import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.city import City
from app.models.complaint import Complaint
from app.models.enums import ComplaintSource, ComplaintStatus
from app.models.status_history import StatusHistory
from app.schemas.complaint import (
    ComplaintAssignUpdate,
    ComplaintCreate,
    ComplaintStatusUpdate,
)
from app.services.errors import NotFoundError, ValidationError

# Allowed status transitions (M1, manual/staff-driven). Terminal states have no
# outgoing transitions. Agent-driven transitions are added in a later milestone.
_ALLOWED_TRANSITIONS: dict[ComplaintStatus, set[ComplaintStatus]] = {
    ComplaintStatus.SUBMITTED: {
        ComplaintStatus.TRIAGED,
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.TRIAGED: {
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.IN_PROGRESS: {
        ComplaintStatus.RESOLVED,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.RESOLVED: {ComplaintStatus.CLOSED, ComplaintStatus.IN_PROGRESS},
    ComplaintStatus.CLOSED: set(),
    ComplaintStatus.REJECTED: set(),
}


def _generate_tracking_code() -> str:
    """Generate a human-friendly, unguessable tracking code: CR-XXXXXXXX."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no ambiguous chars
    body = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"CR-{body}"


class ComplaintService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _require_city(self, city_id: int) -> City:
        city = await self.session.get(City, city_id)
        if city is None:
            raise NotFoundError(f"City {city_id} not found")
        return city

    async def create(self, data: ComplaintCreate) -> Complaint:
        """Create a live (web) complaint and seed its status history."""
        await self._require_city(data.city_id)

        # Ensure a unique tracking code (retry on the rare collision).
        for _ in range(5):
            code = _generate_tracking_code()
            exists = await self.session.scalar(
                select(Complaint.id).where(Complaint.tracking_code == code)
            )
            if exists is None:
                break
        else:  # pragma: no cover - astronomically unlikely
            raise ValidationError("Could not allocate a unique tracking code")

        complaint = Complaint(
            tracking_code=code,
            city_id=data.city_id,
            source=ComplaintSource.WEB,  # live only; never 311_import here
            status=ComplaintStatus.SUBMITTED,
            title=data.title,
            description=data.description,
            reporter_name=data.reporter_name,
            reporter_email=data.reporter_email,
            location_text=data.location_text,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        complaint.status_history.append(
            StatusHistory(
                from_status=None,
                to_status=ComplaintStatus.SUBMITTED,
                actor="resident",
                note="Complaint submitted",
            )
        )
        self.session.add(complaint)
        await self.session.commit()
        await self.session.refresh(complaint)
        return complaint

    async def get(self, complaint_id: int, *, with_history: bool = False) -> Complaint:
        stmt = select(Complaint).where(Complaint.id == complaint_id)
        if with_history:
            stmt = stmt.options(selectinload(Complaint.status_history))
        complaint = await self.session.scalar(stmt)
        if complaint is None:
            raise NotFoundError(f"Complaint {complaint_id} not found")
        return complaint

    async def get_by_tracking_code(self, code: str) -> Complaint:
        stmt = (
            select(Complaint)
            .where(Complaint.tracking_code == code.strip().upper())
            .options(selectinload(Complaint.status_history))
        )
        complaint = await self.session.scalar(stmt)
        if complaint is None:
            raise NotFoundError("No complaint found for that tracking code")
        return complaint

    async def list(
        self,
        *,
        city_id: int | None = None,
        status: ComplaintStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Complaint], int]:
        """List LIVE complaints only. Historical 311 imports are excluded so the
        operational dashboard never mixes reference data with live work."""
        base = select(Complaint).where(Complaint.source == ComplaintSource.WEB)
        if city_id is not None:
            base = base.where(Complaint.city_id == city_id)
        if status is not None:
            base = base.where(Complaint.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = await self.session.scalars(
            base.order_by(Complaint.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows), int(total or 0)

    async def update_status(
        self, complaint_id: int, data: ComplaintStatusUpdate
    ) -> Complaint:
        complaint = await self.get(complaint_id, with_history=True)

        if complaint.source != ComplaintSource.WEB:
            # Guard: historical records are read-only reference data.
            raise ValidationError("Historical complaints cannot be modified")

        current = complaint.status
        target = data.status
        if target == current:
            raise ValidationError(f"Complaint is already '{current.value}'")
        if target not in _ALLOWED_TRANSITIONS[current]:
            allowed = sorted(s.value for s in _ALLOWED_TRANSITIONS[current])
            raise ValidationError(
                f"Illegal transition {current.value} -> {target.value}. "
                f"Allowed: {allowed or 'none (terminal state)'}"
            )

        complaint.status = target
        if target == ComplaintStatus.RESOLVED:
            complaint.resolved_at = dt.datetime.now(dt.UTC)
        complaint.status_history.append(
            StatusHistory(
                from_status=current,
                to_status=target,
                actor=data.actor,
                note=data.note,
            )
        )
        await self.session.commit()
        # Re-load with history eagerly populated for the response schema.
        return await self.get(complaint_id, with_history=True)

    async def update_assignment(
        self, complaint_id: int, data: ComplaintAssignUpdate
    ) -> Complaint:
        """Manually set category/priority/department (pre-agent staff action)."""
        complaint = await self.get(complaint_id)
        if complaint.source != ComplaintSource.WEB:
            raise ValidationError("Historical complaints cannot be modified")

        if data.category is not None:
            complaint.category = data.category
        if data.priority is not None:
            complaint.priority = data.priority
        if data.department_id is not None:
            complaint.department_id = data.department_id
        await self.session.commit()
        # Re-load with history eagerly populated for the response schema.
        return await self.get(complaint_id, with_history=True)
