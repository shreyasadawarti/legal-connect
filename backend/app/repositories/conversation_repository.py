from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

COLLECTION = "conversations"


class ConversationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("participants")
        await self.collection.create_index([("participants", 1), ("updated_at", -1)])

    @staticmethod
    def _key(participant_ids: list[str]) -> list[str]:
        return sorted(set(participant_ids))

    async def find_between(self, participant_ids: list[str]) -> Optional[dict[str, Any]]:
        key = self._key(participant_ids)
        return await self.collection.find_one({"participants": key})

    async def find_by_id(self, conversation_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(conversation_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt = {"participants": user_id}
        cursor = self.collection.find(filt).sort("updated_at", -1)
        rows = [doc for doc in await cursor.to_list(length=None)]
        deduped = []
        seen: set[str] = set()
        for doc in rows:
            key = "|".join(self._key(doc.get("participants", [])))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(doc)
        total = len(deduped)
        start = (page - 1) * page_size
        items = deduped[start : start + page_size]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_all(self) -> list[dict[str, Any]]:
        return [doc for doc in await self.collection.find().to_list(length=None)]

    async def delete_by_id(self, conversation_id: str) -> None:
        try:
            oid = ObjectId(conversation_id)
        except Exception:  # noqa: BLE001
            return
        await self.collection.delete_one({"_id": oid})

    async def create(
        self,
        participant_ids: list[str],
        type_: str = "direct",
        last_message: str = "",
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "participants": self._key(participant_ids),
            "type": type_,
            "last_message": last_message,
            "last_message_at": now,
            "created_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def touch(
        self,
        conversation_id: str,
        last_message: str,
    ) -> None:
        try:
            oid = ObjectId(conversation_id)
        except Exception:  # noqa: BLE001
            return
        await self.collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "last_message": last_message,
                    "last_message_at": datetime.now(timezone.utc),
                }
            },
        )
