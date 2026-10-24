"""Shared API dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.services.agent_service import AgentService
from app.services.city_service import CityService
from app.services.clarification_service import ClarificationService
from app.services.complaint_service import ComplaintService
from app.services.duplicate_service import DuplicateService
from app.services.review_service import ReviewService


def get_complaint_service(
    session: AsyncSession = Depends(get_session),
) -> ComplaintService:
    return ComplaintService(session)


def get_city_service(
    session: AsyncSession = Depends(get_session),
) -> CityService:
    return CityService(session)


def get_agent_service(
    session: AsyncSession = Depends(get_session),
) -> AgentService:
    return AgentService(session)


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(session)


def get_duplicate_service(
    session: AsyncSession = Depends(get_session),
) -> DuplicateService:
    return DuplicateService(session)


def get_clarification_service(
    session: AsyncSession = Depends(get_session),
) -> ClarificationService:
    return ClarificationService(session)


def require_admin(
    request: Request,
    user=Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> None:
    """Guard staff/admin mutation and listing endpoints (M5).

    Accepts a valid staff/admin JWT. When no token is presented, falls back to
    the development-only gate (``admin_endpoints_enabled``) so local demos and
    the existing test suite keep working. In production, a valid token is always
    required — the fallback is never permitted there.
    """
    if user is not None:
        # Any authenticated staff/admin user may access these endpoints.
        return None
    if settings.admin_endpoints_enabled:
        return None
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication required. Staff/admin endpoints are disabled for "
            "unauthenticated access in this environment."
        ),
    )
