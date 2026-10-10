from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import new_id, utcnow
from app.db.models import RevenueEvent
from app.models.platform import RevenueEventType

REGISTRATION_FEE = Decimal("10000.00")
COMMISSION_MULTIPLIER = Decimal("5")


class RevenueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_idempotent(
        self,
        event_type: RevenueEventType,
        reference_id: str,
        amount: Decimal,
    ) -> None:
        """Insert a revenue event unless one already exists for the reference.

        The unique constraint on (event_type, reference_id) plus this MySQL
        `INSERT ... ON DUPLICATE KEY UPDATE` (a no-op update) makes recording
        idempotent, so re-running an action can never double-count revenue.
        """
        stmt = insert(RevenueEvent).values(
            id=new_id(),
            event_type=event_type,
            reference_id=reference_id,
            amount=amount,
            created_at=utcnow(),
        )
        stmt = stmt.on_duplicate_key_update(id=RevenueEvent.id)
        await self.db.execute(stmt)

    async def total(self) -> float:
        """Sum of all recorded revenue events."""
        total = (
            await self.db.execute(
                select(func.coalesce(func.sum(RevenueEvent.amount), 0))
            )
        ).scalar_one()
        return round(float(total), 2)

    async def total_by_source(self) -> dict[str, float]:
        """Sum of revenue events grouped by event type."""
        rows = (
            await self.db.execute(
                select(RevenueEvent.event_type, func.sum(RevenueEvent.amount)).group_by(
                    RevenueEvent.event_type
                )
            )
        ).all()
        return {event_type.value: round(float(value or 0), 2) for event_type, value in rows}