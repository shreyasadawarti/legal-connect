from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import CurrentUser, require_db, require_roles
from app.models.platform import ComplaintStatus
from app.models.user import UserRole
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResolve,
    ComplaintResponse,
    serialize_complaint,
)

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    payload: ComplaintCreate,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    repo = ComplaintRepository(db)
    doc = await repo.create(
        user_id=user["id"],
        subject=payload.subject,
        description=payload.description,
        related_appointment_id=payload.related_appointment_id,
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
    db: AsyncIOMotorDatabase = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = ComplaintRepository(db)
    result = await repo.list_for_user(user["id"], page=page, page_size=page_size)
    return {
        "items": [serialize_complaint(doc) for doc in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/all")
async def list_all_complaints(
    _: Annotated[dict, Depends(require_roles(UserRole.ADMIN))],
    db: AsyncIOMotorDatabase = Depends(require_db),
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
    db: AsyncIOMotorDatabase = Depends(require_db),
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

