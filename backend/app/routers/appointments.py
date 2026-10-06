from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _participant_map(db: AsyncSession, ids: list[str]) -> dict[str, dict]:
    """Name, picture, phone and city for the given user ids."""
    if not ids:
        return {}
    users = await UserRepository(db).find_by_ids(list(set(ids)))
    return {
        str(u["_id"]): {
            "name": u.get("name", ""),
            "profile_picture_url": u.get("profile_picture_url"),
            "phone": u.get("phone"),
            "city": u.get("city"),
        }
        for u in users
    }


async def _to_response(
    db: AsyncSession, doc: dict, viewer_id: str
) -> dict:
    info = await _participant_map(db, [doc["lawyer_id"], doc["client_id"]])
    lawyer = info.get(doc["lawyer_id"], {})
    client = info.get(doc["client_id"], {})
    result = serialize_appointment(doc)
    result["lawyer_name"] = lawyer.get("name", "")
    result["client_name"] = client.get("name", "")
    # Citizen contact details exist for the assigned lawyer only. A citizen
    # reading their own appointment already has this data on their profile, so
    # withholding it here keeps the rule simple: it never travels to anyone who
    # is not the lawyer handling the request.
    if viewer_id == doc["lawyer_id"]:
        result["client_profile_picture_url"] = client.get("profile_picture_url")
        result["client_phone"] = client.get("phone")
        result["client_city"] = client.get("city")
    return result


async def _notify(
    db: AsyncSession,
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
    db: AsyncSession, appointment_id: str, user_id: str
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
    db: AsyncSession = Depends(require_db),
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
    return await _to_response(db, appointment, user["id"])


@router.get("")
async def list_appointments(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
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
    participants = await _participant_map(db, ids)
    items = []
    for doc in result["items"]:
        lawyer = participants.get(doc["lawyer_id"], {})
        client = participants.get(doc["client_id"], {})
        r = serialize_appointment(doc)
        r["lawyer_name"] = lawyer.get("name", "")
        r["client_name"] = client.get("name", "")
        if as_lawyer:
            r["client_profile_picture_url"] = client.get("profile_picture_url")
            r["client_phone"] = client.get("phone")
            r["client_city"] = client.get("city")
        items.append(r)
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    appointment = await _get_participant_appointment(db, appointment_id, user["id"])
    return await _to_response(db, appointment, user["id"])


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
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
    return await _to_response(db, updated, user["id"])


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: str,
    payload: AppointmentReschedule,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
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
    return await _to_response(db, updated, user["id"])


async def _require_lawyer(
    db: AsyncSession, appointment: dict, user_id: str
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
    db: AsyncSession = Depends(require_db),
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
    return await _to_response(db, updated, user["id"])


@router.patch("/{appointment_id}/reject", response_model=AppointmentResponse)
async def reject_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
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
    return await _to_response(db, updated, user["id"])


@router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
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
    return await _to_response(db, updated, user["id"])

