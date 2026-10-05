from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Review
from app.db.serialize import review_to_doc

COLLECTION = "reviews"


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        lawyer_id: str,
        reviewer_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        row = Review(
            lawyer_id=lawyer_id,
            reviewer_id=reviewer_id,
            rating=rating,
            comment=comment,
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return review_to_doc(row)

    async def find_by_id(self, review_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(select(Review).where(Review.id == review_id))
        row = result.scalar_one_or_none()
        return review_to_doc(row) if row else None

    async def find_by_user_and_lawyer(
        self, reviewer_id: str, lawyer_id: str
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Review).where(
                Review.reviewer_id == reviewer_id, Review.lawyer_id == lawyer_id
            )
        )
        row = result.scalar_one_or_none()
        return review_to_doc(row) if row else None

    async def list_for_lawyer(
        self,
        lawyer_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        total = (
            await self.db.execute(
                select(func.count()).select_from(Review).where(
                    Review.lawyer_id == lawyer_id
                )
            )
        ).scalar_one()
        result = await self.db.execute(
            select(Review)
            .where(Review.lawyer_id == lawyer_id)
            .order_by(Review.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [review_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def rating_average(self, lawyer_id: str) -> dict[str, Any]:
        """Return {'avg': float, 'count': int} for a lawyer's reviews.

        Computed in SQL with AVG/COUNT instead of summing in Python, and
        rounded to two places to match the previous return value exactly.
        """
        result = await self.db.execute(
            select(
                func.coalesce(func.avg(Review.rating), 0),
                func.count(Review.id),
            ).where(Review.lawyer_id == lawyer_id)
        )
        avg, count = result.one()
        if not count:
            return {"avg": 0.0, "count": 0}
        return {"avg": round(float(avg), 2), "count": int(count)}

    async def delete(self, review_id: str) -> bool:
        result = await self.db.execute(select(Review).where(Review.id == review_id))
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.flush()
        return True