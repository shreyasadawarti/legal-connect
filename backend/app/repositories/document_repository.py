from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.db.models import Document, DocumentShare
from app.db.serialize import document_to_doc

COLLECTION = "documents"


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_indexes(self) -> None:
        """No-op: constraints live in the MySQL schema now."""
        return None

    async def create(
        self,
        *,
        owner_id: str,
        title: str,
        original_name: str,
        mime_type: str,
        size_bytes: int,
        public_id: str,
        resource_type: str,
        related_appointment_id: Optional[str] = None,
        doc_type: str = "general",
    ) -> dict[str, Any]:
        row = Document(
            owner_id=owner_id,
            title=title,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            public_id=public_id,
            resource_type=resource_type,
            related_appointment_id=related_appointment_id,
            doc_type=doc_type,
            created_at=utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return document_to_doc(row)

    async def find_by_id(self, document_id: str) -> Optional[dict[str, Any]]:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        row = result.scalar_one_or_none()
        return document_to_doc(row) if row else None

    async def is_accessible(self, doc: dict[str, Any], user_id: str) -> bool:
        return doc.get("owner_id") == user_id or user_id in doc.get("shared_with", [])

    async def list_accessible(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        # Owned by the user, OR explicitly shared with them.
        shared_with_user = (
            select(DocumentShare.document_id)
            .where(
                DocumentShare.document_id == Document.id,
                DocumentShare.user_id == user_id,
            )
            .exists()
        )
        return await self._paginate(
            or_(Document.owner_id == user_id, shared_with_user), page, page_size
        )

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._paginate(Document.owner_id == user_id, page, page_size)

    async def _paginate(
        self, where_clause, page: int, page_size: int
    ) -> dict[str, Any]:
        count_q = select(func.count()).select_from(Document)
        list_q = select(Document)
        if where_clause is not None:
            count_q = count_q.where(where_clause)
            list_q = list_q.where(where_clause)

        total = (await self.db.execute(count_q)).scalar_one()
        result = await self.db.execute(
            list_q.order_by(Document.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        items = [document_to_doc(row) for row in result.scalars()]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def _set_shares(self, document_id: str, user_ids: list[str]) -> bool:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.shares = [
            DocumentShare(user_id=uid, position=idx)
            for idx, uid in enumerate(user_ids)
        ]
        await self.db.flush()
        return True

    async def add_shared(self, document_id: str, user_ids: list[str]) -> bool:
        doc = await self.find_by_id(document_id)
        if doc is None:
            return False
        # dict.fromkeys de-duplicates while preserving the existing order.
        updated = list(dict.fromkeys(list(doc.get("shared_with", [])) + list(user_ids)))
        return await self._set_shares(document_id, updated)

    async def remove_shared(self, document_id: str, user_ids: list[str]) -> bool:
        doc = await self.find_by_id(document_id)
        if doc is None:
            return False
        remove = set(user_ids)
        keep = [u for u in doc.get("shared_with", []) if u not in remove]
        return await self._set_shares(document_id, keep)

    async def delete(self, document_id: str) -> bool:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        row = result.scalar_one_or_none()
        if row is None:
            return False
        # Shares go with it via ON DELETE CASCADE, and any lawyer profile that
        # referenced it as verification evidence has the link nulled.
        await self.db.delete(row)
        await self.db.flush()
        return True