"""Auth API schemas (M5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str | None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole = UserRole.STAFF


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
