from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.platform import PaymentStatus


class PaymentCreate(BaseModel):
    appointment_id: str
    amount: float = Field(gt=0)


class PaymentResponse(BaseModel):
    id: str
    appointment_id: str
    payee_id: str
    amount: float
    status: PaymentStatus = PaymentStatus.PENDING
    reference: str = ""
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def serialize_payment(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc
