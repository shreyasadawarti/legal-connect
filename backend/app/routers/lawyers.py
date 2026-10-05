from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.dependencies import require_db, require_roles
from app.models.platform import LegalCategory
from app.models.user import LawyerStatus, UserRole
from app.repositories.document_repository import DocumentRepository
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.user_repository import UserRepository
from app.schemas.lawyer import (
    LawyerProfileCreate,
    LawyerProfileListResponse,
    LawyerProfileResponse,
    LawyerProfileUpdate,
    serialize_lawyer_profile,
)

router = APIRouter(prefix="/lawyers", tags=["lawyers"])


async def _get_lawyer_profile_for_user(
    db: AsyncIOMotorDatabase, user_id: str
) -> tuple[dict, dict]:
    users = UserRepository(db)
    profile_repo = LawyerRepository(db)
    profile = await profile_repo.find_by_user_id(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer profile not found"
        )
    user = await users.find_by_id(user_id) or {}
    return profile, user


def _strip_verification_document(items: list[dict]) -> None:
    for item in items:
        item.pop("verification_document_id", None)


class LawyerVerificationDocumentLink(BaseModel):
    document_id: str


@router.get("", response_model=LawyerProfileListResponse)
async def search_lawyers(
    db: AsyncIOMotorDatabase = Depends(require_db),
    q: str | None = None,
    category: str | None = None,
    city: str | None = None,
    min_rating: float | None = None,
    verified_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.schemas.lawyer import LegalCategory

    cat = None
    if category:
        try:
            cat = LegalCategory(category)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid category: {category}",
            ) from exc
    repo = LawyerRepository(db)
    q = (q or "").strip() or None
    result = await repo.search(
        q=q,
        category=cat,
        city=(city or "").strip() or None,
        min_rating=min_rating,
        verified_only=verified_only,
        page=page,
        page_size=page_size,
    )
    user_ids = [p["user_id"] for p in result["items"]]
    users = await UserRepository(db).find_by_ids(user_ids)
    user_map = {str(u["_id"]): u for u in users}
    items = [
        serialize_lawyer_profile(p, user_map.get(p["user_id"]))
        for p in result["items"]
    ]
    _strip_verification_document(items)
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.get("/{user_id}", response_model=LawyerProfileResponse)
async def get_lawyer_profile(
    user_id: str, db: AsyncIOMotorDatabase = Depends(require_db)
):
    profile, user = await _get_lawyer_profile_for_user(db, user_id)
    data = serialize_lawyer_profile(profile, user)
    _strip_verification_document([data])
    return LawyerProfileResponse.model_validate(data)


@router.get("/me/profile")
async def get_my_lawyer_profile(
    user: Annotated[dict, Depends(require_roles(UserRole.LAWYER))],
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    profile, account = await _get_lawyer_profile_for_user(db, user["id"])
    return serialize_lawyer_profile(profile, account)


@router.put("/me/profile")
async def upsert_my_lawyer_profile(
    payload: LawyerProfileCreate,
    user: Annotated[dict, Depends(require_roles(UserRole.LAWYER))],
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    profile_repo = LawyerRepository(db)
    profile = await profile_repo.find_by_user_id(user["id"])
    if profile is not None and profile.get("verification_status") == LawyerStatus.ACTIVE.value:
        # Editing an approved profile is allowed, but we keep its verification status.
        pass

    fields = payload.model_dump()
    await profile_repo.upsert(user["id"], fields)
    account = await UserRepository(db).find_by_id(user["id"]) or {}
    final = await profile_repo.find_by_user_id(user["id"]) or {}
    return serialize_lawyer_profile(final, account)


@router.patch("/me/profile")
async def update_my_lawyer_profile(
    payload: LawyerProfileUpdate,
    user: Annotated[dict, Depends(require_roles(UserRole.LAWYER))],
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    profile_repo = LawyerRepository(db)
    profile = await profile_repo.find_by_user_id(user["id"])
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer profile not found"
        )
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    await profile_repo.update(user["id"], fields)
    account = await UserRepository(db).find_by_id(user["id"]) or {}
    final = await profile_repo.find_by_user_id(user["id"]) or {}
    return serialize_lawyer_profile(final, account)


@router.put("/me/verification-document")
async def link_verification_document(
    payload: LawyerVerificationDocumentLink,
    user: Annotated[dict, Depends(require_roles(UserRole.LAWYER))],
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    profile_repo = LawyerRepository(db)
    profile = await profile_repo.find_by_user_id(user["id"])
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create your lawyer profile before uploading verification documents",
        )
    docs = DocumentRepository(db)
    doc = await docs.find_by_id(payload.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.get("owner_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Only the owner can attach a document to their profile"
        )
    if doc.get("doc_type") != "verification":
        raise HTTPException(
            status_code=422,
            detail="Only verification documents can be attached to a lawyer profile",
        )
    await profile_repo.set_verification_document(user["id"], payload.document_id)
    account = await UserRepository(db).find_by_id(user["id"]) or {}
    final = await profile_repo.find_by_user_id(user["id"]) or {}
    return serialize_lawyer_profile(final, account)
