from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register,
    register_admin,
    register_lawyer,
    register_user,
)


async def _setup_lawyer(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(fake_db, lawyer["user"]["id"])
    return lawyer


def _slot():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    return start.isoformat(), (start + timedelta(minutes=60)).isoformat()


async def _complete_appointment(client: AsyncClient, fake_db, lawyer, user):
    s, e = _slot()
    appt = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": s, "end_time": e},
    )
    return appt.json()["id"]


async def test_update_own_profile(client: AsyncClient):
    user = await register_user(client)
    resp = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers(user),
        json={"name": "Updated Name", "preferred_language": "hi"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["preferred_language"] == "hi"


async def test_get_own_profile(client: AsyncClient):
    user = await register_user(client)
    resp = await client.get("/api/v1/users/me", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


async def test_profile_update_requires_auth(client: AsyncClient):
    resp = await client.patch("/api/v1/users/me", json={"name": "x"})
    assert resp.status_code in (401, 403)


async def test_booking_creates_notification_for_lawyer(client: AsyncClient, fake_db):
    lawyer = await _setup_lawyer(client, fake_db)
    user = await register_user(client)
    appt_id = await _complete_appointment(client, fake_db, lawyer, user)
    assert appt_id

    resp = await client.get("/api/v1/notifications", headers=auth_headers(lawyer))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["unread"] >= 1
    assert body["items"][0]["type"] == "APPOINTMENT"


async def test_mark_notification_read(client: AsyncClient, fake_db):
    lawyer = await _setup_lawyer(client, fake_db)
    user = await register_user(client)
    await _complete_appointment(client, fake_db, lawyer, user)

    resp = await client.get("/api/v1/notifications", headers=auth_headers(lawyer))
    notif_id = resp.json()["items"][0]["id"]
    mark = await client.patch(
        f"/api/v1/notifications/{notif_id}/read", headers=auth_headers(lawyer)
    )
    assert mark.status_code == 200
    assert mark.json()["is_read"] is True


async def test_review_creates_and_updates_rating(client: AsyncClient, fake_db):
    lawyer = await _setup_lawyer(client, fake_db)
    user = await register_user(client)
    resp = await client.post(
        "/api/v1/reviews",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "rating": 5, "comment": "Great"},
    )
    assert resp.status_code == 201, resp.text

    profile = await client.get(f"/api/v1/lawyers/{lawyer['user']['id']}")
    assert profile.json()["avg_rating"] == 5.0
    assert profile.json()["rating_count"] == 1


async def test_duplicate_review_rejected(client: AsyncClient, fake_db):
    lawyer = await _setup_lawyer(client, fake_db)
    user = await register_user(client)
    payload = {"lawyer_id": lawyer["user"]["id"], "rating": 4}
    first = await client.post("/api/v1/reviews", headers=auth_headers(user), json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/reviews", headers=auth_headers(user), json=payload)
    assert second.status_code == 409


async def test_list_reviews_for_lawyer(client: AsyncClient, fake_db):
    lawyer = await _setup_lawyer(client, fake_db)
    user = await register_user(client)
    await client.post(
        "/api/v1/reviews",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "rating": 3},
    )
    resp = await client.get(f"/api/v1/reviews/{lawyer['user']['id']}")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["reviewer_name"] == "Test User"


async def test_create_complaint(client: AsyncClient):
    user = await register_user(client)
    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={"subject": "Issue", "description": "Something went wrong"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "OPEN"


async def test_admin_resolves_complaint(client: AsyncClient, fake_db):
    user = await register_user(client)
    created = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={"subject": "Issue", "description": "Something went wrong"},
    )
    complaint_id = created.json()["id"]
    admin = await register_admin(client, name="Admin", email="admin@example.com")
    resp = await client.patch(
        f"/api/v1/complaints/{complaint_id}/resolve",
        headers=auth_headers(admin),
        json={"status": "RESOLVED", "admin_note": "We fixed it"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"


async def test_non_admin_cannot_resolve_complaint(client: AsyncClient, fake_db):
    user = await register_user(client)
    created = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={"subject": "Issue", "description": "Something went wrong"},
    )
    complaint_id = created.json()["id"]
    other = await register_user(client, email="other2@example.com", name="Other")
    resp = await client.patch(
        f"/api/v1/complaints/{complaint_id}/resolve",
        headers=auth_headers(other),
        json={"status": "RESOLVED"},
    )
    assert resp.status_code == 403


async def test_demo_payment(client: AsyncClient, fake_db):
    lawyer = await _setup_lawyer(client, fake_db)
    user = await register_user(client)
    await _complete_appointment(client, fake_db, lawyer, user)
    appts = await client.get("/api/v1/appointments", headers=auth_headers(user))
    appt_id = appts.json()["items"][0]["id"]
    resp = await client.post(
        "/api/v1/payments",
        headers=auth_headers(user),
        json={"appointment_id": appt_id, "amount": 100.0},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "PAID"
    assert resp.json()["reference"].startswith("LC-")
