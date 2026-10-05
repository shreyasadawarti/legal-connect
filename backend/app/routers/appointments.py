from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import CurrentUser, require_db
from app.models.platform import AppointmentStatus, NotificationType
from app.models.user import LawyerStatus, UserRole
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentResponse,
    serialize_appointment,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def _name_map(db: AsyncIOMotorDatabase, ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    users = await UserRepository(db).find_by_ids(list(set(ids)))
    return {str(u["_id"]): u.get("name", "") for u in users}


async def _to_response(
    db: AsyncIOMotorDatabase, doc: dict
) -> dict:
    names = await _name_map(db, [doc["lawyer_id"], doc["client_id"]])
    result = serialize_appointment(doc)
    result["lawyer_name"] = names.get(doc["lawyer_id"], "")
    result["client_name"] = names.get(doc["client_id"], "")
    return result


async def _notify(
    db: AsyncIOMotorDatabase,
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    data: dict | None = None,
) -> None:
    await NotificationRepository(db).create(
        user_id=user_id,
        notification_type=notification_type.value,
        title=title,
        message=message,
        data=data,
    )


async def _get_participant_appointment(
    db: AsyncIOMotorDatabase, appointment_id: str, user_id: str
) -> dict:
    appointments = AppointmentRepository(db)
    appointment = await appointments.find_by_id(appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )
    if appointment["client_id"] != user_id and appointment["lawyer_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant in this appointment"
        )
    return appointment


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    payload: AppointmentCreate,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    if user["id"] == payload.lawyer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot book an appointment with yourself",
        )
    profiles = LawyerRepository(db)
    lawyer_profile = await profiles.find_by_user_id(payload.lawyer_id)
    if lawyer_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer profile not found"
        )
    if lawyer_profile.get("verification_status") != LawyerStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This lawyer is not yet verified to accept appointments",
        )

    appointments = AppointmentRepository(db)
    conflicts = await appointments.find_conflicts(
        lawyer_id=payload.lawyer_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The lawyer already has an appointment in that time slot",
        )

    appointment = await appointments.create(
        lawyer_id=payload.lawyer_id,
        client_id=user["id"],
        category=payload.category.value,
        start_time=payload.start_time,
        end_time=payload.end_time,
        description=payload.description,
    )
    lawyer_user = await UserRepository(db).find_by_id(payload.lawyer_id)
    await _notify(
        db,
        payload.lawyer_id,
        NotificationType.APPOINTMENT,
        "New appointment request",
        f"{user['name']} requested an appointment.",
        {"appointment_id": str(appointment["_id"])},
    )
    return await _to_response(db, appointment)


@router.get("")
async def list_appointments(
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    appointments = AppointmentRepository(db)
    appt_status = None
    if status_filter:
        try:
            appt_status = AppointmentStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {status_filter}",
            ) from exc
    as_lawyer = user["role"] == UserRole.LAWYER.value
    result = await appointments.list_for_user(
        user["id"], as_lawyer=as_lawyer, status=appt_status, page=page, page_size=page_size
    )
    ids = []
    for doc in result["items"]:
        ids.extend([doc["lawyer_id"], doc["client_id"]])
    names = await _name_map(db, ids)
    items = []
    for doc in result["items"]:
        r = serialize_appointment(doc)
        r["lawyer_name"] = names.get(doc["lawyer_id"], "")
        r["client_name"] = names.get(doc["client_id"], "")
        items.append(r)
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    return await _to_response(db, appointment)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    appointments = AppointmentRepository(db)
    if appointment["status"] not in (
        AppointmentStatus.PENDING.value,
        AppointmentStatus.CONFIRMED.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or confirmed appointments can be cancelled",
        )
    updated = await appointments.update_status(appointment_id, AppointmentStatus.CANCELLED)
    other = appointment["lawyer_id"] if appointment["client_id"] == user["id"] else appointment["client_id"]
    await _notify(
        db, other, NotificationType.APPOINTMENT, "Appointment cancelled",
        f"An appointment was cancelled by {user['name']}.",
        {"appointment_id": appointment_id},
    )
    return await _to_response(db, updated)


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: str,
    payload: AppointmentReschedule,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    appointments = AppointmentRepository(db)
    conflicts = await appointments.find_conflicts(
        lawyer_id=appointment["lawyer_id"],
        start_time=payload.start_time,
        end_time=payload.end_time,
        exclude_id=appointment_id,
    )
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The lawyer already has an appointment in that time slot",
        )
    updated = await appointments.reschedule(
        appointment_id, payload.start_time, payload.end_time
    )
    other = appointment["lawyer_id"] if appointment["client_id"] == user["id"] else appointment["client_id"]
    await _notify(
        db, other, NotificationType.APPOINTMENT, "Appointment rescheduled",
        f"An appointment was rescheduled by {user['name']}.",
        {"appointment_id": appointment_id},
    )
    return await _to_response(db, updated)


async def _require_lawyer(
    db: AsyncIOMotorDatabase, appointment: dict, user_id: str
) -> None:
    if appointment["lawyer_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the lawyer can perform this action",
        )


@router.patch("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    await _require_lawyer(db, appointment, user["id"])
    appointments = AppointmentRepository(db)
    updated = await appointments.update_status(appointment_id, AppointmentStatus.CONFIRMED)
    await _notify(
        db, appointment["client_id"], NotificationType.APPOINTMENT, "Appointment confirmed",
        "Your appointment has been confirmed.",
        {"appointment_id": appointment_id},
    )
    return await _to_response(db, updated)


@router.patch("/{appointment_id}/reject", response_model=AppointmentResponse)
async def reject_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    await _require_lawyer(db, appointment, user["id"])
    appointments = AppointmentRepository(db)
    updated = await appointments.update_status(appointment_id, AppointmentStatus.REJECTED)
    await _notify(
        db, appointment["client_id"], NotificationType.APPOINTMENT, "Appointment rejected",
        "Your appointment request was declined.",
        {"appointment_id": appointment_id},
    )
    return await _to_response(db, updated)


@router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    await _require_lawyer(db, appointment, user["id"])
    appointments = AppointmentRepository(db)
    updated = await appointments.update_status(appointment_id, AppointmentStatus.COMPLETED)
    await _notify(
        db, appointment["client_id"], NotificationType.APPOINTMENT, "Appointment completed",
        "Your appointment was marked as completed.",
        {"appointment_id": appointment_id},
    )
    return await _to_response(db, updated)

