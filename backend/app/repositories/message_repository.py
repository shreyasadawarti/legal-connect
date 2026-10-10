from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import id_to_datetime, utcnow
from app.db.models import Message
from app.db.serialize import message_to_doc

COLLECTION = "messages"


class MessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        conversation_id: str,
        sender_id: str,
        recipient_id: str,
        content: str,
        message_type: str = "text",
        is_read: bool = False,
    ) -> dict[str, Any]:
        row = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            message_type=message_type,
            is_read=is_read,
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return message_to_doc(row)

    async def list_for_conversation(
        self,
        conversation_id: str,
        before: Optional[str] = None,
        page_size: int = 50,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Newest page of a conversation, returned oldest-first for rendering.

        `before` is the id of the oldest message already on screen. Its embedded
        timestamp still works as a cursor because identifiers keep the
        ObjectId layout, so existing clients keep working unchanged. `since`
        excludes messages at or before a per-user "clear history" cutoff.
        """
        filters = [Message.conversation_id == conversation_id]
        cursor_time = id_to_datetime(before) if before else None
        if cursor_time is not None:
            filters.append(Message.created_at < cursor_time)
        if since is not None:
            filters.append(Message.created_at > since)

        result = await self.db.execute(
            select(Message)
            .where(*filters)
            .order_by(Message.created_at.desc())
            .limit(page_size)
        )
        items = [message_to_doc(row) for row in result.scalars()]
        items.reverse()
        return {"items": items, "has_more": len(items) == page_size}

    async def count_unread(self, conversation_id: str, user_id: str) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.recipient_id == user_id,
                    Message.is_read.is_(False),
                )
            )
        ).scalar_one()

    async def mark_read(
        self, conversation_id: str, user_id: str, before_id: Optional[str] = None
    ) -> None:
        # A CHOose(24) comparison reproduces the ObjectId `<=` comparison the
        # previous implementation used, because identifiers stay monotonic.
        filters = [
            Message.conversation_id == conversation_id,
            Message.recipient_id == user_id,
            Message.is_read.is_(False),
        ]
        if before_id:
            filters.append(Message.id <= before_id)
        # Reading a message implies it was delivered first, so fill both columns
        # in one statement and leave an already-set delivered_at untouched.
        await self.db.execute(
            update(Message)
            .where(*filters)
            .values(is_read=True, delivered_at=func.coalesce(Message.delivered_at, utcnow()))
        )
        await self.db.flush()

    async def mark_one_read(self, message_id: str) -> None:
        await self.db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(is_read=True, delivered_at=func.coalesce(Message.delivered_at, utcnow()))
        )
        await self.db.flush()

    async def mark_delivered(self, conversation_id: str, user_id: str) -> int:
        """Mark the recipient's undelivered messages in one conversation delivered.

        Returns how many rows were affected so the caller can decide whether a
        real-time `delivered` event is worth broadcasting.
        """
        result = await self.db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.recipient_id == user_id,
                Message.delivered_at.is_(None),
            )
            .values(delivered_at=utcnow())
        )
        await self.db.flush()
        return result.rowcount or 0

    async def mark_all_delivered_for_recipient(
        self, user_id: str
    ) -> list[tuple[str, str]]:
        """Catch-up delivery for a recipient who just came online.

        Every message already waiting for them is now available, so all of it is
        marked delivered at once. Returns the distinct `(sender_id,
        conversation_id)` pairs that changed, so each sender can be told which
        conversations to refresh their ticks for.
        """
        pending = (
            select(Message.sender_id, Message.conversation_id)
            .where(
                Message.recipient_id == user_id,
                Message.delivered_at.is_(None),
            )
            .distinct()
        )
        rows = (await self.db.execute(pending)).all()
        if not rows:
            return []
        await self.db.execute(
            update(Message)
            .where(
                Message.recipient_id == user_id,
                Message.delivered_at.is_(None),
            )
            .values(delivered_at=utcnow())
        )
        await self.db.flush()
        return [(row.sender_id, row.conversation_id) for row in rows]

    async def move_conversation(
        self, from_conversation_id: str, to_conversation_id: str
    ) -> None:
        await self.db.execute(
            update(Message)
            .where(Message.conversation_id == from_conversation_id)
            .values(conversation_id=to_conversation_id)
        )
        await self.db.flush()