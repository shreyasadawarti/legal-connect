from datetime import datetime, timedelta, timezone
from typing import Any

from httpx import AsyncClient

from app.models.platform import AppointmentStatus
from app.models.user import LawyerStatus, UserStatus
from app.tests.helpers import (
    activate_lawyer,
    add_verification_document,
    auth_headers,
    create_lawyer_profile,
    register,
    register_admin,
    register_lawyer,
    register_user,
)


async def _admin(client: AsyncClient) -> dict[str, Any]:
    return await register_admin(client)


def _seed_payment(fake_db: Any, *, user_id: str, amount: float, status: str = "PAID") -> None:
    fake_db["payments"]._docs.append(
        {
            "_id": _new_oid(fake_db),
            "user_id": user_id,
            "amount": amount,
            "status": status,
            "created_at": datetime.now(timezone.utc),
        }
    )


def _new_oid(fake_db: Any) -> str:
    n = len(fake_db["payments"]._docs) + 1
    return f"{n:024x}"


async def test_non_admin_forbidden(client: AsyncClient):
    user = await register_user(client)
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers(user))
    assert resp.status_code == 403


async def test_dashboard(client: AsyncClient, fake_db):
    await register_user(client)
    admin = await _admin(client)
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    _seed_payment(fake_db, user_id=admin["user"]["id"], amount=250.0)
    _seed_payment(fake_db, user_id=admin["user"]["id"], amount=50.0, status="PENDING")
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers(admin))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_users"] >= 3
    assert body["total_lawyers"] == 1
    assert body["pending_verifications"] == 1
    assert body["total_revenue"] == 250.0


async def test_list_users(client: AsyncClient):
    await register_user(client)
    admin = await _admin(client)
    resp = await client.get("/api/v1/admin/users", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert all("id" in u and "password_hash" not in u for u in body["items"])


async def test_suspend_user(client: AsyncClient, fake_db):
    user = await register_user(client)
    admin = await _admin(client)
    target_id = user["user"]["id"]
    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        headers=auth_headers(admin),
        json={"status": UserStatus.SUSPENDED.value},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == UserStatus.SUSPENDED.value
    notifs = await fake_db["notifications"].find({"user_id": target_id}).to_list()
    assert any(n.get("title") == "Account suspended" for n in notifs)


async def test_cannot_suspend_self(client: AsyncClient):
    admin = await _admin(client)
    resp = await client.patch(
        f"/api/v1/admin/users/{admin['user']['id']}/status",
        headers=auth_headers(admin),
        json={"status": UserStatus.SUSPENDED.value},
    )
    assert resp.status_code == 400


async def test_approve_lawyer(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await add_verification_document(client, lawyer)
    admin = await _admin(client)
    lawyer_id = lawyer["user"]["id"]
    resp = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer_id}/verification",
        headers=auth_headers(admin),
        json={"status": LawyerStatus.ACTIVE.value, "note": "Approved"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == LawyerStatus.ACTIVE.value
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer_id})
    assert profile["is_verified"] is True


async def test_approve_requires_verification_document(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    admin = await _admin(client)
    lawyer_id = lawyer["user"]["id"]
    resp = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer_id}/verification",
        headers=auth_headers(admin),
        json={"status": LawyerStatus.ACTIVE.value},
    )
    assert resp.status_code == 422
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer_id})
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value
    assert profile["is_verified"] is False


async def test_admin_get_verification_document(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await add_verification_document(client, lawyer)
    admin = await _admin(client)
    resp = await client.get(
        f"/api/v1/admin/lawyers/{lawyer['user']['id']}/verification-document",
        headers=auth_headers(admin),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "signed" in body["url"]
    assert body["filename"] == "license.pdf"
    assert body["document"]["owner_id"] == lawyer["user"]["id"]


async def test_admin_verification_document_forbidden_for_non_admin(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await add_verification_document(client, lawyer)
    admin = await _admin(client)
    url = f"/api/v1/admin/lawyers/{lawyer['user']['id']}/verification-document"
    admin_ok = await client.get(url, headers=auth_headers(admin))
    assert admin_ok.status_code == 200

    citizen = await register_user(client)
    resp = await client.get(url, headers=auth_headers(citizen))
    assert resp.status_code == 403

    other = await register_lawyer(client, email="otherlawyer@example.com")
    await create_lawyer_profile(client, other)
    resp = await client.get(url, headers=auth_headers(other))
    assert resp.status_code == 403


async def test_admin_verification_document_missing(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    admin = await _admin(client)
    resp = await client.get(
        f"/api/v1/admin/lawyers/{lawyer['user']['id']}/verification-document",
        headers=auth_headers(admin),
    )
    assert resp.status_code == 404


async def test_verification_document_private_to_owner(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    _, doc_id = await add_verification_document(client, lawyer)

    other = await register_lawyer(client, email="otherlawyer@example.com")
    await create_lawyer_profile(client, other)
    resp = await client.get(
        f"/api/v1/documents/{doc_id}/download", headers=auth_headers(other)
    )
    assert resp.status_code == 403

    citizen = await register_user(client)
    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers(citizen))
    assert resp.status_code == 403


async def test_delete_verification_document_unlinks_profile(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    _, doc_id = await add_verification_document(client, lawyer)
    resp = await client.delete(
        f"/api/v1/documents/{doc_id}", headers=auth_headers(lawyer)
    )
    assert resp.status_code == 204
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer["user"]["id"]})
    assert profile.get("verification_document_id") is None


async def test_list_lawyers(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    admin = await _admin(client)
    resp = await client.get(
        "/api/v1/admin/lawyers",
        headers=auth_headers(admin),
        params={"verification_status": LawyerStatus.PENDING_VERIFICATION.value},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == lawyer["user"]["id"]


async def test_respond_complaint(client: AsyncClient, fake_db):
    user = await register_user(client)
    created = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={"subject": "Issue", "description": "Something went wrong"},
    )
    complaint_id = created.json()["id"]
    admin = await _admin(client)
    resp = await client.patch(
        f"/api/v1/admin/complaints/{complaint_id}",
        headers=auth_headers(admin),
        json={"status": "RESOLVED", "admin_note": "We fixed it"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "RESOLVED"
    assert resp.json()["admin_note"] == "We fixed it"


async def test_list_complaints(client: AsyncClient):
    user = await register_user(client)
    await client.post(
        "/api/v1/complaints",
        headers=auth_headers(user),
        json={"subject": "Issue", "description": "Something went wrong"},
    )
    admin = await _admin(client)
    resp = await client.get("/api/v1/admin/complaints", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["user_name"] == "Test User"


async def test_analytics(client: AsyncClient, fake_db):
    await register_user(client)
    admin = await _admin(client)
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(fake_db, lawyer["user"]["id"])
    _seed_payment(fake_db, user_id=admin["user"]["id"], amount=100.0)
    resp = await client.get("/api/v1/admin/analytics", headers=auth_headers(admin))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["users_by_role"]["admin"] >= 1
    assert body["lawyers_by_status"]["ACTIVE"] == 1
    assert body["revenue_by_status"]["PAID"] == 100.0


async def test_audit_logs(client: AsyncClient):
    user = await register_user(client)
    admin = await _admin(client)
    await client.patch(
        f"/api/v1/admin/users/{user['user']['id']}/status",
        headers=auth_headers(admin),
        json={"status": UserStatus.SUSPENDED.value},
    )
    resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers=auth_headers(admin),
        params={"entity_type": "user"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"] == "user.update_status"


async def test_reports(client: AsyncClient, fake_db):
    await register_user(client)
    admin = await _admin(client)
    _seed_payment(fake_db, user_id=admin["user"]["id"], amount=99.0)
    resp = await client.get(
        "/api/v1/admin/reports/users", headers=auth_headers(admin)
    )
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "users"
    rev = await client.get("/api/v1/admin/reports/revenue", headers=auth_headers(admin))
    assert rev.status_code == 200
    assert rev.json()["summary"]["total_paid"] == 99.0


async def test_unknown_report(client: AsyncClient):
    admin = await _admin(client)
    resp = await client.get(
        "/api/v1/admin/reports/bogus", headers=auth_headers(admin)
    )
    assert resp.status_code == 404


async def test_list_appointments(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(fake_db, lawyer["user"]["id"])
    user = await register_user(client)
    start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
        hour=11, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(minutes=60)
    booked = await client.post(
        "/api/v1/appointments",
        headers=auth_headers(user),
        json={
            "lawyer_id": lawyer["user"]["id"],
            "category": "family",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "description": "Consultation",
        },
    )
    assert booked.status_code == 201, booked.text
    admin = await _admin(client)

    resp = await client.get(
        "/api/v1/admin/appointments",
        headers=auth_headers(admin),
        params={"status": AppointmentStatus.PENDING.value},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["client_name"] == "Test User"
    assert "lawyer_name" in item
    assert "id" in item
    assert item["status"] == AppointmentStatus.PENDING.value


async def test_citizen_cannot_verify_lawyer(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    citizen = await register_user(client)
    resp = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer['user']['id']}/verification",
        headers=auth_headers(citizen),
        json={"status": LawyerStatus.ACTIVE.value},
    )
    assert resp.status_code == 403
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer["user"]["id"]})
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value


async def test_lawyer_cannot_verify_lawyer(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    other_lawyer = await register_lawyer(
        client, name="Second Lawyer", email="second@example.com"
    )
    resp = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer['user']['id']}/verification",
        headers=auth_headers(other_lawyer),
        json={"status": LawyerStatus.ACTIVE.value},
    )
    assert resp.status_code == 403
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer["user"]["id"]})
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value


async def test_lawyer_cannot_self_verify_via_profile(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={
            "bio": "Updated bio",
            "years_of_experience": 6,
            "categories": ["family"],
            "specializations": ["Divorce"],
            "languages": ["English"],
            "hourly_rate": 120.0,
            "city": "Mumbai",
            "availability": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}
            ],
            "verification_status": LawyerStatus.ACTIVE.value,
            "is_verified": True,
        },
    )
    assert resp.status_code == 200, resp.text
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer["user"]["id"]})
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value
    assert profile["is_verified"] is False


async def test_reject_lawyer_stores_reason(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    admin = await _admin(client)
    lawyer_id = lawyer["user"]["id"]
    resp = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer_id}/verification",
        headers=auth_headers(admin),
        json={"status": LawyerStatus.REJECTED.value, "note": "Missing bar council license"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == LawyerStatus.REJECTED.value
    assert resp.json()["is_verified"] is False
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer_id})
    assert profile["rejection_reason"] == "Missing bar council license"

    approve = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer_id}/verification",
        headers=auth_headers(admin),
        json={"status": LawyerStatus.ACTIVE.value},
    )
    assert approve.status_code == 422

    await add_verification_document(client, lawyer)
    approve = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer_id}/verification",
        headers=auth_headers(admin),
        json={"status": LawyerStatus.ACTIVE.value},
    )
    assert approve.status_code == 200, approve.text
    profile = await fake_db["lawyer_profiles"].find_one({"user_id": lawyer_id})
    assert profile["rejection_reason"] is None
    assert profile["is_verified"] is True

