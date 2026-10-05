from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import CurrentUser, require_db
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.user_repository import UserRepository
from app.schemas.review import ReviewCreate, ReviewResponse, serialize_review

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def _refresh_lawyer_rating(db: AsyncSession, lawyer_id: str) -> None:
    reviews = ReviewRepository(db)
    stats = await reviews.rating_average(lawyer_id)
    await LawyerRepository(db).update_rating(lawyer_id, stats["avg"], stats["count"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    if user["id"] == payload.lawyer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot review yourself",
        )
    lawyer_profile = await LawyerRepository(db).find_by_user_id(payload.lawyer_id)
    if lawyer_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer profile not found"
        )
    reviews = ReviewRepository(db)
    existing = await reviews.find_by_user_and_lawyer(user["id"], payload.lawyer_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this lawyer",
        )
    doc = await reviews.create(
        lawyer_id=payload.lawyer_id,
        reviewer_id=user["id"],
        rating=payload.rating,
        comment=payload.comment,
    )
    await _refresh_lawyer_rating(db, payload.lawyer_id)
    return ReviewResponse.model_validate(serialize_review(doc))


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    reviews = ReviewRepository(db)
    review = await reviews.find_by_id(review_id)
    if review is None or review["reviewer_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    await reviews.delete(review_id)
    await _refresh_lawyer_rating(db, review["lawyer_id"])


@router.get("/{lawyer_id}")
async def list_lawyer_reviews(
    lawyer_id: str,
    db: AsyncSession = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    reviews = ReviewRepository(db)
    result = await reviews.list_for_lawyer(lawyer_id, page=page, page_size=page_size)
    reviewer_ids = [doc["reviewer_id"] for doc in result["items"]]
    users = await UserRepository(db).find_by_ids(reviewer_ids)
    name_map = {str(u["_id"]): u.get("name", "") for u in users}
    items = []
    for doc in result["items"]:
        r = serialize_review(doc)
        r["reviewer_name"] = name_map.get(doc["reviewer_id"], "")
        items.append(r)
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }

