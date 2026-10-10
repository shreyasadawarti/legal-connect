from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Complaint
from app.db.serialize import complaint_to_doc
from app.models.platform import ComplaintStatus

COLLECTION = "complaints"


class ComplaintRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        user_id: str,
        subject: str,
        description: str,
        related_appointment_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict[str, Any]:
        now = utcnow()
        row = Complaint(
            user_id=user_id,
            subject=subject,
            description=description,
            related_appointment_id=related_appointment_id,
            target_user_id=target_user_id,
            conversation_id=conversation_id,
            category=category,
            status=ComplaintStatus.OPEN,
            admin_note=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        return complaint_to_doc(row)

    async def find_by_id(self, complaint_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Complaint).where(Complaint.id == complaint_id)
        )
        row = result.scalar_one_or_none()
        return complaint_to_doc(row) if row else None

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._paginate([Complaint.user_id == user_id], page, page_size)

    async def list_for_target(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._paginate(
            [Complaint.target_user_id == user_id], page, page_size
        )

    async def list_all(
        self,
        status: Optional[ComplaintStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        filters = []
        if status:
            filters.append(Complaint.status == status)
        return await self._paginate(filters, page, page_size)

    async def _paginate(self, filters: list, page: int, page_size: int) -> dict[str, Any]:
        count_q = select(func.count()).select_from(Complaint)
        list_q = select(Complaint)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(Complaint.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [complaint_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_status(
        self,
        complaint_id: str,
        status: ComplaintStatus,
        admin_note: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Complaint).where(Complaint.id == complaint_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = status
        if admin_note is not None:
            row.admin_note = admin_note
        row.updated_at = utcnow()
        await self.db.flush()
        return complaint_to_doc(row)

    async def respond(
        self,
        complaint_id: str,
        status: ComplaintStatus,
        admin_note: Optional[str] = None,
        reporter_response: Optional[str] = None,
        reported_response: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Save an admin reply, stamping each direction's timestamp when set.

        A response is written only when a non-empty value is supplied, so an
        admin updating just the status never clears an earlier reply.
        """
        result = await self.db.execute(
            select(Complaint).where(Complaint.id == complaint_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = status
        if admin_note is not None:
            row.admin_note = admin_note
        now = utcnow()
        if reporter_response:
            row.reporter_response = reporter_response
            row.reporter_responded_at = now
        if reported_response:
            row.reported_response = reported_response
            row.reported_responded_at = now
        row.updated_at = now
        await self.db.flush()
        return complaint_to_doc(row)

    # -- analytics (used by the admin dashboard and reports) ---------------

    async def count_all(self) -> int:
        return (
            await self.db.execute(select(func.count()).select_from(Complaint))
        ).scalar_one()

    async def count_by_status(self, status: ComplaintStatus) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(Complaint)
                .where(Complaint.status == status)
            )
        ).scalar_one()

    async def count_in_statuses(self, statuses: tuple) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(Complaint)
                .where(Complaint.status.in_(statuses))
            )
        ).scalar_one()