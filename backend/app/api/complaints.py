"""Complaint endpoints: submission, tracking, listing, and staff actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_complaint_service, require_admin
from app.models.enums import ComplaintStatus
from app.schemas.common import Page
from app.schemas.complaint import (
    ComplaintAssignUpdate,
    ComplaintCreate,
    ComplaintCreated,
    ComplaintDetail,
    ComplaintPublic,
    ComplaintRead,
    ComplaintStatusUpdate,
)
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post(
    "",
    response_model=ComplaintCreated,
    status_code=201,
    summary="Submit a complaint (resident)",
)
async def create_complaint(
    payload: ComplaintCreate,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintCreated:
    complaint = await service.create(payload)
    return ComplaintCreated.model_validate(complaint, from_attributes=True)


@router.get(
    "",
    response_model=Page[ComplaintRead],
    summary="List live complaints (staff dashboard)",
    dependencies=[Depends(require_admin)],
)
async def list_complaints(
    city_id: int | None = Query(default=None),
    status: ComplaintStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ComplaintService = Depends(get_complaint_service),
) -> Page[ComplaintRead]:
    items, total = await service.list(
        city_id=city_id, status=status, limit=limit, offset=offset
    )
    return Page[ComplaintRead](
        items=[ComplaintRead.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/track/{tracking_code}",
    response_model=ComplaintPublic,
    summary="Track a complaint by its public code (resident, read-only)",
)
async def track_complaint(
    tracking_code: str,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintPublic:
    complaint = await service.get_by_tracking_code(tracking_code)
    # PII-free projection: reporter name/email are never returned here.
    return ComplaintPublic.model_validate(complaint)


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetail,
    summary="Get a complaint with its status timeline (staff)",
    dependencies=[Depends(require_admin)],
)
async def get_complaint(
    complaint_id: int,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintDetail:
    complaint = await service.get(complaint_id, with_history=True)
    return ComplaintDetail.model_validate(complaint)


@router.post(
    "/{complaint_id}/status",
    response_model=ComplaintDetail,
    summary="Change a complaint's status (staff)",
    dependencies=[Depends(require_admin)],
)
async def update_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintDetail:
    complaint = await service.update_status(complaint_id, payload)
    return ComplaintDetail.model_validate(complaint)


@router.patch(
    "/{complaint_id}/assignment",
    response_model=ComplaintDetail,
    summary="Set category/priority/department manually (staff)",
    dependencies=[Depends(require_admin)],
)
async def update_assignment(
    complaint_id: int,
    payload: ComplaintAssignUpdate,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintDetail:
    complaint = await service.update_assignment(complaint_id, payload)
    return ComplaintDetail.model_validate(complaint, from_attributes=True)
