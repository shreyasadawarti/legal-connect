from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import UserBlock


class UserBlockRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def block(self, blocker_id: str, blocked_id: str) -> None:
        """Record that `blocker_id` has blocked `blocked_id`; idempotent."""
        try:
            async with self.db.begin_nested():
                self.db.add(
                    UserBlock(
                        blocker_id=blocker_id,
                        blocked_id=blocked_id,
                        created_at=utcnow(),
                    )
                )
                await self.db.flush()
        except IntegrityError:
            # Already blocked -- the composite primary key rejected the duplicate.
            pass

    async def unblock(self, blocker_id: str, blocked_id: str) -> None:
        await self.db.execute(
            delete(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        await self.db.flush()

    async def is_blocked(self, blocker_id: str, blocked_id: str) -> bool:
        result = await self.db.execute(
            select(UserBlock.blocker_id)
            .where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def either_blocked(self, user_a: str, user_b: str) -> bool:
        """True when either user has blocked the other."""
        result = await self.db.execute(
            select(UserBlock.blocker_id)
            .where(
                or_(
                    (UserBlock.blocker_id == user_a) & (UserBlock.blocked_id == user_b),
                    (UserBlock.blocker_id == user_b) & (UserBlock.blocked_id == user_a),
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def list_blocked_ids(self, user_id: str) -> list[str]:
        result = await self.db.execute(
            select(UserBlock.blocked_id).where(UserBlock.blocker_id == user_id)
        )
        return list(result.scalars())

    async def list_blocked(self, user_id: str) -> list[dict[str, Any]]:
        return [{"id": blocked_id} for blocked_id in await self.list_blocked_ids(user_id)]
