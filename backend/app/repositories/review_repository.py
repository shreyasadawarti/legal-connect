from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

COLLECTION = "reviews"


class ReviewRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("lawyer_id")
        await self.collection.create_index([("lawyer_id", 1), ("reviewer_id", 1)])

    async def create(
        self,
        *,
        lawyer_id: str,
        reviewer_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        doc = {
            "lawyer_id": lawyer_id,
            "reviewer_id": reviewer_id,
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, review_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(review_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

    async def find_by_user_and_lawyer(
        self, reviewer_id: str, lawyer_id: str
    ) -> Optional[dict[str, Any]]:
        return await self.collection.find_one(
            {"reviewer_id": reviewer_id, "lawyer_id": lawyer_id}
        )

    async def list_for_lawyer(
        self,
        lawyer_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt = {"lawyer_id": lawyer_id}
        total = await self.collection.count_documents(filt)
        skip = (page - 1) * page_size
        cursor = (
            self.collection.find(filt).sort("created_at", -1).skip(skip).limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def rating_average(self, lawyer_id: str) -> dict[str, Any]:
        """Return {'avg': float, 'count': int} for a lawyer's reviews."""
        docs = await self.collection.find({"lawyer_id": lawyer_id}).to_list(length=None)
        if not docs:
            return {"avg": 0.0, "count": 0}
        total = sum(d.get("rating", 0) for d in docs)
        return {"avg": round(total / len(docs), 2), "count": len(docs)}

    async def delete(self, review_id: str) -> bool:
        try:
            oid = ObjectId(review_id)
        except Exception:  # noqa: BLE001
            return False
        result = await self.collection.delete_one({"_id": oid})
        return bool(result.deleted_count)
