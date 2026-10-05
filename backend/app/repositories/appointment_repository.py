from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Appointment
from app.db.serialize import appointment_to_doc
from app.models.platform import AppointmentStatus

COLLECTION = "appointments"

# Only these two statuses block a new booking slot.
BLOCKING_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


class AppointmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        lawyer_id: str,
        client_id: str,
        category: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        now = utcnow()
        row = Appointment(
            lawyer_id=lawyer_id,
            client_id=client_id,
            category=category,
            start_time=start_time,
            end_time=end_time,
            description=description,
            status=AppointmentStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        return appointment_to_doc(row)

    async def find_by_id(self, appointment_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        row = result.scalar_one_or_none()
        return appointment_to_doc(row) if row else None

    async def find_conflicts(
        self,
        *,
        lawyer_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Appointments that overlap the requested window.

        The overlap test `existing.start < new.end AND existing.end > new.start`
        is unchanged; only the syntax moved from Mongo operators to SQL.
        """
        filters = [
            Appointment.lawyer_id == lawyer_id,
            Appointment.status.in_(BLOCKING_STATUSES),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        ]
        if exclude_id:
            filters.append(Appointment.id != exclude_id)
        result = await self.db.execute(select(Appointment).where(*filters))
        return [appointment_to_doc(row) for row in result.scalars()]

    async def list_for_user(
        self,
        user_id: str,
        as_lawyer: bool,
        status: Optional[AppointmentStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        field = Appointment.lawyer_id if as_lawyer else Appointment.client_id
        filters = [field == user_id]
        if status:
            filters.append(Appointment.status == status)

        count_q = select(func.count()).select_from(Appointment)
        list_q = select(Appointment)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(Appointment.start_time.asc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [appointment_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_status(
        self, appointment_id: str, status: AppointmentStatus
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = status
        row.updated_at = utcnow()
        await self.db.flush()
        return appointment_to_doc(row)

    async def reschedule(
        self,
        appointment_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.start_time = start_time
        row.end_time = end_time
        row.status = AppointmentStatus.PENDING
        row.updated_at = utcnow()
        await self.db.flush()
        return appointment_to_doc(row)

    async def delete(self, appointment_id: str) -> bool:
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.flush()
        return True

    # -- analytics (used by the admin dashboard and reports) ---------------

    async def count_all(self) -> int:
        return (
            await self.db.execute(select(func.count()).select_from(Appointment))
        ).scalar_one()

    async def count_by_status(self, status: AppointmentStatus) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(Appointment)
                .where(Appointment.status == status)
            )
        ).scalar_one()

    async def count_by_month(self, limit: int = 60) -> list[dict[str, Any]]:
        """Appointments grouped by `YYYY-MM`, oldest first.

        Replaces MongoDB's `$dateToString` grouping. `created_at` is a
        timezone-aware UTC value, so MySQL's DATE_FORMAT runs in the same
        timezone the API has always reported.
        """
        month = func.date_format(Appointment.created_at, "%Y-%m")
        result = await self.db.execute(
            select(month.label("month"), func.count().label("cnt"))
            .group_by(month)
            .order_by(month.asc())
            .limit(limit)
        )
        return [{"month": row.month, "count": row.cnt} for row in result.all()]

    async def list_all_paginated(
        self,
        *,
        status: Optional[AppointmentStatus] = None,
        lawyer_id: Optional[str] = None,
        client_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Unfiltered listing for the admin reports export."""
        filters = []
        if status:
            filters.append(Appointment.status == status)
        if lawyer_id:
            filters.append(Appointment.lawyer_id == lawyer_id)
        if client_id:
            filters.append(Appointment.client_id == client_id)

        count_q = select(func.count()).select_from(Appointment)
        list_q = select(Appointment)
        for f in filters:
            count_q = count_q.where(f)
            list_q = list_q.where(f)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(Appointment.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [appointment_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}