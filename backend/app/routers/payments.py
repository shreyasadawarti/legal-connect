from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import CurrentUser, require_db
from app.models.platform import PaymentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payment import PaymentCreate, PaymentResponse, serialize_payment
from app.services.pdf_service import build_payment_receipt_pdf

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointments = AppointmentRepository(db)
    appointment = await appointments.find_by_id(payload.appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )
    if appointment["client_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the client can pay for this appointment",
        )
    payments = PaymentRepository(db)
    doc = await payments.create(
        appointment_id=payload.appointment_id,
        payee_id=user["id"],
        amount=payload.amount,
        status=PaymentStatus.PAID,
    )
    await NotificationRepository(db).create(
        user_id=appointment["lawyer_id"],
        notification_type="PAYMENT",
        title="Payment received",
        message=f"Payment of {payload.amount:.2f} received for an appointment.",
        data={"appointment_id": payload.appointment_id},
    )
    return serialize_payment(doc)


@router.get("")
async def list_payments(
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
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
    db: AsyncIOMotorDatabase = Depends(require_db),
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

