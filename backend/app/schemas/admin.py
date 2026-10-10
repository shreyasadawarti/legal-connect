from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.platform import ComplaintStatus
from app.models.user import LawyerStatus, UserRole, UserStatus


class AdminDashboardResponse(BaseModel):
    total_users: int
    total_lawyers: int
    total_appointments: int
    pending_verifications: int
    open_complaints: int
    total_revenue: float


class AdminUsersResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class AdminUserStatusRequest(BaseModel):
    status: UserStatus


class AdminVerificationRequest(BaseModel):
    status: LawyerStatus
    note: Optional[str] = None


class AdminComplaintResponsePayload(BaseModel):
    status: ComplaintStatus
    admin_note: Optional[str] = None
    reporter_response: Optional[str] = None
    reported_response: Optional[str] = None


class AdminAnalyticsResponse(BaseModel):
    users_by_role: dict[str, int]
    appointments_by_status: dict[str, int]
    lawyers_by_status: dict[str, int]
    complaints_by_status: dict[str, int]
    appointments_by_month: list[dict[str, Any]]
    top_categories: list[dict[str, Any]]
    top_lawyers: list[dict[str, Any]]
    revenue_by_source: dict[str, float]


class AdminAppointmentsResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class AdminAuditLogsResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class AdminReportResponse(BaseModel):
    report_type: str
    generated_at: datetime
    summary: dict[str, Any]


def serialize_user_item(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


def serialize_audit_item(
    doc: dict[str, Any], actor_names: dict[str, str]
) -> dict[str, Any]:
    d = dict(doc)
    d["id"] = str(d.get("_id", ""))
    d.pop("_id", None)
    d["actor_name"] = actor_names.get(d.get("actor_id", ""), d.get("actor_id", ""))
    return d


def serialize_appointment_item(
    doc: dict[str, Any], names: dict[str, str]
) -> dict[str, Any]:
    d = dict(doc)
    d["id"] = str(d.pop("_id", ""))
    d["lawyer_name"] = names.get(d.get("lawyer_id", ""), "")
    d["client_name"] = names.get(d.get("client_id", ""), "")
    return d
