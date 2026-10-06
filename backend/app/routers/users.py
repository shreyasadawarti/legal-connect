import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_document_storage, require_db
from app.repositories.user_repository import UserRepository, serialize_user
from app.schemas.user import ProfileUpdate, UserProfileResponse
from app.services.cloudinary_service import DocumentStorageError

logger = logging.getLogger("legalconnect.users")

router = APIRouter(prefix="/users", tags=["users"])

MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024

PROFILE_PICTURE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.get("/lookup")
async def lookup_user(
    email: str = Query(..., min_length=3),
    db: AsyncSession = Depends(require_db),
):
    repo = UserRepository(db)
    user = await repo.find_by_email(email.lower())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No user found with that email"
        )
    return {"id": str(user["_id"]), "name": user.get("name", "")}


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(user: CurrentUser):
    return UserProfileResponse.model_validate(user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    payload: ProfileUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    repo = UserRepository(db)
    fields = {
        k: v
        for k, v in payload.model_dump(exclude_unset=True).items()
if v is not None
    }
    updated = await repo.update(user["id"], fields)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserProfileResponse.model_validate(serialize_user(updated))


def _storage_error(exc: DocumentStorageError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


async def _discard_old_picture(storage, public_id: str | None) -> None:
    """Delete a replaced picture, never failing the request over cleanup.

    The new picture is already stored and saved by the time this runs, so a
    Cloudinary hiccup here can only leak one orphaned asset, which is far
    better than returning an error after a successful upload.
    """
    if not public_id:
        return
    try:
        await storage.delete(public_id, "image")
    except DocumentStorageError:
        logger.warning("Could not delete replaced profile picture %s", public_id)


@router.post("/me/profile-picture", response_model=UserProfileResponse)
async def upload_my_profile_picture(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    storage=Depends(get_document_storage),
    file: UploadFile = File(...),
):
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_PROFILE_PICTURE_BYTES:
        raise HTTPException(
            status_code=413, detail="Profile picture is too large (max 5 MB)"
        )
    mime = (file.content_type or "application/octet-stream").lower()
    if mime not in PROFILE_PICTURE_MIME_TYPES:
        raise HTTPException(
            status_code=422, detail="Profile picture must be a PNG, JPG, or WebP file"
        )
    try:
        meta = await storage.upload_bytes(
            data=content,
            filename=file.filename or "profile-picture",
            resource_type="image",
        )
    except DocumentStorageError as exc:
        raise _storage_error(exc) from exc

    previous_public_id = user.get("profile_picture_public_id")
    repo = UserRepository(db)
    updated = await repo.update(
        user["id"],
        {
            "profile_picture_url": meta.get("secure_url") or meta.get("url") or "",
            "profile_picture_public_id": meta.get("public_id", ""),
        },
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await _discard_old_picture(storage, previous_public_id)
    return UserProfileResponse.model_validate(serialize_user(updated))


@router.delete("/me/profile-picture", response_model=UserProfileResponse)
async def remove_my_profile_picture(
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    storage=Depends(get_document_storage),
):
    """Clear the profile picture.

    A dedicated endpoint rather than a `PATCH /me` field because that handler
    drops `None` values, so it can never clear a stored column.
    """
    updated = await UserRepository(db).update(
        user["id"], {"profile_picture_url": None, "profile_picture_public_id": None}
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await _discard_old_picture(storage, user.get("profile_picture_public_id"))
    return UserProfileResponse.model_validate(serialize_user(updated))

