"""Shared API dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.services.city_service import CityService
from app.services.complaint_service import ComplaintService


def get_complaint_service(
    session: AsyncSession = Depends(get_session),
) -> ComplaintService:
    return ComplaintService(session)


def get_city_service(
    session: AsyncSession = Depends(get_session),
) -> CityService:
    return CityService(session)


def require_admin(settings: Settings = Depends(get_settings)) -> None:
    """Guard staff/admin mutation and listing endpoints.

    Authentication does not exist yet (a later milestone). Until then these
    endpoints are only served in development. In any non-development environment
    they are disabled by default and return 403, so an unprotected deployment
    cannot expose administrative operations or bulk resident data.
    """
    if not settings.admin_endpoints_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Staff/admin endpoints are disabled in this environment until "
                "authentication is implemented."
            ),
        )
