from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import AuditLog
from app.db.serialize import audit_log_to_doc

COLLECTION = "audit_logs"


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def record(
        self,
        *,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        row = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return audit_log_to_doc(row)

    async def list_for_actor(
        self,
        actor_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._paginate([AuditLog.actor_id == actor_id], page, page_size)

    async def list_all(
        self,
        *,
        actor_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filters = []
        if actor_id:
            filters.append(AuditLog.actor_id == actor_id)
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        return await self._paginate(filters, page, page_size)

    async def _paginate(self, filters: list, page: int, page_size: int) -> dict[str, Any]:
        count_q = select(func.count()).select_from(AuditLog)
        list_q = select(AuditLog)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(AuditLog.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [audit_log_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}