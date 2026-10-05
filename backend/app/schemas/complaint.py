from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.platform import ComplaintStatus, NotificationType


class ComplaintCreate(BaseModel):
    subject: str
    description: str
    related_appointment_id: Optional[str] = None


class ComplaintResponse(BaseModel):
    id: str
    user_id: str
    subject: str
    description: str
    related_appointment_id: Optional[str] = None
    status: ComplaintStatus = ComplaintStatus.OPEN
    admin_note: Optional[str] = None
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
