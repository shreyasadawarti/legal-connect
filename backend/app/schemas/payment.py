from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.platform import PaymentStatus


class PaymentOrderRequest(BaseModel):
    appointment_id: str


class PaymentOrderResponse(BaseModel):
    payment_id: str
    appointment_id: str
    order_id: str
    amount: float
    amount_paise: int
    currency: str = "INR"
    key_id: str
    reference: str
    description: str = "Legal consultation"


class PaymentVerifyRequest(BaseModel):
    payment_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentResponse(BaseModel):
    id: str
    appointment_id: str
    payee_id: str
    amount: float
    status: PaymentStatus = PaymentStatus.PENDING
    reference: str = ""
    gateway_order_id: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



def serialize_payment(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc
