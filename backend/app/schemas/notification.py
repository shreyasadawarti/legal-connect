from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.platform import NotificationType


class NotificationCreate(BaseModel):
    user_id: str
    type: NotificationType = NotificationType.SYSTEM
    title: str
    message: str
    data: Optional[dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: NotificationType = NotificationType.SYSTEM
    title: str
    message: str
    data: Optional[dict[str, Any]] = None
    is_read: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def serialize_notification(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc
