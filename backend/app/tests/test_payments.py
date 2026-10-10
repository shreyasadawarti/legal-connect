import json
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.config import settings
from app.dependencies import get_payment_gateway
from app.main import app
from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register_lawyer,
    register_user,
)

VALID_SIGNATURE = "valid_signature"
VALID_WEBHOOK_SIGNATURE = "valid_webhook_signature"


class FakeGateway:
    """Stand-in for Razorpay so tests never touch the network."""

    def __init__(self) -> None:
        self.orders: list[dict] = []
        self._n = 0

    @property
    def is_configured(self) -> bool:
        return True

    async def create_order(self, *, amount_paise, receipt, notes=None):
        self._n += 1
        order = {
            "id": f"order_test{self._n}",
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {},
        }
        self.orders.append(order)
        return order

    def verify_payment_signature(self, *, order_id, payment_id, signature):
        return signature == VALID_SIGNATURE

    def verify_webhook_signature(self, *, body, signature):
        return signature == VALID_WEBHOOK_SIGNATURE


def _use_fake_gateway() -> FakeGateway:
    gateway = FakeGateway()
    app.dependency_overrides[get_payment_gateway] = lambda: gateway
    return gateway


def _slot():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    return start.isoformat(), (start + timedelta(hours=1)).isoformat()


async def _setup_lawyer(client: AsyncClient, db, *, rate: float = 100.0):
    lawyer = await register_lawyer(client)
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={
            "bio": "Experienced family lawyer",
            "years_of_experience": 5,
            "categories": ["family"],
            "specializations": ["Divorce"],
            "languages": ["English"],
            "hourly_rate": rate,
            "city": "Mumbai",
            "availability": [{"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}],
        },
    )
    assert resp.status_code == 200, resp.text
    await activate_lawyer(db, lawyer["user"]["id"])
    return lawyer


async def _confirmed_appointment(client: AsyncClient, lawyer, user) -> str:
    s, e = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "category": "family", "start_time": s, "end_time": e},
    )
    assert created.status_code == 201, created.text
    appointment_id = created.json()["id"]
    confirmed = await client.patch(
        f"/api/v1/appointments/{appointment_id}/confirm", headers=auth_headers(lawyer)
    )
    assert confirmed.status_code == 200, confirmed.text
    return appointment_id


async def test_create_order_computes_amount_server_side(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    gateway = _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db, rate=100.0)
    user = await register_user(client)
    appointment_id = await _confirmed_appointment(client, lawyer, user)

    resp = await client.post(
        "/api/v1/payments/order",
        headers=auth_headers(user),
        json={"appointment_id": appointment_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["amount"] == 100.0
    assert body["amount_paise"] == 10000
    assert body["currency"] == "INR"
    assert body["key_id"] == "rzp_test_key"
    assert body["order_id"] == "order_test1"
    assert body["reference"].startswith("LC-")
    assert gateway.orders[0]["receipt"] == body["reference"]

    lookup = await client.get(
        f"/api/v1/payments/appointment/{appointment_id}", headers=auth_headers(user)
    )
    assert lookup.json()["payment"]["status"] == "PENDING"


async def test_order_ignores_client_supplied_amount(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db, rate=200.0)
    user = await register_user(client)
    appointment_id = await _confirmed_appointment(client, lawyer, user)

    resp = await client.post(
        "/api/v1/payments/order",
        headers=auth_headers(user),
        json={"appointment_id": appointment_id, "amount": 1.0},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["amount"] == 200.0


async def test_only_client_can_create_order(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    other = await register_user(client, email="other@example.com")
    appointment_id = await _confirmed_appointment(client, lawyer, user)

    resp = await client.post(
        "/api/v1/payments/order",
        headers=auth_headers(other),
        json={"appointment_id": appointment_id},
    )
    assert resp.status_code == 403


async def test_order_rejected_for_unconfirmed_appointment(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    s, e = _slot()
    created = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={"lawyer_id": lawyer["user"]["id"], "category": "family", "start_time": s, "end_time": e},
    )
    appointment_id = created.json()["id"]

    resp = await client.post(
        "/api/v1/payments/order",
        headers=auth_headers(user),
        json={"appointment_id": appointment_id},
    )
    assert resp.status_code == 409


async def test_verify_marks_paid_and_is_idempotent(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    appointment_id = await _confirmed_appointment(client, lawyer, user)

    order = await client.post(
        "/api/v1/payments/order",
        headers=auth_headers(user),
        json={"appointment_id": appointment_id},
    )
    order = order.json()

    payload = {
        "payment_id": order["payment_id"],
        "razorpay_order_id": order["order_id"],
        "razorpay_payment_id": "pay_test123",
        "razorpay_signature": VALID_SIGNATURE,
    }
    verified = await client.post("/api/v1/payments/verify", headers=auth_headers(user), json=payload)
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "PAID"
    assert verified.json()["gateway_payment_id"] == "pay_test123"

    again = await client.post("/api/v1/payments/verify", headers=auth_headers(user), json=payload)
    assert again.status_code == 200
    assert again.json()["status"] == "PAID"

    notifications = await client.get("/api/v1/notifications", headers=auth_headers(lawyer))
    titles = [n["title"] for n in notifications.json()["items"]]
    assert "Payment received" in titles


async def test_verify_rejects_bad_signature(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    appointment_id = await _confirmed_appointment(client, lawyer, user)
    order = (
        await client.post(
            "/api/v1/payments/order",
            headers=auth_headers(user),
            json={"appointment_id": appointment_id},
        )
    ).json()

    resp = await client.post(
        "/api/v1/payments/verify",
        headers=auth_headers(user),
        json={
            "payment_id": order["payment_id"],
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": "forged",
        },
    )
    assert resp.status_code == 400
    lookup = await client.get(
        f"/api/v1/payments/appointment/{appointment_id}", headers=auth_headers(user)
    )
    assert lookup.json()["payment"]["status"] == "PENDING"


async def test_webhook_marks_paid(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", "rzp_test_secret")
    monkeypatch.setattr(settings, "razorpay_webhook_secret", "whsec_test")
    _use_fake_gateway()
    lawyer = await _setup_lawyer(client, db)
    user = await register_user(client)
    appointment_id = await _confirmed_appointment(client, lawyer, user)
    order = (
        await client.post(
            "/api/v1/payments/order",
            headers=auth_headers(user),
            json={"appointment_id": appointment_id},
        )
    ).json()

    event = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_webhook1", "order_id": order["order_id"]}}},
    }
    resp = await client.post(
        "/api/v1/payments/webhook",
        content=json.dumps(event).encode(),
        headers={"X-Razorpay-Signature": VALID_WEBHOOK_SIGNATURE},
    )
    assert resp.status_code == 200, resp.text

    lookup = await client.get(
        f"/api/v1/payments/appointment/{appointment_id}", headers=auth_headers(user)
    )
    assert lookup.json()["payment"]["status"] == "PAID"


async def test_webhook_rejects_bad_signature(client: AsyncClient, db, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_webhook_secret", "whsec_test")
    _use_fake_gateway()
    resp = await client.post(
        "/api/v1/payments/webhook",
        content=b'{"event": "payment.captured"}',
        headers={"X-Razorpay-Signature": "forged"},
    )
    assert resp.status_code == 400
