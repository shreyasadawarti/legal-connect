from datetime import time as dt_time
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import (
    LawyerAvailability,
    LawyerCategory,
    LawyerLanguage,
    LawyerProfile,
    LawyerSpecialization,
    User,
)
from app.db.serialize import lawyer_profile_to_doc
from app.db.serialize import enum_value
from app.models.platform import LegalCategory
from app.models.user import LawyerStatus

COLLECTION = "lawyer_profiles"

# MongoDB stored these four fields as embedded arrays; they are now child tables.
LIST_FIELDS = ("categories", "specializations", "languages", "availability")

# Never surfaced in search results, matching the previous `$nin` filter.
HIDDEN_STATUSES = (LawyerStatus.REJECTED, LawyerStatus.SUSPENDED)


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _parse_time(value: Any) -> Optional[dt_time]:
    if value is None or isinstance(value, dt_time):
        return value
    try:
        return dt_time.fromisoformat(str(value))
    except ValueError:
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math

    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


class LawyerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    # -- internal helpers ---------------------------------------------------

    def _scalar_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        columns = {c.key for c in LawyerProfile.__table__.columns}
        return {
            k: v
            for k, v in fields.items()
            if k in columns and k not in LIST_FIELDS
        }

    def _apply_list_fields(self, row: LawyerProfile, fields: dict[str, Any]) -> None:
        """Rebuild the child rows that back the four list fields."""
        if "categories" in fields:
            row.categories = [
                LawyerCategory(
                    position=idx,
                    category=getattr(c, "value", c),
                )
                for idx, c in enumerate(fields["categories"] or [])
            ]
        if "specializations" in fields:
            row.specializations = [
                LawyerSpecialization(position=idx, value=str(v))
                for idx, v in enumerate(fields["specializations"] or [])
            ]
        if "languages" in fields:
            row.languages = [
                LawyerLanguage(position=idx, value=str(v))
                for idx, v in enumerate(fields["languages"] or [])
            ]
        if "availability" in fields:
            slots = []
            for idx, slot in enumerate(fields["availability"] or []):
                slots.append(
                    LawyerAvailability(
                        position=idx,
                        day_of_week=int(slot.get("day_of_week", 0)),
                        start_time=_parse_time(slot.get("start_time")) or dt_time(0, 0),
                        end_time=_parse_time(slot.get("end_time")) or dt_time(0, 0),
                    )
                )
            row.availability = slots

    # -- reads --------------------------------------------------------------

    async def find_by_user_id(self, user_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return lawyer_profile_to_doc(row) if row else None

    async def find_by_user_ids(self, user_ids: list[str]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        unique_ids = list(dict.fromkeys(user_ids))
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id.in_(unique_ids))
        )
        rows = {r.user_id: r for r in result.scalars()}
        return [lawyer_profile_to_doc(rows[uid]) for uid in unique_ids if uid in rows]

    # -- writes -------------------------------------------------------------

    async def upsert(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Create or update a profile.

        Mirrors the previous `find_one_and_update(upsert=True)`, including
        refreshing `created_at` on every call, which the admin verification
        screen relies on for its "newest first" ordering.
        """
        now = utcnow()
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = LawyerProfile(
                user_id=user_id,
                avg_rating=Decimal("0.00"),
                rating_count=0,
                verification_status=LawyerStatus.PENDING_VERIFICATION,
                is_verified=False,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)

        for key, value in self._scalar_fields(fields).items():
            setattr(row, key, value)
        self._apply_list_fields(row, fields)
        row.user_id = user_id
        row.created_at = now
        row.updated_at = now

        await self.db.flush()
        await self.db.refresh(row)
        return lawyer_profile_to_doc(row)

    async def update(
        self, user_id: str, fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        for key, value in self._scalar_fields(fields).items():
            setattr(row, key, value)
        self._apply_list_fields(row, fields)
        row.updated_at = utcnow()
        await self.db.flush()
        await self.db.refresh(row)
        return lawyer_profile_to_doc(row)

    async def set_verification_status(
        self,
        user_id: str,
        status: LawyerStatus,
        note: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        fields: dict[str, Any] = {
            "verification_status": status,
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
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.avg_rating = Decimal(str(round(avg, 2)))
        row.rating_count = count
        await self.db.flush()
        return None

    # -- search -------------------------------------------------------------

    def _search_filters(
        self,
        q: Optional[str],
        category: Optional[LegalCategory],
        city: Optional[str],
        min_rating: Optional[float],
        verified_only: bool,
    ) -> list:
        filters = []
        if verified_only:
            filters.append(LawyerProfile.verification_status == LawyerStatus.ACTIVE)
        else:
            filters.append(LawyerProfile.verification_status.not_in(HIDDEN_STATUSES))
        if category:
            # An embedded-array membership test becomes an EXISTS subquery.
            filters.append(
                select(LawyerCategory.position)
                .where(
                    LawyerCategory.lawyer_profile_id == LawyerProfile.id,
                    LawyerCategory.category == category,
                )
                .exists()
            )
        if city:
            filters.append(func.lower(LawyerProfile.city).like(_like(city.lower()), escape="\\"))
        if q:
            pattern = _like(q.lower())
            # The displayed lawyer name lives on `users`, not `lawyer_profiles`, and the
            # profile rows are selected without a join, so it needs its own EXISTS subquery.
            name_match = (
                select(User.name)
                .where(
                    User.id == LawyerProfile.user_id,
                    func.lower(User.name).like(pattern, escape="\\"),
                )
                .exists()
            )
            filters.append(
                name_match
                | func.lower(LawyerProfile.bio).like(pattern, escape="\\")
                | select(LawyerSpecialization.position)
                .where(
                    LawyerSpecialization.lawyer_profile_id == LawyerProfile.id,
                    func.lower(LawyerSpecialization.value).like(pattern, escape="\\"),
                )
                .exists()
                | select(LawyerLanguage.position)
                .where(
                    LawyerLanguage.lawyer_profile_id == LawyerProfile.id,
                    func.lower(LawyerLanguage.value).like(pattern, escape="\\"),
                )
                .exists()
            )
        if min_rating and min_rating > 0:
            filters.append(LawyerProfile.avg_rating >= Decimal(str(min_rating)))
        return filters

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
        filters = self._search_filters(q, category, city, min_rating, verified_only)

        count_q = select(func.count()).select_from(LawyerProfile)
        list_q = select(LawyerProfile)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(LawyerProfile.avg_rating.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [lawyer_profile_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_with_geo(
        self,
        *,
        radius_km: Optional[float] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        verified_only: bool = False,
        sort: str = "rating",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return lawyers with coordinates, optionally annotated and sorted by distance.

        Only rows that carry both coordinates are considered, so a lawyer whose
        office location is missing can never be shown as "nearby". When `lat`/`lng`
        are supplied each result gains a `distance_km` field; `sort="distance"`
        orders nearest-first, while the default preserves the historical
        rating-first ordering the map has always rendered.
        """
        filters = [
            LawyerProfile.latitude.is_not(None),
            LawyerProfile.longitude.is_not(None),
        ]
        if verified_only:
            filters.append(LawyerProfile.verification_status == LawyerStatus.ACTIVE)
        else:
            filters.append(LawyerProfile.verification_status.not_in(HIDDEN_STATUSES))

        result = await self.db.execute(
            select(LawyerProfile).where(*filters).limit(limit * 5)
        )
        docs = [lawyer_profile_to_doc(row) for row in result.scalars()]

        if lat is not None and lng is not None:
            for doc in docs:
                doc["distance_km"] = round(
                    _haversine_km(lat, lng, doc["latitude"], doc["longitude"]), 2
                )
            if radius_km:
                docs = [d for d in docs if d["distance_km"] <= radius_km]

        if lat is not None and lng is not None and sort == "distance":
            docs.sort(key=lambda d: (d["distance_km"], -(d.get("avg_rating") or 0)))
        else:
            if lat is not None and lng is not None:
                docs.sort(key=lambda d: d["distance_km"])
            docs.sort(key=lambda d: d.get("avg_rating") or 0, reverse=True)
        return docs[:limit]

    async def list_with_city_but_no_coords(self) -> list[dict[str, Any]]:
        """Profiles that carry a city name but no usable coordinates yet.

        Used by the geocoding service to back-fill real office coordinates for
        lawyers who only published a city, so they can take part in
        distance-based "nearby lawyers" search results.
        """
        result = await self.db.execute(
            select(LawyerProfile)
            .where(
                LawyerProfile.city.is_not(None),
                func.trim(LawyerProfile.city) != "",
                (LawyerProfile.latitude.is_(None) | LawyerProfile.longitude.is_(None)),
                LawyerProfile.verification_status.not_in(HIDDEN_STATUSES),
            )
            .limit(500)
        )
        return [lawyer_profile_to_doc(row) for row in result.scalars()]

    async def list_by_status(
        self,
        *,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filters = []
        if status:
            filters.append(LawyerProfile.verification_status == status)

        count_q = select(func.count()).select_from(LawyerProfile)
        list_q = select(LawyerProfile)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(LawyerProfile.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [lawyer_profile_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    # -- analytics (used by the admin dashboard and reports) ---------------

    async def count_all(self) -> int:
        return (
            await self.db.execute(select(func.count()).select_from(LawyerProfile))
        ).scalar_one()

    async def count_by_status(self, status: Any) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(LawyerProfile)
                .where(LawyerProfile.verification_status == status)
            )
        ).scalar_one()

    async def top_rated(self, limit: int = 5) -> list[dict[str, Any]]:
        """Highest-rated profiles, for the admin analytics leaderboard."""
        result = await self.db.execute(
            select(LawyerProfile)
            .order_by(LawyerProfile.avg_rating.desc())
            .limit(limit)
        )
        return [lawyer_profile_to_doc(row) for row in result.scalars()]

    async def category_counts(self, limit: int = 8) -> list[dict[str, Any]]:
        """Most common practice areas.

        Replaces the MongoDB `$unwind` + `$group` pipeline: because categories
        are a real child table this is a plain GROUP BY over
        `lawyer_categories`.
        """
        result = await self.db.execute(
            select(LawyerCategory.category, func.count().label("cnt"))
            .group_by(LawyerCategory.category)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [
            {"category": enum_value(row.category), "count": row.cnt}
            for row in result.all()
        ]
