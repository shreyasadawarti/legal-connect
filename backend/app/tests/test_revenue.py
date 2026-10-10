from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.repositories.revenue_repository import RevenueRepository
from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register_lawyer,
    register_user,
)


def _slot(days: int = 1, hour: int = 10, duration_min: int = 60):
    start = datetime.now(timezone.utc) + timedelta(days=days)
    start = start.replace(hour=hour, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=duration_min)
    return start.isoformat(), end.isoformat()


async def _book(client: AsyncClient, user, lawyer, *, duration_min: int = 60) -> str:
    start, end = _slot(duration_min=duration_min)
    resp = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={
            "lawyer_id": lawyer["user"]["id"],
            "category": "family",
            "start_time": start,
            "end_time": end,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _complete(client: AsyncClient, lawyer, appointment_id: str) -> None:
    await client.patch(
        f"/api/v1/appointments/{appointment_id}/confirm", headers=auth_headers(lawyer)
    )
    resp = await client.patch(
        f"/api/v1/appointments/{appointment_id}/complete", headers=auth_headers(lawyer)
    )
    assert resp.status_code == 200, resp.text


async def test_registration_records_fee(client: AsyncClient, db):
    await register_user(client)
    await register_lawyer(client)
    repo = RevenueRepository(db)
    assert await repo.total() == 20000.0
    assert await repo.total_by_source() == {"registration": 20000.0}


async def test_duplicate_registration_adds_no_revenue(client: AsyncClient, db):
    await register_user(client, email="dup@example.com")
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate",
            "email": "dup@example.com",
            "password": "StrongPass123",
            "role": "user",
        },
    )
    assert resp.status_code == 409
    assert await RevenueRepository(db).total() == 10000.0


async def test_completion_records_commission(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)  # hourly_rate = 100
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    appointment_id = await _book(client, user, lawyer, duration_min=60)
    await _complete(client, lawyer, appointment_id)

    repo = RevenueRepository(db)
    by_source = await repo.total_by_source()
    assert by_source["commission"] == 500.0  # 5 x (100/hr x 1h)
    assert by_source["registration"] == 20000.0
    assert await repo.total() == 20500.0


async def test_completion_is_idempotent(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    appointment_id = await _book(client, user, lawyer, duration_min=60)
    await _complete(client, lawyer, appointment_id)
    await _complete(client, lawyer, appointment_id)

    assert (await RevenueRepository(db).total_by_source())["commission"] == 500.0


async def test_zero_rate_records_no_commission(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={
            "bio": "Pro bono lawyer",
            "years_of_experience": 5,
            "categories": ["family"],
            "specializations": ["Divorce"],
            "languages": ["English"],
            "hourly_rate": 0.0,
            "city": "Mumbai",
            "availability": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    appointment_id = await _book(client, user, lawyer)
    await _complete(client, lawyer, appointment_id)

    assert "commission" not in await RevenueRepository(db).total_by_source()