"""Staff authentication service (M5)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.services.errors import NotFoundError, ValidationError


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(
        self,
        *,
        city_id: int,
        email: str,
        password: str,
        role: UserRole = UserRole.STAFF,
        full_name: str | None = None,
    ) -> User:
        email = email.strip().lower()
        existing = await self.session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise ValidationError("A user with that email already exists")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        user = User(
            city_id=city_id,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> tuple[User, str]:
        email = email.strip().lower()
        user = await self.session.scalar(select(User).where(User.email == email))
        # Constant-ish time: always run verify even if user missing.
        if user is None or not user.is_active:
            # Run a dummy verify to reduce timing signal, then fail.
            verify_password(password, "$2b$12$" + "x" * 53)
            raise ValidationError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise ValidationError("Invalid email or password")
        token = create_access_token(
            subject=str(user.id), role=user.role.value, city_id=user.city_id
        )
        return user, token

    async def get(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user
