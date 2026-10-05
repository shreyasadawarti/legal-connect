from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

COLLECTION = "audit_logs"


class AuditLogRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("actor_id")
        await self.collection.create_index([("actor_id", 1), ("created_at", -1)])

    async def record(
        self,
        *,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        doc = {
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def list_for_actor(
        self,
        actor_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        total = await self.collection.count_documents({"actor_id": actor_id})
        cursor = (
            self.collection.find({"actor_id": actor_id})
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_all(
        self,
        *,
        actor_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt: dict[str, Any] = {}
        if actor_id:
            filt["actor_id"] = actor_id
        if entity_type:
            filt["entity_type"] = entity_type
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
