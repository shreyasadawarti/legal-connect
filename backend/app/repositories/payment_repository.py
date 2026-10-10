from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Payment
from app.db.serialize import payment_to_doc
from app.models.platform import PaymentStatus

COLLECTION = "payments"


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        appointment_id: str,
        payee_id: str,
        amount: float,
        status: PaymentStatus = PaymentStatus.PAID,
    ) -> dict[str, Any]:
        row = Payment(
            appointment_id=appointment_id,
            payee_id=payee_id,
            # Converted to Decimal here so the value round-trips through the
            # DECIMAL(12,2) column without binary floating-point drift.
            amount=Decimal(str(amount)),
            status=status,
            reference=f"LC-{uuid4().hex[:10].upper()}",
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return payment_to_doc(row)

    async def find_by_id(self, payment_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        row = result.scalar_one_or_none()
        return payment_to_doc(row) if row else None

    async def create_pending(
        self,
        *,
        appointment_id: str,
        payee_id: str,
        amount: Decimal,
        gateway_order_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a PENDING payment awaiting gateway capture."""
        row = Payment(
            appointment_id=appointment_id,
            payee_id=payee_id,
            amount=amount,
            status=PaymentStatus.PENDING,
            reference=f"LC-{uuid4().hex[:10].upper()}",
            gateway_order_id=gateway_order_id,
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return payment_to_doc(row)

    async def attach_order(
        self, payment_id: str, gateway_order_id: str
    ) -> Optional[dict[str, Any]]:
        row = await self.db.get(Payment, payment_id)
        if row is None:
            return None
        row.gateway_order_id = gateway_order_id
        await self.db.flush()
        return payment_to_doc(row)

    async def mark_paid(
        self,
        payment_id: str,
        *,
        gateway_payment_id: Optional[str] = None,
        gateway_signature: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        row = await self.db.get(Payment, payment_id)
        if row is None:
            return None
        row.status = PaymentStatus.PAID
        if gateway_payment_id:
            row.gateway_payment_id = gateway_payment_id
        if gateway_signature:
            row.gateway_signature = gateway_signature
        await self.db.flush()
        return payment_to_doc(row)

    async def mark_failed(self, payment_id: str) -> Optional[dict[str, Any]]:
        row = await self.db.get(Payment, payment_id)
        if row is None:
            return None
        row.status = PaymentStatus.FAILED
        await self.db.flush()
        return payment_to_doc(row)

    async def find_by_order_id(self, gateway_order_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Payment).where(Payment.gateway_order_id == gateway_order_id)
        )
        row = result.scalar_one_or_none()
        return payment_to_doc(row) if row else None

    async def find_latest_for_appointment(
        self, appointment_id: str
    ) -> Optional[dict[str, Any]]:
        result = await self.db.execute(
            select(Payment)
            .where(Payment.appointment_id == appointment_id)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return payment_to_doc(row) if row else None

    async def list_for_payee(
        self,
        payee_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        total = (
            await self.db.execute(
                select(func.count()).select_from(Payment).where(
                    Payment.payee_id == payee_id
                )
            )
        ).scalar_one()
        result = await self.db.execute(
            select(Payment)
            .where(Payment.payee_id == payee_id)
            .order_by(Payment.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [payment_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # -- analytics (used by the admin dashboard and reports) ---------------

    async def count_all(self) -> int:
        return (
            await self.db.execute(select(func.count()).select_from(Payment))
        ).scalar_one()

    async def count_by_status(self, status: PaymentStatus) -> int:
        return (
            await self.db.execute(
                select(func.count())
                .select_from(Payment)
                .where(Payment.status == status)
            )
        ).scalar_one()

    async def sum_by_status(self, status: PaymentStatus) -> float:
        """Total amount for one status.

        Replaces the MongoDB `$match` + `$group` + `$sum` pipeline. SUM over a
        DECIMAL column returns None for an empty table, hence the coalesce.
        """
        total = (
            await self.db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.status == status
                )
            )
        ).scalar_one()
        return round(float(total), 2)