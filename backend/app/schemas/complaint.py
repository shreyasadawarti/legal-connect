from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.platform import ComplaintStatus


class ComplaintCreate(BaseModel):
    subject: str
    description: str
    related_appointment_id: Optional[str] = None
    target_user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    category: Optional[str] = None


class ComplaintResponse(BaseModel):
    id: str
    user_id: str
    subject: str
    description: str
    related_appointment_id: Optional[str] = None
    target_user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    category: Optional[str] = None
    status: ComplaintStatus = ComplaintStatus.OPEN
    admin_note: Optional[str] = None
    reporter_response: Optional[str] = None
    reporter_responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintAgainstMeResponse(BaseModel):
    """The reported party's view: no reporter identity and no reporter reply."""

    id: str
    subject: str
    description: str
    category: Optional[str] = None
    status: ComplaintStatus = ComplaintStatus.OPEN
    reported_response: Optional[str] = None
    reported_responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintResolve(BaseModel):
    status: ComplaintStatus = ComplaintStatus.RESOLVED
    admin_note: Optional[str] = None


def serialize_complaint(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc


def serialize_complaint_for_reporter(doc: dict[str, Any]) -> dict[str, Any]:
    """Reporter's view: their own complaint plus the reply addressed to them."""
    data = serialize_complaint(doc)
    for key in ("reported_response", "reported_responded_at"):
        data.pop(key, None)
    return data


def serialize_complaint_for_target(doc: dict[str, Any]) -> dict[str, Any]:
    """Reported party's view: anonymised details plus the reply addressed to them."""
    data = serialize_complaint(doc)
    return {
        "id": data.get("id"),
        "subject": data.get("subject"),
        "description": data.get("description"),
        "category": data.get("category"),
        "status": data.get("status"),
        "reported_response": data.get("reported_response"),
        "reported_responded_at": data.get("reported_responded_at"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }
