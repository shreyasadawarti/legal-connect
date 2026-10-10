from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select

from app.db.compat import new_id, utcnow
from app.db.models import Appointment, Notification, Payment, User
from app.models.platform import AppointmentStatus, LegalCategory
from app.models.user import LawyerStatus, UserRole, UserStatus
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.notification_repository import NotificationRepository
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


async def _ensure_appointment(db: Any) -> str:
    """Create a completed appointment so payments have a valid foreign key.

    The old fake had no referential integrity, so tests could invent payment rows
    pointing at nothing. MySQL enforces the constraint, so the fixture now
    creates the appointment the payment belongs to.
    """
    lawyer = (
        await db.execute(select(User).where(User.role == UserRole.LAWYER).limit(1))
    ).scalar_one_or_none()
    citizen = (
        await db.execute(select(User).where(User.role == UserRole.USER).limit(1))
    ).scalar_one_or_none()
    if lawyer is None or citizen is None:
        lawyer = User(
            name="Seed Lawyer",
            email="seed-lawyer@example.com",
            password_hash="x",
            role=UserRole.LAWYER,
            status=UserStatus.ACTIVE,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        citizen = User(
            name="Seed Citizen",
            email="seed-citizen@example.com",
            password_hash="x",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add_all([lawyer, citizen])
        await db.flush()

    now = utcnow()
    appt = Appointment(
        id=new_id(),
        lawyer_id=lawyer.id,
        client_id=citizen.id,
        category=LegalCategory.FAMILY,
        start_time=now,
        end_time=now + timedelta(hours=1),
        status=AppointmentStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    db.add(appt)
    await db.commit()
    return appt.id


async def _seed_payment(db: Any, *, user_id: str, amount: float, status: str = "PAID") -> None:
    db.add(
        Payment(
            id=new_id(),
            appointment_id=await _ensure_appointment(db),
            payee_id=user_id,
            amount=Decimal(str(amount)),
            status=status,
            reference=f"LC-{uuid4().hex[:10].upper()}",
            created_at=utcnow(),
        )
    )
    await db.commit()


async def test_non_admin_forbidden(client: AsyncClient):
    user = await register_user(client)
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers(user))
    assert resp.status_code == 403


async def test_dashboard(client: AsyncClient, db):
    await register_user(client)
    admin = await _admin(client)
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers(admin))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_users"] >= 3
    assert body["total_lawyers"] == 1
    assert body["pending_verifications"] == 1
    assert body["total_revenue"] == 20000.0


async def test_list_users(client: AsyncClient):
    await register_user(client)
    admin = await _admin(client)
    resp = await client.get("/api/v1/admin/users", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert all("id" in u and "password_hash" not in u for u in body["items"])


async def test_suspend_user(client: AsyncClient, db):
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
    notifs = (await NotificationRepository(db).list_for_user(target_id))["items"]
    assert any(n.get("title") == "Account suspended" for n in notifs)


async def test_cannot_suspend_self(client: AsyncClient):
    admin = await _admin(client)
    resp = await client.patch(
        f"/api/v1/admin/users/{admin['user']['id']}/status",
        headers=auth_headers(admin),
        json={"status": UserStatus.SUSPENDED.value},
    )
    assert resp.status_code == 400


async def test_approve_lawyer(client: AsyncClient, db):
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
    profile = await LawyerRepository(db).find_by_user_id(lawyer_id)
    assert profile["is_verified"] is True


async def test_approve_requires_verification_document(client: AsyncClient, db):
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
    profile = await LawyerRepository(db).find_by_user_id(lawyer_id)
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


async def test_delete_verification_document_unlinks_profile(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    _, doc_id = await add_verification_document(client, lawyer)
    resp = await client.delete(
        f"/api/v1/documents/{doc_id}", headers=auth_headers(lawyer)
    )
    assert resp.status_code == 204
    profile = await LawyerRepository(db).find_by_user_id(lawyer["user"]["id"])
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


async def test_respond_complaint(client: AsyncClient, db):
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
    reporter = await register_user(
        client, name="Reporter", email="reporter@example.com"
    )
    reported = await register_user(
        client, name="Reported User", email="reported@example.com"
    )
    await client.post(
        "/api/v1/complaints",
        headers=auth_headers(reporter),
        json={
            "subject": "Issue",
            "description": "Something went wrong",
            "target_user_id": reported["user"]["id"],
            "category": "harassment",
        },
    )
    admin = await _admin(client)
    resp = await client.get("/api/v1/admin/complaints", headers=auth_headers(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["user_name"] == "Reporter"
    assert item["target_user_name"] == "Reported User"
    assert item["target_user_email"] == "reported@example.com"
    assert item["category"] == "harassment"


async def _file_complaint_with_target(
    client: AsyncClient, reporter: dict[str, Any], reported: dict[str, Any]
) -> str:
    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(reporter),
        json={
            "subject": "Issue",
            "description": "Something went wrong",
            "target_user_id": reported["user"]["id"],
            "category": "harassment",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_admin_responds_separately_to_both_parties(client: AsyncClient):
    reporter = await register_user(
        client, name="Reporter", email="reporter@example.com"
    )
    reported = await register_user(
        client, name="Reported User", email="reported@example.com"
    )
    complaint_id = await _file_complaint_with_target(client, reporter, reported)
    admin = await _admin(client)

    resp = await client.patch(
        f"/api/v1/admin/complaints/{complaint_id}",
        headers=auth_headers(admin),
        json={
            "status": "IN_PROGRESS",
            "reporter_response": "Thanks, we are investigating.",
            "reported_response": "We are looking into this for you.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["reporter_response"] == "Thanks, we are investigating."
    assert body["reported_response"] == "We are looking into this for you."
    assert body["reporter_responded_at"] is not None
    assert body["reported_responded_at"] is not None

    listing = await client.get(
        "/api/v1/admin/complaints", headers=auth_headers(admin)
    )
    item = listing.json()["items"][0]
    assert item["reporter_response"] == "Thanks, we are investigating."
    assert item["reported_response"] == "We are looking into this for you."


async def test_response_notifications_go_to_both_parties(client: AsyncClient):
    reporter = await register_user(
        client, name="Reporter", email="reporter@example.com"
    )
    reported = await register_user(
        client, name="Reported User", email="reported@example.com"
    )
    complaint_id = await _file_complaint_with_target(client, reporter, reported)
    admin = await _admin(client)

    resp = await client.patch(
        f"/api/v1/admin/complaints/{complaint_id}",
        headers=auth_headers(admin),
        json={
            "status": "RESOLVED",
            "reporter_response": "Resolved for you.",
            "reported_response": "Noted for you.",
        },
    )
    assert resp.status_code == 200, resp.text

    reporter_ns = (await client.get("/api/v1/notifications", headers=auth_headers(reporter))).json()["items"]
    target_ns = (await client.get("/api/v1/notifications", headers=auth_headers(reported))).json()["items"]

    reporter_dirs = [
        n["data"].get("direction")
        for n in reporter_ns
        if n["data"] and n["data"].get("complaint_id") == complaint_id
    ]
    target_dirs = [
        n["data"].get("direction")
        for n in target_ns
        if n["data"] and n["data"].get("complaint_id") == complaint_id
    ]
    assert "reporter" in reporter_dirs
    assert "reported" not in reporter_dirs
    assert "reported" in target_dirs
    assert "reporter" not in target_dirs


async def test_status_only_update_preserves_prior_responses(client: AsyncClient):
    reporter = await register_user(
        client, name="Reporter", email="reporter@example.com"
    )
    reported = await register_user(
        client, name="Reported User", email="reported@example.com"
    )
    complaint_id = await _file_complaint_with_target(client, reporter, reported)
    admin = await _admin(client)

    first = await client.patch(
        f"/api/v1/admin/complaints/{complaint_id}",
        headers=auth_headers(admin),
        json={
            "status": "IN_PROGRESS",
            "reporter_response": "Investigating.",
            "reported_response": "Under review.",
        },
    )
    assert first.status_code == 200, first.text

    listing = await client.get(
        "/api/v1/admin/complaints", headers=auth_headers(admin)
    )
    before = listing.json()["items"][0]

    moved = await client.patch(
        f"/api/v1/admin/complaints/{complaint_id}",
        headers=auth_headers(admin),
        json={"status": "RESOLVED"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "RESOLVED"

    listing = await client.get(
        "/api/v1/admin/complaints", headers=auth_headers(admin)
    )
    after = listing.json()["items"][0]
    assert after["reporter_response"] == before["reporter_response"]
    assert after["reported_response"] == before["reported_response"]
    assert after["reporter_responded_at"] == before["reporter_responded_at"]
    assert after["reported_responded_at"] == before["reported_responded_at"]


async def test_non_admin_cannot_respond_via_admin_endpoint(client: AsyncClient):
    reporter = await register_user(
        client, name="Reporter", email="reporter@example.com"
    )
    reported = await register_user(
        client, name="Reported User", email="reported@example.com"
    )
    complaint_id = await _file_complaint_with_target(client, reporter, reported)
    other = await register_user(client, name="Other", email="other@example.com")

    resp = await client.patch(
        f"/api/v1/admin/complaints/{complaint_id}",
        headers=auth_headers(other),
        json={"status": "RESOLVED", "reporter_response": "Unauthorized"},
    )
    assert resp.status_code == 403


async def test_respond_unknown_complaint(client: AsyncClient):
    admin = await _admin(client)
    resp = await client.patch(
        f"/api/v1/admin/complaints/000000000000000000000000",
        headers=auth_headers(admin),
        json={"status": "RESOLVED"},
    )
    assert resp.status_code == 404


async def test_analytics(client: AsyncClient, db):
    await register_user(client)
    admin = await _admin(client)
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    resp = await client.get("/api/v1/admin/analytics", headers=auth_headers(admin))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["users_by_role"]["admin"] >= 1
    assert body["lawyers_by_status"]["ACTIVE"] == 1
    assert body["revenue_by_source"] == {"registration": 20000.0}


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


async def test_reports(client: AsyncClient, db):
    await register_user(client)
    admin = await _admin(client)
    resp = await client.get(
        "/api/v1/admin/reports/users", headers=auth_headers(admin)
    )
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "users"
    rev = await client.get("/api/v1/admin/reports/revenue", headers=auth_headers(admin))
    assert rev.status_code == 200
    summary = rev.json()["summary"]
    assert summary["total_revenue"] == 10000.0
    assert summary["by_source"] == {"registration": 10000.0}


async def test_unknown_report(client: AsyncClient):
    admin = await _admin(client)
    resp = await client.get(
        "/api/v1/admin/reports/bogus", headers=auth_headers(admin)
    )
    assert resp.status_code == 404


async def test_list_appointments(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
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


async def test_citizen_cannot_verify_lawyer(client: AsyncClient, db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    citizen = await register_user(client)
    resp = await client.patch(
        f"/api/v1/admin/lawyers/{lawyer['user']['id']}/verification",
        headers=auth_headers(citizen),
        json={"status": LawyerStatus.ACTIVE.value},
    )
    assert resp.status_code == 403
    profile = await LawyerRepository(db).find_by_user_id(lawyer["user"]["id"])
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value


async def test_lawyer_cannot_verify_lawyer(client: AsyncClient, db):
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
    profile = await LawyerRepository(db).find_by_user_id(lawyer["user"]["id"])
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value


async def test_lawyer_cannot_self_verify_via_profile(client: AsyncClient, db):
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
    profile = await LawyerRepository(db).find_by_user_id(lawyer["user"]["id"])
    assert profile["verification_status"] == LawyerStatus.PENDING_VERIFICATION.value
    assert profile["is_verified"] is False


async def test_reject_lawyer_stores_reason(client: AsyncClient, db):
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
    profile = await LawyerRepository(db).find_by_user_id(lawyer_id)
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
    profile = await LawyerRepository(db).find_by_user_id(lawyer_id)
    assert profile["rejection_reason"] is None
    assert profile["is_verified"] is True

