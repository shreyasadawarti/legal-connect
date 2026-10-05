from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.models.platform import ComplaintStatus

COLLECTION = "complaints"


class ComplaintRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("user_id")
        await self.collection.create_index("status")

    async def create(
        self,
        *,
        user_id: str,
        subject: str,
        description: str,
        related_appointment_id: Optional[str] = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "subject": subject,
            "description": description,
            "related_appointment_id": related_appointment_id,
            "status": ComplaintStatus.OPEN.value,
            "admin_note": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, complaint_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(complaint_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

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
            self.collection.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_all(
        self,
        status: Optional[ComplaintStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt: dict[str, Any] = {}
        if status:
            filt["status"] = status.value
        total = await self.collection.count_documents(filt)
        skip = (page - 1) * page_size
        cursor = (
            self.collection.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_status(
        self,
        complaint_id: str,
        status: ComplaintStatus,
        admin_note: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(complaint_id)
        except Exception:  # noqa: BLE001
            return None
        update: dict[str, Any] = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc),
        }
        if admin_note is not None:
            update["admin_note"] = admin_note
        await self.collection.update_one({"_id": oid}, {"$set": update})
        return await self.find_by_id(complaint_id)
