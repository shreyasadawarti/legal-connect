from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models.user import UserRole, UserStatus

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
    return resp.json()


async def login_user(client: AsyncClient, email: str, password: str) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def auth_headers(data: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    data = await register_user(client)
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["role"] == "user"


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
    await register_user(client)
    data = await login_user(client, "test@example.com", "StrongPass123")
    assert data["access_token"]
    assert data["user"]["email"] == "test@example.com"


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
    data = await register_user(client)
    resp = await client.get("/api/v1/auth/me", headers=await auth_headers(data))
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    data = await register_user(client)
    resp = await client.patch(
        "/api/v1/auth/change-password",
        headers=await auth_headers(data),
        json={"current_password": "StrongPass123", "new_password": "NewStrongPass456"},
    )
    assert resp.status_code == 200

    # Old password no longer works, new one does
    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"},
    )
    assert bad.status_code == 401
    good = await login_user(client, "test@example.com", "NewStrongPass456")
    assert good["access_token"]


@pytest.mark.asyncio
async def test_forgot_password_no_user_enumeration(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "missing@example.com"}
    )
    assert resp.status_code == 200
    assert "sent" in resp.json()["message"]


@pytest.mark.asyncio
async def test_reset_password_flow(client: AsyncClient):
    await register_user(client)
    from app.services.auth_service import generate_reset_token

    token = generate_reset_token("test@example.com")
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "ResetPass123"},
    )
    assert resp.status_code == 200
    login = await login_user(client, "test@example.com", "ResetPass123")
    assert login["access_token"]


@pytest.mark.asyncio
async def test_verify_email_flow(client: AsyncClient):
    data = await register_user(client)
    assert data["user"]["is_email_verified"] is False
    from app.services.auth_service import generate_verify_email_token

    token = generate_verify_email_token("test@example.com")
    resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    me = await client.get("/api/v1/auth/me", headers=await auth_headers(data))
    assert me.json()["is_email_verified"] is True


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    data = await register_user(client)
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-valid"})
    assert resp.status_code == 401
