from copy import deepcopy
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import UserPreference

DEFAULT_PREFERENCES: dict[str, Any] = {
    "notifications": {
        "email_appointments": True,
        "email_messages": True,
        "email_reviews": True,
        "push_appointments": True,
        "push_messages": True,
        "push_complaints": True,
    },
    "interests": [],
    "privacy": {
        "show_profile": True,
        "show_online_status": True,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `override` into a copy of `base`; lists replace wholesale."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def merge_preferences(stored: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Stored settings over the defaults, so a partial save is still complete."""
    return _deep_merge(DEFAULT_PREFERENCES, stored or {})


class UserPreferenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return row.data if row else None

    async def upsert(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = UserPreference(user_id=user_id, data=patch, updated_at=utcnow())
            self.db.add(row)
        else:
            row.data = _deep_merge(row.data or {}, patch)
            row.updated_at = utcnow()
        await self.db.flush()
        return row.data
