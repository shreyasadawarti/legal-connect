from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from app.db.compat import utcnow
from app.main import app
from app.repositories.user_repository import UserRepository
from app.services import auth_service

REGISTER_PAYLOAD = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "StrongPass123",
    "role": "user",
}


async def register_user(client: AsyncClient, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or dict(REGISTER_PAYLOAD)
    resp = await client.post("/api/v1/auth/register", json=body)
    assert resp.status_code == 201, resp.text
    assert "access_token" not in resp.json()
    return resp.json()


async def _mark_verified(email: str) -> None:
    db = getattr(app.state, "test_db_session", None)
    if db is None:
        pytest.fail("test DB session not available")
    user = await UserRepository(db).find_by_email(email)
    assert user is not None
    await UserRepository(db).mark_email_verified(str(user["_id"]))


async def login_user(client: AsyncClient, email: str, password: str) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def register_and_login(
    client: AsyncClient,
    payload: dict[str, Any] | None = None,
    password: str = "StrongPass123",
) -> dict[str, Any]:
    body = payload or dict(REGISTER_PAYLOAD)
    await register_user(client, body)
    await _mark_verified(body["email"])
    return await login_user(client, body["email"], password)


async def _grant_reset_token(email: str, *, ttl_minutes: int = 30) -> str:
    db = getattr(app.state, "test_db_session", None)
    if db is None:
        pytest.fail("test DB session not available")
    user = await UserRepository(db).find_by_email(email)
    assert user is not None
    token = auth_service.generate_reset_token()
    token_hash = auth_service.hash_reset_token(token)
    expires_at = utcnow() + timedelta(minutes=ttl_minutes)
    await UserRepository(db).set_reset_token(str(user["_id"]), token_hash, expires_at)
    return token


async def auth_headers(data: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    data = await register_user(client)
    assert "message" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["role"] == "user"
    assert data["user"]["is_email_verified"] is False


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: AsyncClient):
    await register_user(client)
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client: AsyncClient):
    payload = dict(REGISTER_PAYLOAD, password="short")
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_admin_role_rejected(client: AsyncClient):
    payload = dict(REGISTER_PAYLOAD, role="admin")
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "admin" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    data = await register_and_login(client)
    assert data["access_token"]
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_unverified_rejected(client: AsyncClient):
    await register_user(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 403
    assert "verif" in resp.json()["detail"].lower()
    # The unverified account still exists and can be verified later.
    await _mark_verified("test@example.com")
    good = await login_user(client, "test@example.com", "StrongPass123")
    assert good["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await register_user(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "WrongPass123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_valid_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.value"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient):
    data = await register_and_login(client)
    resp = await client.get("/api/v1/auth/me", headers=await auth_headers(data))
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    data = await register_and_login(client)
    resp = await client.patch(
        "/api/v1/auth/change-password",
        headers=await auth_headers(data),
        json={"current_password": "StrongPass123", "new_password": "NewStrongPass456"},
    )
    assert resp.status_code == 200

    # Old password no longer works, new one does.
    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"},
    )
    assert bad.status_code == 401
    good = await login_user(client, "test@example.com", "NewStrongPass456")
    assert good["access_token"]

    # The password change invalidated the old access token.
    stale = await client.get("/api/v1/auth/me", headers=await auth_headers(data))
    assert stale.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_identical_for_known_and_unknown(client: AsyncClient):
    unknown = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "missing@example.com"}
    )
    assert unknown.status_code == 200

    await register_user(client)
    known = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "test@example.com"}
    )
    assert known.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]


@pytest.mark.asyncio
async def test_reset_password_flow(client: AsyncClient):
    await register_and_login(client)
    token = await _grant_reset_token("test@example.com")
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "ResetPass123"},
    )
    assert resp.status_code == 200
    login = await login_user(client, "test@example.com", "ResetPass123")
    assert login["access_token"]


@pytest.mark.asyncio
async def test_reset_password_single_use(client: AsyncClient):
    await register_and_login(client)
    token = await _grant_reset_token("test@example.com")
    first = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "ResetPass123"},
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "AnotherPass456"},
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_expired_token_rejected(client: AsyncClient):
    await register_and_login(client)
    token = await _grant_reset_token("test@example.com", ttl_minutes=-5)
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "ResetPass123"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_unknown_token_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": auth_service.generate_reset_token(), "password": "ResetPass123"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_invalidates_sessions(client: AsyncClient):
    data = await register_and_login(client)
    token = await _grant_reset_token("test@example.com")
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "ResetPass123"},
    )
    assert resp.status_code == 200

    stale_me = await client.get("/api/v1/auth/me", headers=await auth_headers(data))
    assert stale_me.status_code == 401
    stale_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert stale_refresh.status_code == 401


@pytest.mark.asyncio
async def test_verify_email_flow(client: AsyncClient):
    await register_user(client)
    token = auth_service.generate_verify_email_token("test@example.com")
    resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    login = await login_user(client, "test@example.com", "StrongPass123")
    me = await client.get("/api/v1/auth/me", headers=await auth_headers(login))
    assert me.json()["is_email_verified"] is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/verify-email", json={"token": "not-a-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_resend_verification_enumeration_safe(client: AsyncClient):
    unknown = await client.post(
        "/api/v1/auth/resend-verification", json={"email": "missing@example.com"}
    )
    assert unknown.status_code == 200

    await register_user(client)
    known = await client.post(
        "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
    )
    assert known.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]

    # Resending does not verify the account.
    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    data = await register_and_login(client)
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-valid"})
    assert resp.status_code == 401