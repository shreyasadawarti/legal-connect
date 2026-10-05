from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies import CurrentUser, get_document_storage, require_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentShareRequest,
    serialize_document,
)
from app.services.cloudinary_service import DocumentStorageError

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024

ALLOWED_DOC_TYPES = {"general", "verification"}

VERIFICATION_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}


async def _find_accessible(
    db: AsyncSession, document_id: str, user: dict, owner_only: bool = False
):
    docs = DocumentRepository(db)
    doc = await docs.find_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if owner_only:
        if doc["owner_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Only the owner can do this")
    elif not await docs.is_accessible(doc, user["id"]):
        raise HTTPException(status_code=403, detail="You do not have access to this document")
    return doc


def _storage_error(exc: DocumentStorageError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    storage = Depends(get_document_storage), 
    file: UploadFile = File(...),
    title: str = Form(""),
    doc_type: str = Form("general"),
    related_appointment_id: Optional[str] = Form(None),
    share_with_user_id: Optional[str] = Form(None),
):
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=422, detail="Invalid document type")
    if doc_type == "verification":
        mime = (file.content_type or "application/octet-stream").lower()
        if mime not in VERIFICATION_MIME_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Verification documents must be a PDF, PNG, or JPG file",
            )
    if share_with_user_id:
        target = await UserRepository(db).find_by_id(share_with_user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User to share with not found")
    try:
        meta = await storage.upload_bytes(
            data=content,
            filename=file.filename or "document",
            resource_type="raw",
        )
    except DocumentStorageError as exc:
        raise _storage_error(exc) from exc
    doc = await DocumentRepository(db).create(
        owner_id=user["id"],
        title=title.strip() or (file.filename or "document"),
        original_name=file.filename or "document",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=meta["bytes"],
        public_id=meta["public_id"],
        resource_type=meta["resource_type"],
        related_appointment_id=related_appointment_id,
        doc_type=doc_type,
    )
    if share_with_user_id:
        await DocumentRepository(db).add_shared(doc["_id"], [share_with_user_id])
        doc["shared_with"] = [share_with_user_id]
        notifications = NotificationRepository(db)
        await notifications.create(
            user_id=share_with_user_id,
            notification_type="SYSTEM",
            title="Document shared with you",
            message=f"{user['name']} shared a document with you: {doc['title']}",
            data={"document_id": str(doc["_id"])},
        )
    return DocumentResponse.model_validate(serialize_document(doc, owner_name=user["name"]))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    docs = DocumentRepository(db)
    result = await docs.list_accessible(user["id"], page=page, page_size=page_size)
    owner_ids = {d["owner_id"] for d in result["items"]}
    users = await UserRepository(db).find_by_ids(list(owner_ids))
    name_map = {str(u["_id"]): u.get("name", "") for u in users}
    items = [
        DocumentResponse.model_validate(
            serialize_document(d, owner_name=name_map.get(d["owner_id"], ""))
        )
        for d in result["items"]
    ]
    return {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    doc = await _find_accessible(db, document_id, user)
    owner = await UserRepository(db).find_by_id(doc["owner_id"])
    name = owner.get("name", "") if owner else ""
    return DocumentResponse.model_validate(serialize_document(doc, owner_name=name))


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    storage = Depends(get_document_storage), 
):
    doc = await _find_accessible(db, document_id, user)
    try:
        url = storage.signed_url(doc.get("public_id", ""), doc.get("resource_type", "raw"))
    except DocumentStorageError as exc:
        raise _storage_error(exc) from exc
    return {"url": url, "filename": doc.get("original_name", "document")}


@router.post("/{document_id}/share", response_model=DocumentResponse)
async def share_document(
    document_id: str,
    payload: DocumentShareRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    doc = await _find_accessible(db, document_id, user, owner_only=True)
    users = await UserRepository(db).find_by_ids(payload.user_ids)
    found = {str(u["_id"]) for u in users}
    if found != set(payload.user_ids):
        raise HTTPException(status_code=404, detail="One or more users were not found")
    docs = DocumentRepository(db)
    await docs.add_shared(document_id, payload.user_ids)
    notifications = NotificationRepository(db)
    for uid in payload.user_ids:
        if uid == user["id"]:
            continue
        await notifications.create(
            user_id=uid,
            notification_type="SYSTEM",
            title="Document shared with you",
            message=f"{user['name']} shared a document with you: {doc['title']}",
            data={"document_id": document_id},
        )
    audit = AuditLogRepository(db)
    await audit.record(
        actor_id=user["id"],
        action="document.share",
        entity_type="document",
        entity_id=document_id,
        details={"target_user_ids": payload.user_ids},
    )
    updated = await docs.find_by_id(document_id)
    return DocumentResponse.model_validate(serialize_document(updated, owner_name=user["name"]))


@router.post("/{document_id}/revoke", response_model=DocumentResponse)
async def revoke_document(
    document_id: str,
    payload: DocumentShareRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    doc = await _find_accessible(db, document_id, user, owner_only=True)
    docs = DocumentRepository(db)
    await docs.remove_shared(document_id, payload.user_ids)
    audit = AuditLogRepository(db)
    await audit.record(
        actor_id=user["id"],
        action="document.revoke",
        entity_type="document",
        entity_id=document_id,
        details={"target_user_ids": payload.user_ids},
    )
    updated = await docs.find_by_id(document_id)
    owner = await UserRepository(db).find_by_id(doc["owner_id"])
    name = owner.get("name", "") if owner else ""
    return DocumentResponse.model_validate(serialize_document(updated, owner_name=name))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    storage = Depends(get_document_storage), 
):
    doc = await _find_accessible(db, document_id, user, owner_only=True)
    docs = DocumentRepository(db)
    await docs.delete(document_id)
    if doc.get("doc_type") == "verification":
        from app.repositories.lawyer_repository import LawyerRepository

        await LawyerRepository(db).clear_verification_document(doc.get("owner_id", ""), document_id)
    try:
        await storage.delete(doc.get("public_id", ""), doc.get("resource_type", "raw"))
    except DocumentStorageError:
        pass  # metadata already removed; cloud cleanup is best-effort
    audit = AuditLogRepository(db)
    await audit.record(
        actor_id=user["id"],
        action="document.delete",
        entity_type="document",
        entity_id=document_id,
        details={"title": doc.get("title")},
    )
