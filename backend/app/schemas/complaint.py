"""Complaint API schemas."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ComplaintPriority, ComplaintSource, ComplaintStatus


class ComplaintCreate(BaseModel):
    """Payload for a resident submitting a new complaint.

    Note: `source` is intentionally NOT accepted from the client. All
    submissions through this path are live (`web`); historical 311 data is
    never created here.
    """

    city_id: int
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    reporter_name: str | None = Field(default=None, max_length=120)
    reporter_email: EmailStr | None = None
    location_text: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class ComplaintStatusUpdate(BaseModel):
    """Staff action to change a complaint's status."""

    status: ComplaintStatus
    actor: str = Field(default="staff", max_length=80)
    note: str | None = None


class ComplaintAssignUpdate(BaseModel):
    """Staff action to set classification/routing fields manually (pre-agent)."""

    category: str | None = Field(default=None, max_length=120)
    priority: ComplaintPriority | None = None
    department_id: int | None = None
    actor: str = Field(default="staff", max_length=80)


class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: ComplaintStatus | None
    to_status: ComplaintStatus
    actor: str
    note: str | None
    created_at: dt.datetime


class ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_code: str
    city_id: int
    source: ComplaintSource
    status: ComplaintStatus
    title: str
    description: str
    reporter_name: str | None
    reporter_email: str | None
    location_text: str | None
    latitude: float | None
    longitude: float | None
    category: str | None
    priority: ComplaintPriority | None
    department_id: int | None
    resolved_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


class ComplaintDetail(ComplaintRead):
    """Full complaint with its status timeline (used by staff detail views)."""

    status_history: list[StatusHistoryRead] = []


class ComplaintPublic(BaseModel):
    """Public, PII-free view for the resident tracking page.

    Deliberately omits reporter name/email and other sensitive fields so the
    public tracking endpoint cannot be used to harvest resident information.
    """

    model_config = ConfigDict(from_attributes=True)

    tracking_code: str
    status: ComplaintStatus
    title: str
    description: str
    location_text: str | None
    category: str | None
    priority: ComplaintPriority | None
    created_at: dt.datetime
    updated_at: dt.datetime
    resolved_at: dt.datetime | None
    status_history: list[StatusHistoryRead] = []


class ComplaintCreated(BaseModel):
    """Returned on submission — surfaces the tracking code to the resident."""

    id: int
    tracking_code: str
    status: ComplaintStatus
