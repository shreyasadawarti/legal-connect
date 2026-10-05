from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

COLLECTION = "messages"


class MessageRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("conversation_id")
        await self.collection.create_index([("conversation_id", 1), ("created_at", -1)])

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
        doc = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "content": content,
            "message_type": message_type,
            "is_read": is_read,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def list_for_conversation(
        self,
        conversation_id: str,
        before: Optional[str] = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        filt: dict[str, Any] = {"conversation_id": conversation_id}
        if before:
            try:
                filt["created_at"] = {"$lt": ObjectId(before).generation_time}
            except Exception:  # noqa: BLE001
                pass
        cursor = self.collection.find(filt).sort("created_at", -1).limit(page_size)
        items = [doc for doc in await cursor.to_list(length=page_size)]
        items.reverse()
        return {"items": items, "has_more": len(items) == page_size}

    async def count_unread(self, conversation_id: str, user_id: str) -> int:
        return await self.collection.count_documents(
            {
                "conversation_id": conversation_id,
                "recipient_id": user_id,
                "is_read": False,
            }
        )

    async def mark_read(
        self, conversation_id: str, user_id: str, before_id: Optional[str] = None
    ) -> None:
        filt: dict[str, Any] = {
            "conversation_id": conversation_id,
            "recipient_id": user_id,
            "is_read": False,
        }
        if before_id:
            try:
                filt["_id"] = {"$lte": ObjectId(before_id)}
            except Exception:  # noqa: BLE001
                pass
        await self.collection.update_many(filt, {"$set": {"is_read": True}})

    async def mark_one_read(self, message_id: str) -> None:
        try:
            oid = ObjectId(message_id)
        except Exception:  # noqa: BLE001
            return
        await self.collection.update_one({"_id": oid}, {"$set": {"is_read": True}})

    async def move_conversation(self, from_conversation_id: str, to_conversation_id: str) -> None:
        await self.collection.update_many(
            {"conversation_id": from_conversation_id},
            {"$set": {"conversation_id": to_conversation_id}},
        )
