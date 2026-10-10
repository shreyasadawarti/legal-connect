from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, require_db, require_roles
from app.models.platform import ComplaintStatus
from app.models.user import UserRole
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.complaint import (
    ComplaintAgainstMeResponse,
    ComplaintCreate,
    ComplaintResolve,
    ComplaintResponse,
    serialize_complaint,
    serialize_complaint_for_reporter,
    serialize_complaint_for_target,
)

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    payload: ComplaintCreate,
    user: CurrentUser,
    _: Annotated[dict, Depends(require_roles(UserRole.USER, UserRole.LAWYER))],
    db: AsyncSession = Depends(require_db),
):
    # Both roles may report. The party being reported is always derived from a source
    # the caller provably belongs to -- a chat conversation or an appointment they are
    # part of -- so a client can never name an unrelated user as the target. When a
    # conversation is given the counterpart is taken from it; otherwise the linked
    # appointment is verified and its other participant becomes the target.
    target_user_id = payload.target_user_id

    if payload.conversation_id:
        conversation = await ConversationRepository(db).find_by_id(
            payload.conversation_id
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
        participants = conversation.get("participants", [])
        if user["id"] not in participants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only report someone you have a conversation with",
            )
        counterpart = next((p for p in participants if p != user["id"]), None)
        if counterpart is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation has no other participant",
            )
        target_user_id = counterpart
    elif payload.related_appointment_id:
        appointment = await AppointmentRepository(db).find_by_id(
            payload.related_appointment_id
        )
        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
            )
        if user["id"] not in (appointment["client_id"], appointment["lawyer_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only report someone you have an appointment with",
            )
        target_user_id = (
            appointment["lawyer_id"]
            if user["id"] == appointment["client_id"]
            else appointment["client_id"]
        )
    elif payload.target_user_id:
        if payload.target_user_id == user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot report yourself",
            )
        target = await UserRepository(db).find_by_id(payload.target_user_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

    repo = ComplaintRepository(db)
    doc = await repo.create(
        user_id=user["id"],
        subject=payload.subject,
        description=payload.description,
        related_appointment_id=payload.related_appointment_id,
        target_user_id=target_user_id,
        conversation_id=payload.conversation_id,
        category=payload.category,
    )
    await NotificationRepository(db).create(
        user_id=user["id"],
        notification_type="COMPLAINT",
        title="Complaint received",
        message="We have received your complaint and will review it shortly.",
        data={"complaint_id": str(doc["_id"])},
    )
    return ComplaintResponse.model_validate(serialize_complaint(doc))


@router.get("")
async def list_my_complaints(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = ComplaintRepository(db)
    result = await repo.list_for_user(user["id"], page=page, page_size=page_size)
    return {
        "items": [
            serialize_complaint_for_reporter(doc) for doc in result["items"]
        ],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/received")
async def list_complaints_against_me(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Complaints where the caller is the reported party.

    Only the reply addressed to the reported party is exposed; the reporter's
    identity and their reply are never serialised here.
    """
    repo = ComplaintRepository(db)
    result = await repo.list_for_target(user["id"], page=page, page_size=page_size)
    items = [
        ComplaintAgainstMeResponse.model_validate(
            serialize_complaint_for_target(doc)
        ).model_dump()
        for doc in result["items"]
    ]
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/all")
async def list_all_complaints(
    _: Annotated[dict, Depends(require_roles(UserRole.ADMIN))],
    db: AsyncSession = Depends(require_db),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    comp_status = None
    if status_filter:
        try:
            comp_status = ComplaintStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {status_filter}",
            ) from exc
    repo = ComplaintRepository(db)
    result = await repo.list_all(status=comp_status, page=page, page_size=page_size)
    return {
        "items": [serialize_complaint(doc) for doc in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.patch("/{complaint_id}/resolve", response_model=ComplaintResponse)
async def resolve_complaint(
    complaint_id: str,
    payload: ComplaintResolve,
    _: Annotated[dict, Depends(require_roles(UserRole.ADMIN))],
    db: AsyncSession = Depends(require_db),
):
    repo = ComplaintRepository(db)
    complaint = await repo.find_by_id(complaint_id)
    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )
    updated = await repo.update_status(
        complaint_id, payload.status, payload.admin_note
    )
    if updated and complaint.get("user_id"):
        await NotificationRepository(db).create(
            user_id=complaint["user_id"],
            notification_type="COMPLAINT",
            title="Complaint update",
            message=f"Your complaint was updated to {payload.status.value}.",
            data={"complaint_id": complaint_id},
        )
    return ComplaintResponse.model_validate(serialize_complaint(updated))

