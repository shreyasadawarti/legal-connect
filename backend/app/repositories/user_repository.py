from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import User
from app.db.serialize import user_to_doc
from app.models.user import UserRole, UserStatus

COLLECTION = "users"


class UserNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


def serialize_user(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert a user document to an API-friendly dict with 'id'."""
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


def _like(term: str) -> str:
    """Escape LIKE wildcards so a search string is matched literally.

    MongoDB's `$regex` treated `%` as a literal, so escaping keeps results
    identical for the strings users actually type.
    """
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: the unique/index constraints are part of the MySQL schema.

        Kept so any existing caller keeps working; `create_all` and Alembic own
        the indexes now.
        """
        return None

    async def find_by_email(self, email: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        row = result.scalar_one_or_none()
        return user_to_doc(row) if row else None

    async def find_by_reset_token(self, token_hash: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(User).where(User.reset_token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return user_to_doc(row) if row else None

    async def find_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        # No ObjectId parsing is needed any more: IDs are already strings, so a
        # malformed value simply matches nothing and returns None as before.
        result = await self.db.execute(select(User).where(User.id == user_id))
        row = result.scalar_one_or_none()
        return user_to_doc(row) if row else None

    async def find_by_ids(self, user_ids: list[str]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        # dict.fromkeys de-duplicates while preserving the caller's ordering.
        unique_ids = list(dict.fromkeys(user_ids))
        result = await self.db.execute(select(User).where(User.id.in_(unique_ids)))
        rows = {row.id: row for row in result.scalars()}
        return [user_to_doc(rows[uid]) for uid in unique_ids if uid in rows]

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> dict[str, Any]:
        now = utcnow()
        row = User(
            name=name,
            email=email.lower(),
            phone=phone,
            password_hash=password_hash,
            role=role,
            preferred_language="en",
            city=None,
            bio=None,
            is_email_verified=False,
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_login_at=None,
        )
        self.db.add(row)
        await self.db.flush()
        return user_to_doc(row)

    async def update(
        self, user_id: str, fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        columns = {c.key for c in User.__table__.columns}
        for key, value in fields.items():
            # Unknown keys are ignored rather than raising, matching the
            # schemaless `$set` behaviour of the previous implementation.
            if key in columns:
                setattr(row, key, value)
        row.updated_at = utcnow()
        await self.db.flush()
        return user_to_doc(row)

    async def update_last_login(self, user_id: str) -> None:
        await self.update(user_id, {"last_login_at": utcnow()})

    async def mark_email_verified(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self.update(user_id, {"is_email_verified": True})

    async def set_reset_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> Optional[dict[str, Any]]:
        return await self.update(
            user_id,
            {"reset_token_hash": token_hash, "reset_token_expires_at": expires_at},
        )

    async def clear_reset_token(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self.update(
            user_id,
            {"reset_token_hash": None, "reset_token_expires_at": None},
        )

    async def increment_auth_version(self, user_id: str) -> int:
        """Bump auth_version so previously-issued JWTs are rejected."""
        user = await self.find_by_id(user_id)
        if user is None:
            return 0
        ver = int(user.get("auth_version", 0)) + 1
        await self.update(user_id, {"auth_version": ver})
        return ver

    async def list_all(
        self,
        *,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filters = []
        if role:
            filters.append(User.role == role)
        if status:
            filters.append(User.status == status)
        if q:
            pattern = _like(q.lower())
            filters.append(
                func.lower(User.name).like(pattern, escape="\\")
                | func.lower(User.email).like(pattern, escape="\\")
            )

        count_q = select(func.count()).select_from(User)
        list_q = select(User)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(User.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [user_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def set_status(
        self, user_id: str, status: UserStatus
    ) -> Optional[dict[str, Any]]:
        return await self.update(user_id, {"status": status})

    # -- analytics (used by the admin dashboard and reports) ---------------

    async def count_all(self) -> int:
        return (await self.db.execute(select(func.count()).select_from(User))).scalar_one()

    async def count_by_role(self, role: UserRole) -> int:
        return (
            await self.db.execute(
                select(func.count()).select_from(User).where(User.role == role)
            )
        ).scalar_one()