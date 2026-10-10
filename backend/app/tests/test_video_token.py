from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.config import settings
from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register_lawyer,
    register_user,
)

# Non-secret placeholders for tests. Real credentials come from the
# environment (ZEGO_APP_ID / ZEGO_APP_SECRET) and are never committed.
# The token algorithm requires a 32-byte secret.
ZEGO_APP_ID = 123456789
ZEGO_APP_SECRET = "0123456789abcdef0123456789abcdef"


def _slot(days: int = 1, hour: int = 10, minutes: int = 0, duration_min: int = 60):
    start = datetime.now(timezone.utc) + timedelta(days=days)
    start = start.replace(hour=hour, minute=minutes, second=0, microsecond=0)
    end = start + timedelta(minutes=duration_min)
    return start.isoformat(), end.isoformat()


def _configure_zego(monkeypatch) -> None:
    monkeypatch.setattr(settings, "zego_app_id", ZEGO_APP_ID)
    monkeypatch.setattr(settings, "zego_app_secret", ZEGO_APP_SECRET)


async def _setup_confirmed_appointment(client: AsyncClient, db) -> tuple[dict, dict, str]:
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    start, end = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    assert created.status_code == 201, created.text
    appt_id = created.json()["id"]
    confirmed = await client.patch(
        f"/api/v1/appointments/{appt_id}/confirm", headers=auth_headers(lawyer)
    )
    assert confirmed.status_code == 200, confirmed.text
    return lawyer, user, appt_id


async def test_participant_gets_video_token(client: AsyncClient, db, monkeypatch):
    _configure_zego(monkeypatch)
    lawyer, user, appt_id = await _setup_confirmed_appointment(client, db)

    for account in (user, lawyer):
        resp = await client.get(
            f"/api/v1/appointments/{appt_id}/video-token", headers=auth_headers(account)
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["room_id"] == f"lc_{appt_id}"
        assert body["token"].startswith("04")
        assert body["app_id"] == ZEGO_APP_ID
        assert body["expires_in"] > 0
        assert body["user_id"] == account["user"]["id"]
        assert body["user_name"] == account["user"]["name"]
        # Both participants must resolve to the same room.
        if account is user:
            user_room = body["room_id"]
        else:
            assert body["room_id"] == user_room

    resp = await client.get(
        f"/api/v1/appointments/{appt_id}/video-token", headers=auth_headers(user)
    )
    assert ZEGO_APP_SECRET not in resp.text


async def test_outsider_cannot_get_video_token(client: AsyncClient, db, monkeypatch):
    _configure_zego(monkeypatch)
    _, _, appt_id = await _setup_confirmed_appointment(client, db)
    other = await register_user(client, email="other@example.com", name="Other")
    resp = await client.get(
        f"/api/v1/appointments/{appt_id}/video-token", headers=auth_headers(other)
    )
    assert resp.status_code == 403


async def test_unknown_appointment_video_token_404(client: AsyncClient, monkeypatch):
    _configure_zego(monkeypatch)
    user = await register_user(client)
    resp = await client.get(
        "/api/v1/appointments/000000000000000000000000/video-token",
        headers=auth_headers(user),
    )
    assert resp.status_code == 404


async def test_pending_appointment_rejected(client: AsyncClient, db, monkeypatch):
    _configure_zego(monkeypatch)
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    start, end = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "start_time": start, "end_time": end},
    )
    appt_id = created.json()["id"]
    resp = await client.get(
        f"/api/v1/appointments/{appt_id}/video-token", headers=auth_headers(user)
    )
    assert resp.status_code == 400


async def test_cancelled_appointment_rejected(client: AsyncClient, db, monkeypatch):
    _configure_zego(monkeypatch)
    _, user, appt_id = await _setup_confirmed_appointment(client, db)
    cancelled = await client.patch(
        f"/api/v1/appointments/{appt_id}/cancel", headers=auth_headers(user)
    )
    assert cancelled.status_code == 200
    resp = await client.get(
        f"/api/v1/appointments/{appt_id}/video-token", headers=auth_headers(user)
    )
    assert resp.status_code == 400


async def test_unconfigured_zego_returns_503(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "zego_app_id", 0)
    monkeypatch.setattr(settings, "zego_app_secret", "")
    _, user, appt_id = await _setup_confirmed_appointment(client, db)
    resp = await client.get(
        f"/api/v1/appointments/{appt_id}/video-token", headers=auth_headers(user)
    )
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"]
