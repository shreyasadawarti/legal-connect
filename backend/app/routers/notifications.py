from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, require_db
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationResponse, serialize_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = NotificationRepository(db)
    result = await repo.list_for_user(user["id"], page=page, page_size=page_size)
    return {
        "items": [serialize_notification(doc) for doc in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "unread": await repo.count_unread(user["id"]),
    }


@router.get("/unread-count")
async def unread_count(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    repo = NotificationRepository(db)
    return {"unread": await repo.count_unread(user["id"])}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    repo = NotificationRepository(db)
    updated = await repo.mark_read(notification_id, user["id"])
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    doc = await repo.find_by_id(notification_id, user["id"])
    return NotificationResponse.model_validate(serialize_notification(doc))


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    await NotificationRepository(db).mark_all_read(user["id"])


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    await NotificationRepository(db).delete(notification_id, user["id"])

