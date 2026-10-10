from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Conversation, ConversationParticipant
from app.db.serialize import conversation_to_doc

COLLECTION = "conversations"


def pair_key(participant_ids: list[str]) -> str:
    """Stable key for a participant set: sorted, de-duplicated, pipe-joined."""
    return "|".join(sorted(set(participant_ids)))


class ConversationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    @staticmethod
    def _key(participant_ids: list[str]) -> list[str]:
        return sorted(set(participant_ids))

    async def find_between(
        self,
        participant_ids: list[str],
        *,
        for_update: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Find the single direct conversation for a set of participants.

        MongoDB matched the participants array for exact equality; MySQL uses
        the UNIQUE `pair_key` column, which the schema also uses to prevent two
        direct conversations for the same pair from ever being created.

        `for_update` issues a locking read. That matters when retrying after a
        lost insert race: under InnoDB's default REPEATABLE READ a plain SELECT
        still sees the original snapshot and would not find the row the winning
        transaction just committed, whereas a locking read sees the latest
        committed version.
        """
        stmt = select(Conversation).where(Conversation.pair_key == pair_key(participant_ids))
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return conversation_to_doc(row) if row else None

    async def find_by_id(self, conversation_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        row = result.scalar_one_or_none()
        return conversation_to_doc(row) if row else None

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        # MongoDB sorted by an `updated_at` field that no conversation document
        # ever had, so the result order was effectively arbitrary. Sorting by
        # `last_message_at` is the same intent made explicit: newest activity
        # first. `create()` seeds `last_message_at`, so brand-new chats sort
        # correctly too.
        # A conversation the user deleted is hidden for them only -- a NULL
        # `hidden_at` on their participant row keeps it listed.
        is_participant = (
            select(ConversationParticipant.conversation_id)
            .where(
                ConversationParticipant.conversation_id == Conversation.id,
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.hidden_at.is_(None),
            )
            .exists()
        )
        result = await self.db.execute(
            select(Conversation)
            .where(is_participant)
            .order_by(Conversation.last_message_at.desc())
        )

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in result.scalars():
            doc = conversation_to_doc(row)
            key = pair_key(doc.get("participants", []))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(doc)

        total = len(deduped)
        start = max(page - 1, 0) * page_size
        items = deduped[start : start + page_size]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_all(self) -> list[dict[str, Any]]:
        result = await self.db.execute(select(Conversation))
        return [conversation_to_doc(row) for row in result.scalars()]

    async def delete_by_id(self, conversation_id: str) -> None:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        # Participants and messages go with it via ON DELETE CASCADE.
        await self.db.delete(row)
        await self.db.flush()

    async def create(
        self,
        participant_ids: list[str],
        type_: str = "direct",
        last_message: str = "",
    ) -> dict[str, Any]:
        now = utcnow()
        ordered = self._key(participant_ids)
        row = Conversation(
            type=type_,
            pair_key=pair_key(participant_ids),
            last_message=last_message,
            last_message_at=now,
            created_at=now,
            participants=[
                ConversationParticipant(user_id=uid, position=idx)
                for idx, uid in enumerate(ordered)
            ],
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return conversation_to_doc(row)

    async def get_or_create(
        self,
        participant_ids: list[str],
        type_: str = "direct",
        last_message: str = "",
    ) -> dict[str, Any]:
        """Return the existing conversation for these participants, or create it.

        Two concurrent requests for the same pair both find nothing and both try
        to insert; the UNIQUE `pair_key` index lets exactly one through. The
        loser rolls back to a savepoint (so earlier writes in the caller's
        transaction survive) and returns the winner's row instead of surfacing a
        500. The in-process lock in `ChatService` is only an optimisation -- it
        cannot coordinate across workers, so the database is the real guard.
        """
        existing = await self.find_between(participant_ids)
        if existing:
            return existing
        try:
            async with self.db.begin_nested():
                return await self.create(participant_ids, type_, last_message)
        except IntegrityError:
            existing = await self.find_between(participant_ids, for_update=True)
            if existing:
                return existing
            raise

    async def touch(self, conversation_id: str, last_message: str) -> None:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.last_message = last_message
        row.last_message_at = utcnow()
        await self.db.flush()

    async def get_participant_state(
        self, conversation_id: str, user_id: str
    ) -> Optional[dict[str, Any]]:
        """Per-user view state for a conversation, or None if not a participant."""
        result = await self.db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {"hidden_at": row.hidden_at, "cleared_at": row.cleared_at}

    async def set_hidden(
        self, conversation_id: str, user_id: str, hidden: bool
    ) -> None:
        """Hide (delete) or restore a conversation for one participant only."""
        await self.db.execute(
            update(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
            .values(hidden_at=utcnow() if hidden else None)
        )
        await self.db.flush()

    async def set_cleared(self, conversation_id: str, user_id: str) -> None:
        """Hide the message history up to now for one participant only."""
        await self.db.execute(
            update(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
            .values(cleared_at=utcnow())
        )
        await self.db.flush()

    async def clear_hidden_for_all(self, conversation_id: str) -> None:
        """Bring a deleted conversation back for everyone when it gets activity."""
        await self.db.execute(
            update(ConversationParticipant)
            .where(ConversationParticipant.conversation_id == conversation_id)
            .values(hidden_at=None)
        )
        await self.db.flush()