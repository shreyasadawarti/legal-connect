from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_document_storage, require_db, require_roles
from app.models.platform import AppointmentStatus, ComplaintStatus
from app.models.user import LawyerStatus, UserRole, UserStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.revenue_repository import RevenueRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminAppointmentsResponse,
    AdminAuditLogsResponse,
    AdminComplaintResponsePayload,
    AdminDashboardResponse,
    AdminReportResponse,
    AdminUserStatusRequest,
    AdminUsersResponse,
    AdminVerificationRequest,
    serialize_appointment_item,
    serialize_audit_item,
    serialize_user_item,
)
from app.schemas.document import DocumentResponse, serialize_document
from app.services.cloudinary_service import DocumentStorageError
from app.services.pdf_service import build_admin_report_pdf

router = APIRouter(prefix="/admin", tags=["admin"])

AdminDep = Annotated[dict, Depends(require_roles(UserRole.ADMIN))]


async def _audit(
    db: AsyncSession,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    await AuditLogRepository(db).record(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    users_repo = UserRepository(db)
    lawyers_repo = LawyerRepository(db)
    appts_repo = AppointmentRepository(db)
    complaints_repo = ComplaintRepository(db)

    total_users = await users_repo.count_all()
    total_lawyer_profiles = await lawyers_repo.count_all()
    total_appointments = await appts_repo.count_all()
    total_complaints = await complaints_repo.count_all()
    pending_verifications = await lawyers_repo.count_by_status(
        LawyerStatus.PENDING_VERIFICATION
    )
    open_complaints = await complaints_repo.count_in_statuses(
        (ComplaintStatus.OPEN, ComplaintStatus.IN_PROGRESS)
    )
    total_revenue = await RevenueRepository(db).total()

    return AdminDashboardResponse(
        total_users=total_users,
        total_lawyers=total_lawyer_profiles,
        total_appointments=total_appointments,
        pending_verifications=pending_verifications,
        open_complaints=open_complaints,
        total_revenue=total_revenue,
    )


@router.get("/users", response_model=AdminUsersResponse)
async def admin_list_users(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
    role: Optional[str] = None,
    user_status: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    role_enum = UserRole(role) if role in {r.value for r in UserRole} else None
    status_enum = UserStatus(user_status) if user_status in {s.value for s in UserStatus} else None
    result = await UserRepository(db).list_all(
        role=role_enum,
        status=status_enum,
        q=(q or "").strip() or None,
        page=page,
        page_size=page_size,
    )
    items = [serialize_user_item(u) for u in result["items"]]
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.patch("/users/{user_id}/status")
async def admin_update_user_status(
    user_id: str,
    payload: AdminUserStatusRequest,
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    repo = UserRepository(db)
    target = await repo.find_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target["_id"]) == admin["id"]:
        raise HTTPException(status_code=400, detail="Admins cannot change their own status")
    updated = await repo.set_status(user_id, payload.status)
    await _audit(
        db,
        admin["id"],
        "user.update_status",
        "user",
        user_id,
        {"status": payload.status.value},
    )
    if payload.status == UserStatus.SUSPENDED:
        await NotificationRepository(db).create(
            user_id=user_id,
            notification_type="SYSTEM",
            title="Account suspended",
            message="Your account has been suspended. Contact support for details.",
        )
    return serialize_user_item(updated)


@router.get("/lawyers")
async def admin_list_lawyers(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
    verification_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = LawyerRepository(db)
    result = await repo.list_by_status(
        status=verification_status or None,
        page=page,
        page_size=page_size,
    )
    users = await UserRepository(db).find_by_ids([p["user_id"] for p in result["items"]])
    user_map = {str(u["_id"]): u for u in users}
    from app.schemas.lawyer import serialize_lawyer_profile

    items = [serialize_lawyer_profile(p, user_map.get(p["user_id"])) for p in result["items"]]
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.patch("/lawyers/{lawyer_id}/verification")
async def admin_set_lawyer_verification(
    lawyer_id: str,
    payload: AdminVerificationRequest,
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    repo = LawyerRepository(db)
    profile = await repo.find_by_user_id(lawyer_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Lawyer profile not found")
    try:
        new_status = LawyerStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid verification status") from exc
    if (
        new_status == LawyerStatus.ACTIVE
        and not profile.get("verification_document_id")
    ):
        raise HTTPException(
            status_code=422,
            detail="Lawyer must upload a documentary proof before approval",
        )
    updated = await repo.set_verification_status(lawyer_id, new_status, note=payload.note)
    await _audit(
        db,
        admin["id"],
        "lawyer.verify",
        "lawyer",
        lawyer_id,
        {"verification_status": new_status.value, "note": payload.note},
    )
    await NotificationRepository(db).create(
        user_id=lawyer_id,
        notification_type="SYSTEM",
        title="Lawyer verification update",
        message=f"Your lawyer profile was {new_status.value.replace('_', ' ').lower()}.",
        data={"verification_status": new_status.value, "note": payload.note},
    )
    updated["user_id"] = lawyer_id
    from app.schemas.lawyer import serialize_lawyer_profile

    account = await UserRepository(db).find_by_id(lawyer_id) or {}
    return serialize_lawyer_profile(updated, account)


@router.get("/lawyers/{lawyer_id}/verification-document")
async def admin_get_lawyer_verification_document(
    lawyer_id: str,
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
    storage = Depends(get_document_storage),
):
    repo = LawyerRepository(db)
    profile = await repo.find_by_user_id(lawyer_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Lawyer profile not found")
    doc_id = profile.get("verification_document_id")
    if not doc_id:
        raise HTTPException(status_code=404, detail="No verification document uploaded")
    docs = DocumentRepository(db)
    doc = await docs.find_by_id(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Verification document missing")
    try:
        url = storage.signed_url(doc.get("public_id", ""), doc.get("resource_type", "raw"))
    except DocumentStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    owner = await UserRepository(db).find_by_id(doc.get("owner_id", "")) or {}
    return {
        "document": DocumentResponse.model_validate(
            serialize_document(doc, owner_name=owner.get("name", ""))
        ),
        "url": url,
        "filename": doc.get("original_name", "document"),
    }


@router.get("/appointments", response_model=AdminAppointmentsResponse)
async def admin_list_appointments(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    appt_status = None
    if status_filter:
        try:
            appt_status = AppointmentStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid appointment status: {status_filter}",
            ) from exc
    listing = await AppointmentRepository(db).list_all_paginated(
        status=appt_status, page=page, page_size=page_size
    )
    docs = listing["items"]
    ids = []
    for doc in docs:
        ids.extend([doc.get("lawyer_id"), doc.get("client_id")])
    names = {str(u["_id"]): u.get("name", "") for u in await UserRepository(db).find_by_ids(ids)}
    items = [serialize_appointment_item(doc, names) for doc in docs]
    return {
        "items": items,
        "total": listing["total"],
        "page": page,
        "page_size": page_size,
    }


@router.get("/complaints")
async def admin_list_complaints(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
    complaint_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = ComplaintRepository(db)
    status_enum = (
        ComplaintStatus(complaint_status)
        if complaint_status in {c.value for c in ComplaintStatus}
        else None
    )
    result = await repo.list_all(status=status_enum, page=page, page_size=page_size)
    user_ids = {c["user_id"] for c in result["items"]}
    user_ids.update(
        c["target_user_id"] for c in result["items"] if c.get("target_user_id")
    )
    users = await UserRepository(db).find_by_ids(list(user_ids))
    user_map = {str(u["_id"]): u for u in users}
    items = []
    for c in result["items"]:
        d = dict(c)
        d["id"] = str(d["_id"])
        d.pop("_id", None)
        reporter = user_map.get(d["user_id"], {})
        d["user_name"] = reporter.get("name", "")
        d["user_email"] = reporter.get("email", "")
        target = user_map.get(d.get("target_user_id") or "", {})
        d["target_user_name"] = target.get("name", "")
        d["target_user_email"] = target.get("email", "")
        items.append(d)
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.patch("/complaints/{complaint_id}")
async def admin_respond_complaint(
    complaint_id: str,
    payload: AdminComplaintResponsePayload,
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    repo = ComplaintRepository(db)
    complaint = await repo.find_by_id(complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    updated = await repo.respond(
        complaint_id,
        payload.status,
        admin_note=payload.admin_note,
        reporter_response=payload.reporter_response,
        reported_response=payload.reported_response,
    )
    await _audit(
        db,
        admin["id"],
        "complaint.respond",
        "complaint",
        complaint_id,
        {
            "status": payload.status.value,
            "reporter_response": bool(payload.reporter_response),
            "reported_response": bool(payload.reported_response),
        },
    )
    notifications = NotificationRepository(db)
    await notifications.create(
        user_id=complaint["user_id"],
        notification_type="COMPLAINT",
        title="Complaint updated",
        message=f"Your complaint status is now {payload.status.value}.",
        data={"complaint_id": complaint_id},
    )
    if payload.reporter_response:
        await notifications.create(
            user_id=complaint["user_id"],
            notification_type="COMPLAINT",
            title="Response to your complaint",
            message="An administrator replied to your complaint.",
            data={"complaint_id": complaint_id, "direction": "reporter"},
        )
    if payload.reported_response and complaint.get("target_user_id"):
        await notifications.create(
            user_id=complaint["target_user_id"],
            notification_type="COMPLAINT",
            title="A complaint about you was reviewed",
            message="An administrator left a response regarding a complaint about you.",
            data={"complaint_id": complaint_id, "direction": "reported"},
        )
    d = dict(updated)
    d["id"] = str(d["_id"])
    d.pop("_id", None)
    return d


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def admin_analytics(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    users_repo = UserRepository(db)
    lawyers_repo = LawyerRepository(db)
    appts_repo = AppointmentRepository(db)
    complaints_repo = ComplaintRepository(db)

    users_by_role = {}
    for r in UserRole:
        users_by_role[r.value] = await users_repo.count_by_role(r)

    appointments_by_status = {}
    for s in AppointmentStatus:
        appointments_by_status[s.value] = await appts_repo.count_by_status(s)

    lawyers_by_status = {}
    for s in LawyerStatus:
        lawyers_by_status[s.value] = await lawyers_repo.count_by_status(s)

    complaints_by_status = {}
    for s in ComplaintStatus:
        complaints_by_status[s.value] = await complaints_repo.count_by_status(s)

    month_items = await appts_repo.count_by_month(limit=60)

    category_items = await lawyers_repo.category_counts(limit=8)

    top_lawyer_docs = await lawyers_repo.top_rated(limit=5)
    users = await users_repo.find_by_ids([p["user_id"] for p in top_lawyer_docs])
    user_map = {str(u["_id"]): u for u in users}
    top_lawyers = [
        {
            "name": user_map.get(p["user_id"], {}).get("name", ""),
            "avg_rating": p.get("avg_rating", 0),
            "rating_count": p.get("rating_count", 0),
            "categories": p.get("categories", []),
        }
        for p in top_lawyer_docs
    ]

    revenue_by_source = await RevenueRepository(db).total_by_source()

    return AdminAnalyticsResponse(
        users_by_role=users_by_role,
        appointments_by_status=appointments_by_status,
        lawyers_by_status=lawyers_by_status,
        complaints_by_status=complaints_by_status,
        appointments_by_month=month_items,
        top_categories=category_items,
        top_lawyers=top_lawyers,
        revenue_by_source=revenue_by_source,
    )


@router.get("/audit-logs", response_model=AdminAuditLogsResponse)
async def admin_audit_logs(
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
    actor_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = AuditLogRepository(db)
    result = await repo.list_all(
        actor_id=actor_id or None,
        entity_type=entity_type or None,
        page=page,
        page_size=page_size,
    )
    actor_ids = {a.get("actor_id") for a in result["items"] if a.get("actor_id")}
    users = await UserRepository(db).find_by_ids(list(actor_ids))
    name_map = {str(u["_id"]): u.get("name", "") for u in users}
    items = [serialize_audit_item(a, name_map) for a in result["items"]]
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


_REPORT_TYPES = {"users", "lawyers", "appointments", "complaints", "revenue"}


async def _build_report_summary(
    db: AsyncSession, report_type: str
) -> dict:
    summary: dict = {}
    if report_type == "users":
        users_repo = UserRepository(db)
        summary["total"] = await users_repo.count_all()
        summary["by_role"] = {
            r.value: await users_repo.count_by_role(r) for r in UserRole
        }
    elif report_type == "lawyers":
        lawyers_repo = LawyerRepository(db)
        summary["total"] = await lawyers_repo.count_all()
        summary["by_status"] = {
            s.value: await lawyers_repo.count_by_status(s) for s in LawyerStatus
        }
    elif report_type == "appointments":
        appts_repo = AppointmentRepository(db)
        summary["total"] = await appts_repo.count_all()
        summary["by_status"] = {
            s.value: await appts_repo.count_by_status(s) for s in AppointmentStatus
        }
    elif report_type == "complaints":
        complaints_repo = ComplaintRepository(db)
        summary["total"] = await complaints_repo.count_all()
        summary["by_status"] = {
            s.value: await complaints_repo.count_by_status(s) for s in ComplaintStatus
        }
    elif report_type == "revenue":
        revenue_repo = RevenueRepository(db)
        summary["total_revenue"] = await revenue_repo.total()
        summary["by_source"] = await revenue_repo.total_by_source()
    return summary


@router.get("/reports/{report_type}", response_model=AdminReportResponse)
async def admin_report(
    report_type: str,
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    if report_type not in _REPORT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown report type")

    from datetime import datetime, timezone

    summary = await _build_report_summary(db, report_type)
    await _audit(db, admin["id"], "report.generate", "report", report_type)
    return AdminReportResponse(
        report_type=report_type,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
    )


@router.get("/reports/{report_type}/download")
async def admin_report_download(
    report_type: str,
    admin: AdminDep,
    db: AsyncSession = Depends(require_db),
):
    if report_type not in _REPORT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown report type")

    from datetime import datetime, timezone

    summary = await _build_report_summary(db, report_type)
    await _audit(db, admin["id"], "report.download", "report", report_type)
    pdf = build_admin_report_pdf(
        {
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc),
            "summary": summary,
        }
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report_type}-report.pdf"'
        },
    )
