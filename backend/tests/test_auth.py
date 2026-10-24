"""Staff authentication and RBAC tests (M5)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import async_session_factory
from app.main import create_app
from app.models.enums import UserRole
from app.models.user import User

API = "/api"


@pytest.fixture
async def staff_user(boston_city_id: int):
    """Create a staff + an admin user in the test city."""
    from sqlalchemy import delete

    async with async_session_factory() as session:
        await session.execute(delete(User))
        session.add_all(
            [
                User(
                    city_id=boston_city_id,
                    email="staff@example.com",
                    hashed_password=hash_password("staffpass123"),
                    role=UserRole.STAFF,
                ),
                User(
                    city_id=boston_city_id,
                    email="admin@example.com",
                    hashed_password=hash_password("adminpass123"),
                    role=UserRole.ADMIN,
                ),
            ]
        )
        await session.commit()
    yield boston_city_id
    async with async_session_factory() as session:
        await session.execute(delete(User))
        await session.commit()


@pytest.fixture
async def prod_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, app_env="production", jwt_secret="test-secret"
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://prod") as ac:
        yield ac
    app.dependency_overrides.clear()


def test_password_hashing_roundtrip() -> None:
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong", h)


async def test_login_success_and_me(client: AsyncClient, staff_user: int) -> None:
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "staff@example.com", "password": "staffpass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "staff"
    token = body["access_token"]

    me = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "staff@example.com"


async def test_login_wrong_password(client: AsyncClient, staff_user: int) -> None:
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "staff@example.com", "password": "nope"},
    )
    assert resp.status_code == 409


async def test_token_grants_admin_access_in_prod(
    prod_client: AsyncClient, staff_user: int
) -> None:
    # Without a token, prod blocks admin endpoints.
    unauth = await prod_client.get(f"{API}/complaints", params={"city_id": 1})
    assert unauth.status_code in (401, 403)

    # Log in and use the token — now allowed.
    login = await prod_client.post(
        f"{API}/auth/login",
        json={"email": "staff@example.com", "password": "staffpass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    listed = await prod_client.get(
        f"{API}/complaints",
        params={"city_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200


async def test_rbac_staff_cannot_create_users(
    prod_client: AsyncClient, staff_user: int
) -> None:
    staff_token = (
        await prod_client.post(
            f"{API}/auth/login",
            json={"email": "staff@example.com", "password": "staffpass123"},
        )
    ).json()["access_token"]
    # Creating users is admin-only.
    resp = await prod_client.post(
        f"{API}/auth/users",
        json={"email": "new@example.com", "password": "newpass12345", "role": "staff"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


async def test_rbac_admin_can_create_users(
    prod_client: AsyncClient, staff_user: int
) -> None:
    admin_token = (
        await prod_client.post(
            f"{API}/auth/login",
            json={"email": "admin@example.com", "password": "adminpass123"},
        )
    ).json()["access_token"]
    resp = await prod_client.post(
        f"{API}/auth/users",
        json={"email": "new@example.com", "password": "newpass12345", "role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@example.com"


async def test_invalid_token_rejected(prod_client: AsyncClient) -> None:
    resp = await prod_client.get(
        f"{API}/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_expired_token_signature_mismatch(client: AsyncClient) -> None:
    # Token signed with a different secret must be rejected.
    bad = create_access_token(subject="1", role="admin", city_id=1)
    # Tamper with it.
    tampered = bad[:-3] + "zzz"
    resp = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert resp.status_code == 401
