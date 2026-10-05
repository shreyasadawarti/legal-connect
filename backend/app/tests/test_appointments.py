from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.models.platform import AppointmentStatus
from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register_lawyer,
    register_user,
)


def _slot(days: int = 1, hour: int = 10, minutes: int = 0, duration_min: int = 60):
    start = datetime.now(timezone.utc) + timedelta(days=days)
    start = start.replace(hour=hour, minute=minutes, second=0, microsecond=0)
    end = start + timedelta(minutes=duration_min)
    return start.isoformat(), end.isoformat()


async def _setup(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    return lawyer, user


async def test_client_books_appointment(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    start, end = _slot()
    resp = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={
            "lawyer_id": lawyer["user"]["id"],
            "category": "family",
            "start_time": start,
            "end_time": end,
            "description": "Consultation",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == AppointmentStatus.PENDING.value
    assert body["lawyer_id"] == lawyer["user"]["id"]
    assert body["client_id"] == user["user"]["id"]


async def test_booking_unverified_lawyer_rejected(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)  # still PENDING_VERIFICATION
    user = await register_user(client)
    start, end = _slot()
    resp = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={
            "lawyer_id": lawyer["user"]["id"],
            "start_time": start,
            "end_time": end,
        },
    )
    assert resp.status_code == 400


async def test_booking_self_rejected(client: AsyncClient, db):
    lawyer, _ = await _setup(client, db)
    start, end = _slot()
    resp = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(lawyer),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    assert resp.status_code == 400


async def test_anti_double_booking_conflict(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    start, end = _slot()
    payload = {
        "lawyer_id": lawyer["user"]["id"],
        "start_time": start,
        "end_time": end,
    }
    first = await client.post("/api/v1/appointments", headers=auth_headers(user), json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/appointments", headers=auth_headers(user), json=payload)
    assert second.status_code == 409


async def test_lawyer_confirms_appointment(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    start, end = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    appt_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/confirm", headers=auth_headers(lawyer)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == AppointmentStatus.CONFIRMED.value


async def test_only_lawyer_can_confirm(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    start, end = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    appt_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/confirm", headers=auth_headers(user)
    )
    assert resp.status_code == 403


async def test_client_cancels_appointment(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    start, end = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    appt_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/cancel", headers=auth_headers(user)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == AppointmentStatus.CANCELLED.value


async def test_reschedule_checks_conflicts(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    s1, e1 = _slot(days=1, hour=10)
    s2, e2 = _slot(days=1, hour=11)  # overlaps s1/e1
    a1 = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": s1, "end_time": e1},
    )
    a2 = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": s2, "end_time": e2},
    )
    # a1 and a2 conflict with each other already; instead reschedule a2 into a1's slot.
    resp = await client.patch(
        f"/api/v1/appointments/{a2.json()['id']}/reschedule",
        headers=auth_headers(user),
        json={"start_time": s1, "end_time": e1},
    )
    assert resp.status_code == 409


async def test_list_only_own_appointments(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    other = await register_user(client, email="other@example.com", name="Other")
    start, end = _slot()
    await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    resp = await client.get("/api/v1/appointments", headers=auth_headers(other))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    resp = await client.get("/api/v1/appointments", headers=auth_headers(user))
    assert resp.json()["total"] == 1


async def test_participant_only_can_view_detail(client: AsyncClient, db):
    lawyer, user = await _setup(client, db)
    other = await register_user(client, email="other@example.com", name="Other")
    start, end = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    appt_id = created.json()["id"]
    resp = await client.get(f"/api/v1/appointments/{appt_id}", headers=auth_headers(other))
    assert resp.status_code == 403
