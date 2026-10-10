from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register_admin,
    register_lawyer,
    register_user,
)
from app.repositories.payment_repository import PaymentRepository


def _slot():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    return start.isoformat(), (start + timedelta(minutes=60)).isoformat()


async def _complete_appointment(client: AsyncClient, db, lawyer, user):
    s, e = _slot()
    appt = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={
            "lawyer_id": lawyer["user"]["id"],
            "category": "family",
            "start_time": s,
            "end_time": e,
        },
    )
    assert appt.status_code == 201, appt.text
    return appt.json()["id"]


async def _create_paid_payment(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    user = await register_user(client)
    appt_id = await _complete_appointment(client, db, lawyer, user)
    doc = await PaymentRepository(db).create(
        appointment_id=appt_id,
        payee_id=user["user"]["id"],
        amount=150.0,
    )
    await db.commit()
    return user, doc["_id"], doc


async def test_download_payment_receipt_pdf(client: AsyncClient, db):
    user, payment_id, _ = await _create_paid_payment(client, db)
    resp = await client.get(
        f"/api/v1/payments/{payment_id}/receipt",
        headers=auth_headers(user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"


async def test_non_payee_cannot_download_receipt(client: AsyncClient, db):
    user, payment_id, _ = await _create_paid_payment(client, db)
    other = await register_user(client, email=f"otherpdf{id(user)}@example.com", name="Other")
    resp = await client.get(
        f"/api/v1/payments/{payment_id}/receipt",
        headers=auth_headers(other),
    )
    assert resp.status_code == 403


async def test_receipt_unknown_payment_404(client: AsyncClient):
    user = await register_user(client)
    resp = await client.get(
        "/api/v1/payments/000000000000000000000000/receipt",
        headers=auth_headers(user),
    )
    assert resp.status_code == 404


async def test_admin_download_report_pdf(client: AsyncClient, db):
    admin = await register_admin(client)
    resp = await client.get(
        "/api/v1/admin/reports/users/download",
        headers=auth_headers(admin),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"


async def test_admin_report_download_unknown_404(client: AsyncClient):
    admin = await register_admin(client)
    resp = await client.get(
        "/api/v1/admin/reports/bogus/download",
        headers=auth_headers(admin),
    )
    assert resp.status_code == 404
