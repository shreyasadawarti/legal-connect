from httpx import AsyncClient

from app.tests.helpers import auth_headers, register_user


async def test_preferences_defaults(client: AsyncClient):
    user = await register_user(client)
    resp = await client.get("/api/v1/users/me/preferences", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["notifications"]["email_appointments"] is True
    assert body["notifications"]["push_messages"] is True
    assert body["interests"] == []
    assert body["privacy"]["show_profile"] is True


async def test_preferences_patch_merges_and_persists(client: AsyncClient):
    user = await register_user(client)
    resp = await client.patch(
        "/api/v1/users/me/preferences",
        headers=auth_headers(user),
        json={
            "notifications": {"email_messages": False},
            "interests": ["family", "tax"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["notifications"]["email_messages"] is False
    # Untouched defaults survive a partial update.
    assert body["notifications"]["email_appointments"] is True
    assert body["interests"] == ["family", "tax"]

    again = await client.get("/api/v1/users/me/preferences", headers=auth_headers(user))
    assert again.json()["notifications"]["email_messages"] is False


async def test_preferences_rejects_unknown_interest(client: AsyncClient):
    user = await register_user(client)
    resp = await client.patch(
        "/api/v1/users/me/preferences",
        headers=auth_headers(user),
        json={"interests": ["not_a_category"]},
    )
    assert resp.status_code == 422


async def test_delete_account_requires_correct_password(client: AsyncClient):
    user = await register_user(client)
    resp = await client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=auth_headers(user),
        json={"password": "WrongPass123"},
    )
    assert resp.status_code == 400

    # The account is untouched and still usable.
    me = await client.get("/api/v1/users/me", headers=auth_headers(user))
    assert me.status_code == 200


async def test_delete_account_deactivates_and_anonymizes(client: AsyncClient):
    user = await register_user(client, name="Grace", email="grace@example.com")
    resp = await client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=auth_headers(user),
        json={"password": "StrongPass123"},
    )
    assert resp.status_code == 204

    # The session token stops working because the account is no longer active.
    me = await client.get("/api/v1/users/me", headers=auth_headers(user))
    assert me.status_code == 403

    # The original credentials can no longer sign in.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "grace@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 401
