from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, require_db
from app.repositories.user_repository import UserRepository, serialize_user
from app.schemas.user import ProfileUpdate, UserProfileResponse

router = APIRouter(prefix="/users", tags=["users"])


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

