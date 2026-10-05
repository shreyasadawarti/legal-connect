from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.models.platform import AppointmentStatus

COLLECTION = "appointments"


class AppointmentRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("client_id")
        await self.collection.create_index("lawyer_id")
        await self.collection.create_index([("lawyer_id", 1), ("status", 1)])

    async def create(
        self,
        *,
        lawyer_id: str,
        client_id: str,
        category: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "lawyer_id": lawyer_id,
            "client_id": client_id,
            "category": category,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "status": AppointmentStatus.PENDING.value,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, appointment_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(appointment_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

    async def find_conflicts(
        self,
        *,
        lawyer_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        filt: dict[str, Any] = {
            "lawyer_id": lawyer_id,
            "status": {"$in": [AppointmentStatus.PENDING.value, AppointmentStatus.CONFIRMED.value]},
            "start_time": {"$lt": end_time},
            "end_time": {"$gt": start_time},
        }
        if exclude_id:
            try:
                filt["_id"] = {"$ne": ObjectId(exclude_id)}
            except Exception:  # noqa: BLE001
                pass
        cursor = self.collection.find(filt)
        return [doc for doc in await cursor.to_list(length=None)]

    async def list_for_user(
        self,
        user_id: str,
        as_lawyer: bool,
        status: Optional[AppointmentStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        field = "lawyer_id" if as_lawyer else "client_id"
        filt: dict[str, Any] = {field: user_id}
        if status:
            filt["status"] = status.value
        total = await self.collection.count_documents(filt)
        skip = (page - 1) * page_size
        cursor = (
            self.collection.find(filt)
            .sort("start_time", 1)
            .skip(skip)
            .limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_status(
        self, appointment_id: str, status: AppointmentStatus
    ) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(appointment_id)
        except Exception:  # noqa: BLE001
            return None
        await self.collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return await self.find_by_id(appointment_id)

    async def reschedule(
        self,
        appointment_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(appointment_id)
        except Exception:  # noqa: BLE001
            return None
        await self.collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": AppointmentStatus.PENDING.value,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return await self.find_by_id(appointment_id)

    async def delete(self, appointment_id: str) -> bool:
        try:
            oid = ObjectId(appointment_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.delete_one({"_id": oid})
        return bool(result.deleted_count)
