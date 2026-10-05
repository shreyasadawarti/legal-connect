from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

COLLECTION = "notifications"


class NotificationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("user_id")
        await self.collection.create_index([("user_id", 1), ("created_at", -1)])

    async def create(
        self,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        doc = {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data,
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt = {"user_id": user_id}
        total = await self.collection.count_documents(filt)
        skip = (page - 1) * page_size
        cursor = (
            self.collection.find(filt)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def count_unread(self, user_id: str) -> int:
        return await self.collection.count_documents(
            {"user_id": user_id, "is_read": False}
        )

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        try:
            oid = ObjectId(notification_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.update_one(
            {"_id": oid, "user_id": user_id}, {"$set": {"is_read": True}}
        )
        return bool(result.modified_count)

    async def find_by_id(self, notification_id: str, user_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(notification_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid, "user_id": user_id})

    async def mark_all_read(self, user_id: str) -> None:
        await self.collection.update_many(
            {"user_id": user_id, "is_read": False}, {"$set": {"is_read": True}}
        )

    async def delete(self, notification_id: str, user_id: str) -> bool:
        try:
            oid = ObjectId(notification_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.delete_one({"_id": oid, "user_id": user_id})
        return bool(result.deleted_count)
