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


async def _setup_lawyer(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    return lawyer


def _slot():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    return start.isoformat(), (start + timedelta(minutes=60)).isoformat()


async def _complete_appointment(client: AsyncClient, db, lawyer, user):
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
        json={
            "name": "Updated Name",
            "phone": "+91 98765 43210",
            "city": "Pune",
            "address": "12 Shivaji Nagar, Pune 411005",
            "bio": "Tenant dispute advice",
            "preferred_language": "hi",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Name"
    assert body["preferred_language"] == "hi"
    assert body["phone"] == "+91 98765 43210"
    assert body["city"] == "Pune"
    assert body["address"] == "12 Shivaji Nagar, Pune 411005"
    assert body["bio"] == "Tenant dispute advice"


async def test_profile_update_persists_across_refetch(client: AsyncClient):
    """A save must survive a re-read, which is what the profile page relies on.

    The page seeds its form from `GET /users/me` after a reload, so a value that
    only lives in the PATCH response would look lost to the user.
    """
    user = await register_user(client)
    resp = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers(user),
        json={"name": "Persisted Name", "address": "9 Fort Road, Mumbai 400001"},
    )
    assert resp.status_code == 200

    refetch = await client.get("/api/v1/users/me", headers=auth_headers(user))
    assert refetch.status_code == 200
    assert refetch.json()["name"] == "Persisted Name"
    assert refetch.json()["address"] == "9 Fort Road, Mumbai 400001"


async def test_profile_update_persists_for_every_role(client: AsyncClient, db):
    """The address lives on the shared user record, so all three roles get it."""
    accounts = {
        "user": await register_user(client),
        "lawyer": await register_lawyer(client),
        "admin": await register_admin(client),
    }
    for role, account in accounts.items():
        address = f"{role} address, sector {len(role)}"
        resp = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers(account),
            json={"address": address},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["address"] == address

        refetch = await client.get(
            "/api/v1/users/me", headers=auth_headers(account)
        )
        assert refetch.status_code == 200
        assert refetch.json()["address"] == address


async def test_profile_update_rejects_oversized_address(client: AsyncClient):
    user = await register_user(client)
    resp = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers(user),
        json={"address": "x" * 501},
    )
    assert resp.status_code == 422


async def test_profile_update_cannot_touch_email(client: AsyncClient):
    """Email is not in ProfileUpdate, so it stays read-only for self-service."""
    user = await register_user(client)
    resp = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers(user),
        json={"email": "hijack@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


async def test_get_own_profile(client: AsyncClient):
    user = await register_user(client)
    resp = await client.get("/api/v1/users/me", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"
    assert resp.json()["address"] is None


async def test_profile_update_requires_auth(client: AsyncClient):
    resp = await client.patch("/api/v1/users/me", json={"name": "x"})
    assert resp.status_code in (401, 403)


async def test_booking_creates_notification_for_lawyer(client: AsyncClient, db):
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    appt_id = await _complete_appointment(client, db, lawyer, user)
    assert appt_id

    resp = await client.get("/api/v1/notifications", headers=auth_headers(lawyer))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["unread"] >= 1
    assert body["items"][0]["type"] == "APPOINTMENT"


async def test_mark_notification_read(client: AsyncClient, db):
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    await _complete_appointment(client, db, lawyer, user)

    resp = await client.get("/api/v1/notifications", headers=auth_headers(lawyer))
    notif_id = resp.json()["items"][0]["id"]
    mark = await client.patch(
        f"/api/v1/notifications/{notif_id}/read", headers=auth_headers(lawyer)
    )
    assert mark.status_code == 200
    assert mark.json()["is_read"] is True


async def test_review_creates_and_updates_rating(client: AsyncClient, db):
    lawyer = await _setup_lawyer(client, db)
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


async def test_duplicate_review_rejected(client: AsyncClient, db):
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    payload = {"lawyer_id": lawyer["user"]["id"], "rating": 4}
    first = await client.post("/api/v1/reviews", headers=auth_headers(user), json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/reviews", headers=auth_headers(user), json=payload)
    assert second.status_code == 409


async def test_list_reviews_for_lawyer(client: AsyncClient, db):
    lawyer = await _setup_lawyer(client, db)
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


async def test_complaint_against_own_appointment_is_accepted(
    client: AsyncClient, db
):
    # The citizen booked this lawyer, so reporting them must succeed and the link must
    # be persisted so admins can trace the complaint back to the lawyer.
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    appt_id = await _complete_appointment(client, db, lawyer, user)

    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={
            "subject": "Unprofessional behaviour",
            "description": "The lawyer was late and did not follow through.",
            "related_appointment_id": appt_id,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["related_appointment_id"] == appt_id

    mine = await client.get("/api/v1/complaints", headers=auth_headers(user))
    assert mine.status_code == 200
    assert mine.json()["total"] == 1
    assert mine.json()["items"][0]["related_appointment_id"] == appt_id


async def test_complaint_rejects_another_citizens_appointment(
    client: AsyncClient, db
):
    # A citizen must not be able to attach someone else's appointment id.
    lawyer = await _setup_lawyer(client, db)
    owner = await register_user(client)
    appt_id = await _complete_appointment(client, db, lawyer, owner)

    attacker = await register_user(
        client, name="Attacker", email="attacker@example.com"
    )
    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(attacker),
        json={
            "subject": "Framing someone",
            "description": "This is not my appointment.",
            "related_appointment_id": appt_id,
        },
    )
    assert resp.status_code == 403

    # Nothing was written.
    listed = await client.get("/api/v1/complaints", headers=auth_headers(attacker))
    assert listed.json()["total"] == 0


async def test_complaint_rejects_unknown_appointment(client: AsyncClient):
    user = await register_user(client)
    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={
            "subject": "Bad link",
            "description": "That appointment does not exist.",
            "related_appointment_id": "000000000000000000000000",
        },
    )
    assert resp.status_code == 404


async def test_citizen_cannot_file_complaint_against_the_lawyer_side(
    client: AsyncClient, db
):
    # The lawyer on the appointment is the target, never the caller, so the lawyer must
    # not be able to file a complaint naming themselves.
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    appt_id = await _complete_appointment(client, db, lawyer, user)

    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(lawyer),
        json={
            "subject": "Not allowed",
            "description": "A lawyer cannot be a complainant.",
            "related_appointment_id": appt_id,
        },
    )
    assert resp.status_code == 403


async def test_admin_cannot_file_complaint(client: AsyncClient):
    admin = await register_admin(client)
    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(admin),
        json={"subject": "Admin issue", "description": "Admins are not citizens."},
    )
    assert resp.status_code == 403


async def test_admin_resolves_complaint(client: AsyncClient, db):
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


async def test_non_admin_cannot_resolve_complaint(client: AsyncClient, db):
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


async def test_demo_payment(client: AsyncClient, db):
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    await _complete_appointment(client, db, lawyer, user)
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
