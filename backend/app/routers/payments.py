import json
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import CurrentUser, get_payment_gateway, require_db
from app.models.platform import AppointmentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payment import (
    PaymentOrderRequest,
    PaymentOrderResponse,
    PaymentResponse,
    PaymentVerifyRequest,
    serialize_payment,
)
from app.services.payment_gateway import PaymentGatewayError, PaymentGatewayNotConfigured
from app.services.pdf_service import build_payment_receipt_pdf

router = APIRouter(prefix="/payments", tags=["payments"])

BILLABLE_STATUSES = {AppointmentStatus.CONFIRMED.value, AppointmentStatus.COMPLETED.value}


async def _require_appointment(db: AsyncSession, appointment_id: str) -> dict:
    appointment = await AppointmentRepository(db).find_by_id(appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )
    return appointment


async def _compute_amount(db: AsyncSession, appointment: dict) -> Decimal:
    """Bill the lawyer's hourly rate for the appointment's scheduled duration.

    The amount is always derived here, never accepted from the browser, so a
    client cannot pay less (or the platform record a different figure) than the
    consultation actually costs.
    """
    profile = await LawyerRepository(db).find_by_user_id(appointment["lawyer_id"])
    rate = (profile or {}).get("hourly_rate") or 0
    hours = (
        appointment["end_time"] - appointment["start_time"]
    ).total_seconds() / 3600
    if not rate or hours <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This appointment does not have a billable amount",
        )
    return (Decimal(str(rate)) * Decimal(str(hours))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


@router.post("/order", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    payload: PaymentOrderRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    gateway=Depends(get_payment_gateway),
):
    appointment = await _require_appointment(db, payload.appointment_id)
    if appointment["client_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the client can pay for this appointment",
        )
    if appointment["status"] not in BILLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment cannot be paid for in its current state",
        )

    payments = PaymentRepository(db)
    existing = await payments.find_latest_for_appointment(payload.appointment_id)
    if existing and existing["status"] == "PAID":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment has already been paid for",
        )

    amount = await _compute_amount(db, appointment)
    payment = await payments.create_pending(
        appointment_id=payload.appointment_id,
        payee_id=user["id"],
        amount=amount,
    )

    try:
        order = await gateway.create_order(
            amount_paise=int(amount * 100),
            receipt=payment["reference"],
            notes={"appointment_id": payload.appointment_id},
        )
    except PaymentGatewayNotConfigured as exc:
        await payments.mark_failed(payment["_id"])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except PaymentGatewayError as exc:
        await payments.mark_failed(payment["_id"])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    order_id = order.get("id")
    if not order_id:
        await payments.mark_failed(payment["_id"])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment gateway returned an invalid order",
        )
    await payments.attach_order(payment["_id"], order_id)

    return PaymentOrderResponse(
        payment_id=payment["_id"],
        appointment_id=payload.appointment_id,
        order_id=order_id,
        amount=float(amount),
        amount_paise=int(amount * 100),
        key_id=settings.razorpay_key_id,
        reference=payment["reference"],
    )


@router.post("/verify", response_model=PaymentResponse)
async def verify_payment(
    payload: PaymentVerifyRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    gateway=Depends(get_payment_gateway),
):
    payments = PaymentRepository(db)
    payment = await payments.find_by_id(payload.payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    if payment["payee_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the payee can confirm this payment",
        )
    if payment["status"] == "PAID":
        return serialize_payment(payment)

    if not payment.get("gateway_order_id") or payment["gateway_order_id"] != payload.razorpay_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment order does not match",
        )

    if not gateway.verify_payment_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )

    updated = await payments.mark_paid(
        payload.payment_id,
        gateway_payment_id=payload.razorpay_payment_id,
        gateway_signature=payload.razorpay_signature,
    )
    await _notify_payment_received(db, updated)
    return serialize_payment(updated)


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(require_db),
    gateway=Depends(get_payment_gateway),
):
    """Razorpay server-to-server callback.

    The signature is verified against the raw body, so an unauthenticated
    caller cannot forge a capture. Unknown orders are acknowledged but ignored,
    which keeps the endpoint safe to receive retries.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not gateway.verify_webhook_signature(body=body, signature=signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    try:
        event = json.loads(body or b"{}")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload"
        )

    event_type = event.get("event", "")
    entity = (event.get("payload", {}).get("payment", {}) or {}).get("entity", {}) or {}
    order_id = entity.get("order_id")
    if not order_id:
        return {"status": "ignored"}

    payments = PaymentRepository(db)
    payment = await payments.find_by_order_id(order_id)
    if payment is None or payment["status"] == "PAID":
        return {"status": "ok"}

    if event_type in {"payment.captured", "order.paid"}:
        updated = await payments.mark_paid(
            payment["_id"], gateway_payment_id=entity.get("id")
        )
        await _notify_payment_received(db, updated)
    elif event_type == "payment.failed":
        await payments.mark_failed(payment["_id"])

    return {"status": "ok"}


async def _notify_payment_received(db: AsyncSession, payment: dict) -> None:
    if not payment:
        return
    appointment = await AppointmentRepository(db).find_by_id(payment["appointment_id"]) or {}
    if appointment.get("lawyer_id"):
        await NotificationRepository(db).create(
            user_id=appointment["lawyer_id"],
            notification_type="PAYMENT",
            title="Payment received",
            message=f"Payment of ₹{payment['amount']:.2f} received for an appointment.",
            data={"appointment_id": payment["appointment_id"]},
        )


@router.get("/appointment/{appointment_id}")
async def get_appointment_payment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    appointment = await _require_appointment(db, appointment_id)
    if user["id"] not in {appointment["client_id"], appointment["lawyer_id"]}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this appointment",
        )
    payment = await PaymentRepository(db).find_latest_for_appointment(appointment_id)
    return {"payment": serialize_payment(payment) if payment else None}


@router.get("")
async def list_payments(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    payments = PaymentRepository(db)
    result = await payments.list_for_payee(user["id"], page=page, page_size=page_size)
    return {
        "items": [serialize_payment(doc) for doc in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/{payment_id}/receipt")
async def download_receipt(
    payment_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    payments = PaymentRepository(db)
    payment = await payments.find_by_id(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    if payment.get("payee_id") != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the payee can download this receipt",
        )

    appointments = AppointmentRepository(db)
    appointment = await appointments.find_by_id(payment["appointment_id"]) or {}
    ids = [appointment.get("client_id"), appointment.get("lawyer_id")]
    users = await UserRepository(db).find_by_ids([i for i in ids if i])
    name_map = {str(u["_id"]): u.get("name", "") for u in users}

    invoice = {
        "reference": payment.get("reference", payment_id),
        "payee_name": name_map.get(payment.get("payee_id", ""), ""),
        "lawyer_name": name_map.get(appointment.get("lawyer_id", ""), ""),
        "category": appointment.get("category", "other"),
        "start_time": appointment.get("start_time"),
        "end_time": appointment.get("end_time"),
        "amount": payment.get("amount", 0),
        "status": payment.get("status", ""),
        "created_at": payment.get("created_at"),
    }

    pdf = build_payment_receipt_pdf(invoice)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="receipt-{payment_id}.pdf"'
        },
    )
