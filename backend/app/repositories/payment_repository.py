from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.models.platform import PaymentStatus

COLLECTION = "payments"


class PaymentRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("appointment_id")
        await self.collection.create_index("payee_id")

    async def create(
        self,
        *,
        appointment_id: str,
        payee_id: str,
        amount: float,
        status: PaymentStatus = PaymentStatus.PAID,
    ) -> dict[str, Any]:
        doc = {
            "appointment_id": appointment_id,
            "payee_id": payee_id,
            "amount": amount,
            "status": status.value,
            "reference": f"LC-{uuid4().hex[:10].upper()}",
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, payment_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(payment_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

    async def list_for_payee(
        self,
        payee_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt = {"payee_id": payee_id}
        total = await self.collection.count_documents(filt)
        skip = (page - 1) * page_size
        cursor = (
            self.collection.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
