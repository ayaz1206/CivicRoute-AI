"""Authentication endpoints (M5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_user, require_admin_role
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Staff login")
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    service = AuthService(session)
    user, token = await service.authenticate(payload.email, payload.password)
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserRead, summary="Current user")
async def me(user: User | None = Depends(get_current_user)) -> UserRead:
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserRead.model_validate(user)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=201,
    summary="Create a staff user (admin only)",
    dependencies=[Depends(require_admin_role())],
)
async def create_user(
    payload: UserCreate,
    current: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    service = AuthService(session)
    # New users are created in the admin's city (or city 1 under the dev gate).
    city_id = current.city_id if current is not None else 1
    user = await service.create_user(
        city_id=city_id,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        full_name=payload.full_name,
    )
    return UserRead.model_validate(user)
