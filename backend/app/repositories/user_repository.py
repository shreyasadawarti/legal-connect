from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import UserRole, UserStatus


class UserNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


COLLECTION = "users"


def serialize_user(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert a MongoDB user document to an API-friendly dict with 'id'."""
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db[COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("email", unique=True)
        await self.collection.create_index("role")

    async def find_by_email(self, email: str) -> Optional[dict[str, Any]]:
        return await self.collection.find_one({"email": email.lower()})

    async def find_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        try:
            oid = ObjectId(user_id)
        except Exception:  # noqa: BLE001
            return None
        return await self.collection.find_one({"_id": oid})

    async def find_by_ids(self, user_ids: list[str]) -> list[dict[str, Any]]:
        ids: list[ObjectId] = []
        for uid in user_ids:
            try:
                ids.append(ObjectId(uid))
            except Exception:  # noqa: BLE001
                continue
        if not ids:
            return []
        return await self.collection.find({"_id": {"$in": ids}}).to_list(length=len(ids))

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "name": name,
            "email": email.lower(),
            "phone": phone,
            "password_hash": password_hash,
            "role": role.value,
            "preferred_language": "en",
            "city": None,
            "bio": None,
            "is_email_verified": False,
            "status": UserStatus.ACTIVE.value,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def update(self, user_id: str, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
        fields = dict(fields)
        fields["updated_at"] = datetime.now(timezone.utc)
        try:
            oid = ObjectId(user_id)
        except Exception:  # noqa: BLE001
            return None
        await self.collection.update_one({"_id": oid}, {"$set": fields})
        return await self.find_by_id(user_id)

    async def update_last_login(self, user_id: str) -> None:
        await self.update(user_id, {"last_login_at": datetime.now(timezone.utc)})

    async def mark_email_verified(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self.update(user_id, {"is_email_verified": True})

    async def list_all(
        self,
        *,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filt: dict[str, Any] = {}
        if role:
            filt["role"] = role.value
        if status:
            filt["status"] = status.value
        if q:
            filt["$or"] = [
                {"name": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}},
            ]
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

    async def set_status(self, user_id: str, status: UserStatus) -> Optional[dict[str, Any]]:
        return await self.update(user_id, {"status": status.value})
