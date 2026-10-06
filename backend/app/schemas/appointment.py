from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.platform import AppointmentStatus, LegalCategory


class AppointmentCreate(BaseModel):
    lawyer_id: str
    category: LegalCategory = LegalCategory.OTHER
    start_time: datetime
    end_time: datetime
    description: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v: datetime, info) -> datetime:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class AppointmentReschedule(BaseModel):
    start_time: datetime
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v: datetime, info) -> datetime:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class AppointmentResponse(BaseModel):
    id: str
    lawyer_id: str
    lawyer_name: str = ""
    client_id: str
    client_name: str = ""
    client_profile_picture_url: Optional[str] = None
    client_phone: Optional[str] = None
    client_city: Optional[str] = None
    category: LegalCategory = LegalCategory.OTHER
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus = AppointmentStatus.PENDING
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def serialize_appointment(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc
