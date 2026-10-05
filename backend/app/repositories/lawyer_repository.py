from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.models.platform import LegalCategory
from app.models.user import LawyerStatus

COLLECTION = "lawyer_profiles"


class LawyerRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection: AsyncIOMotorCollection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("user_id", unique=True)
        await self.collection.create_index("verification_status")
        await self.collection.create_index("categories")
        await self.collection.create_index("city")

    async def find_by_user_id(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self.collection.find_one({"user_id": user_id})

    async def find_by_user_ids(self, user_ids: list[str]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        cursor = self.collection.find({"user_id": {"$in": user_ids}})
        return [doc for doc in await cursor.to_list(length=len(user_ids))]

    async def upsert(
        self,
        user_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return await self.collection.find_one_and_update(
            {"user_id": user_id},
            {
                "$set": {**fields, "user_id": user_id, "created_at": now, "updated_at": now},
                "$setOnInsert": {
                    "avg_rating": 0.0,
                    "rating_count": 0,
                    "verification_status": LawyerStatus.PENDING_VERIFICATION.value,
                    "is_verified": False,
                },
            },
            upsert=True,
            return_document=True,
        )

    async def update(self, user_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
        fields = dict(fields)
        fields["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one({"user_id": user_id}, {"$set": fields})
        return await self.find_by_user_id(user_id)

    async def set_verification_status(
        self,
        user_id: str,
        status: LawyerStatus,
        note: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        fields: dict[str, Any] = {
            "verification_status": status.value,
            "is_verified": status == LawyerStatus.ACTIVE,
        }
        if status == LawyerStatus.REJECTED:
            fields["rejection_reason"] = (note or "").strip() or None
        else:
            fields["rejection_reason"] = None
        return await self.update(user_id, fields)

    async def set_verification_document(
        self, user_id: str, document_id: str
    ) -> Optional[dict[str, Any]]:
        return await self.update(user_id, {"verification_document_id": document_id})

    async def clear_verification_document(
        self, user_id: str, document_id: str
    ) -> Optional[dict[str, Any]]:
        return await self.update(user_id, {"verification_document_id": None})

    async def update_rating(self, user_id: str, avg: float, count: int) -> None:
        await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"avg_rating": round(avg, 2), "rating_count": count}},
        )

    async def search(
        self,
        *,
        q: Optional[str] = None,
        category: Optional[LegalCategory] = None,
        city: Optional[str] = None,
        min_rating: Optional[float] = None,
        verified_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt: dict[str, Any] = {
            "verification_status": {
                "$nin": [LawyerStatus.REJECTED.value, LawyerStatus.SUSPENDED.value]
            }
        }
        if verified_only:
            filt["verification_status"] = LawyerStatus.ACTIVE.value
        if category:
            filt["categories"] = category.value
        if city:
            filt["city"] = {"$regex": city, "$options": "i"}
        if q:
            filt["$or"] = [
                {"bio": {"$regex": q, "$options": "i"}},
                {"specializations": {"$regex": q, "$options": "i"}},
                {"languages": {"$regex": q, "$options": "i"}},
            ]
        if min_rating and min_rating > 0:
            filt["avg_rating"] = {"$gte": min_rating}

        total = await self.collection.count_documents(filt)
        skip = (page - 1) * page_size
        cursor = (
            self.collection.find(filt)
            .sort("avg_rating", -1)
            .skip(skip)
            .limit(page_size)
        )
        items = [doc for doc in await cursor.to_list(length=page_size)]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_with_geo(
        self,
        *,
        radius_km: Optional[float] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        verified_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return lawyers that have coordinates (for the map), sorted by distance.

        Uses a simple equal-rectangle approximation of haversine distance which is
        fine for rendering nearby markers on a local map.
        """
        filt: dict[str, Any] = {
            "verification_status": {
                "$nin": [LawyerStatus.REJECTED.value, LawyerStatus.SUSPENDED.value]
            },
            "latitude": {"$type": "double"},
            "longitude": {"$type": "double"},
        }
        if verified_only:
            filt["verification_status"] = LawyerStatus.ACTIVE.value
        all_docs = [
            doc for doc in await self.collection.find(filt).to_list(length=limit * 5)
        ]
        if lat is not None and lng is not None and radius_km:
            all_docs = [
                d
                for d in all_docs
                if _haversine_km(lat, lng, d.get("latitude"), d.get("longitude")) <= radius_km
            ]
        if lat is not None and lng is not None:
            all_docs.sort(
                key=lambda d: _haversine_km(lat, lng, d.get("latitude"), d.get("longitude"))
            )
        all_docs.sort(key=lambda d: d.get("avg_rating") or 0, reverse=True)
        return all_docs[:limit]

    async def list_by_status(
        self,
        *,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt: dict[str, Any] = {}
        if status:
            filt["verification_status"] = status
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


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math

    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))

