"""Authentication & authorization dependencies (M5).

`get_current_user` validates a Bearer JWT. `require_roles(...)` builds a
dependency enforcing that the caller is an authenticated user with one of the
allowed roles.

Backward-compatible dev access: when no token is presented AND the environment
permits unauthenticated admin (development only; never production — see
Settings.admin_endpoints_enabled), staff/admin endpoints remain open so local
demos and the existing test suite keep working. In production, a valid token is
always required.
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.enums import UserRole
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Return the authenticated user, or None if no/invalid token presented."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = await session.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(*roles: UserRole):
    """Dependency factory enforcing an authenticated user with one of `roles`.

    Falls back to the development admin gate when no token is presented, so
    local demos/tests keep working. Production never allows the fallback.
    """
    allowed = set(roles) or {UserRole.STAFF, UserRole.ADMIN}

    async def _dep(
        request: Request,
        user: User | None = Depends(get_current_user),
        settings: Settings = Depends(get_settings),
    ) -> User | None:
        if user is not None:
            if user.role not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient role for this operation",
                )
            return user
        # No token: allow only when the dev gate permits (never in production).
        if settings.admin_endpoints_enabled:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return _dep


# Convenience dependencies.
def require_staff():
    return require_roles(UserRole.STAFF, UserRole.ADMIN)


def require_admin_role():
    return require_roles(UserRole.ADMIN)
