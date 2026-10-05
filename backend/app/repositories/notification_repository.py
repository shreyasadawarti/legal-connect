from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Notification
from app.db.serialize import notification_to_doc

COLLECTION = "notifications"


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        row = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data,
            is_read=False,
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return notification_to_doc(row)

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        total = (
            await self.db.execute(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id)
            )
        ).scalar_one()
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [notification_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def count_unread(self, user_id: str) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
        ).scalar_one()

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Return True only when an unread row was actually flipped.

        The `is_read = False` guard reproduces MongoDB's `modified_count`
        semantics: a notification that was already read reports False.
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return bool(result.rowcount)

    async def find_by_id(
        self, notification_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        row = result.scalar_one_or_none()
        return notification_to_doc(row) if row else None

    async def mark_all_read(self, user_id: str) -> None:
        await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
            .values(is_read=True)
        )
        await self.db.flush()

    async def delete(self, notification_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.flush()
        return True