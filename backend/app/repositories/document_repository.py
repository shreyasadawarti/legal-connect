from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

COLLECTION = "documents"


class DocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("owner_id")
        await self.collection.create_index([("owner_id", 1), ("created_at", -1)])
        await self.collection.create_index("shared_with")

    async def create(
        self,
        *,
        owner_id: str,
        title: str,
        original_name: str,
        mime_type: str,
        size_bytes: int,
        public_id: str,
        resource_type: str,
        related_appointment_id: Optional[str] = None,
        doc_type: str = "general",
    ) -> dict[str, Any]:
        doc = {
            "owner_id": owner_id,
            "title": title,
            "original_name": original_name,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "public_id": public_id,
            "resource_type": resource_type,
            "related_appointment_id": related_appointment_id,
            "doc_type": doc_type,
            "shared_with": [],
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, document_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(document_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

    async def is_accessible(self, doc: dict[str, Any], user_id: str) -> bool:
        return doc.get("owner_id") == user_id or user_id in doc.get("shared_with", [])

    async def list_accessible(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt = {"$or": [{"owner_id": user_id}, {"shared_with": {"$in": [user_id]}}]}
        return await self._paginate(filt, page, page_size)

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._paginate({"owner_id": user_id}, page, page_size)

    async def _paginate(
        self, filt: dict[str, Any], page: int, page_size: int
    ) -> dict[str, Any]:
        total = await self.collection.count_documents(filt)
        cursor = (
            self.collection.find(filt)
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def add_shared(self, document_id: str, user_ids: list[str]) -> bool:
        doc = await self.find_by_id(document_id)
        if doc is None:
            return False
        updated = list(dict.fromkeys(doc.get("shared_with", []) + user_ids))
        try:
            oid = ObjectId(document_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.update_one(
            {"_id": oid}, {"$set": {"shared_with": updated}}
        )
        return bool(result.matched_count)

    async def remove_shared(self, document_id: str, user_ids: list[str]) -> bool:
        doc = await self.find_by_id(document_id)
        if doc is None:
            return False
        keep = [u for u in doc.get("shared_with", []) if u not in set(user_ids)]
        try:
            oid = ObjectId(document_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.update_one(
            {"_id": oid}, {"$set": {"shared_with": keep}}
        )
        return bool(result.matched_count)

    async def delete(self, document_id: str) -> bool:
        try:
            oid = ObjectId(document_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.delete_one({"_id": oid})
        return bool(result.deleted_count)
