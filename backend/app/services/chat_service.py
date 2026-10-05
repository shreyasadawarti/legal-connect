import asyncio
from datetime import datetime
from typing import Any

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository


class ChatService:
    def __init__(self, conversations: ConversationRepository, messages: MessageRepository) -> None:
        self._conversations = conversations
        self._messages = messages
        self._create_locks: dict[str, asyncio.Lock] = {}
        self._create_locks_guard = asyncio.Lock()

    @property
    def conversations(self) -> ConversationRepository:
        return self._conversations

    @property
    def messages(self) -> MessageRepository:
        return self._messages

    @staticmethod
    def _pair_key(participant_ids: list[str]) -> str:
        return "|".join(sorted(set(participant_ids)))

    async def get_or_create_conversation(self, participant_ids: list[str]) -> dict[str, Any]:
        key = self._pair_key(participant_ids)
        async with self._create_locks_guard:
            lock = self._create_locks.setdefault(key, asyncio.Lock())
        async with lock:
            existing = await self._conversations.find_between(participant_ids)
            if existing:
                return existing
            return await self._conversations.create(participant_ids)

    async def send_message(
        self,
        *,
        conversation: dict[str, Any],
        sender_id: str,
        recipient_id: str,
        content: str,
        message_type: str = "text",
    ) -> dict[str, Any]:
        conversation_id = str(conversation["_id"])
        message = await self._messages.create(
            conversation_id=conversation_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            message_type=message_type,
        )
        preview = content if len(content) <= 120 else content[:117] + "..."
        await self._conversations.touch(conversation_id, preview)
        return message

    async def merge_duplicate_conversations(self) -> int:
        """Merge conversations that share the exact same participant pair.

        Keeps the most recently active conversation, moves all of its messages
        into that doc, and deletes the duplicates. Returns how many duplicates
        were removed.
        """
        convos = await self._conversations.list_all()
        groups: dict[str, list[dict[str, Any]]] = {}
        for doc in convos:
            key = self._pair_key(doc.get("participants", []))
            groups.setdefault(key, []).append(doc)

        removed = 0
        for group in groups.values():
            if len(group) < 2:
                continue
            group.sort(
                key=lambda d: (d.get("last_message_at") or d.get("created_at") or datetime.min),
                reverse=True,
            )
            keeper_id = str(group[0]["_id"])
            for dup in group[1:]:
                duplicate_id = str(dup["_id"])
                await self._messages.move_conversation(duplicate_id, keeper_id)
                await self._conversations.delete_by_id(duplicate_id)
                removed += 1
        return removed