from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, require_db
from app.middleware.rate_limit import limiter
from app.models.platform import LegalCategory
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai import (
    AiChatRequest,
    AiChatResponse,
    AiFaqRequest,
    AiFaqResponse,
    AiPredictRequest,
    AiPredictResponse,
    AiRecommendRequest,
    AiRecommendResponse,
    AiSummarizeRequest,
    AiSummarizeResponse,
    AiTranslateRequest,
    AiTranslateResponse,
)
from app.schemas.lawyer import redact_lawyer_contact, serialize_lawyer_profile
from app.services.ai_service import AIError

router = APIRouter(prefix="/ai", tags=["ai"])

CATEGORY_KEYS = [c.value for c in LegalCategory]

AI_RATE_LIMIT = "30/minute"


def _get_ai():
    from app.services.ai_service import ai_service

    return ai_service


def _ai_error(exc: AIError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
    )


@router.post("/chat", response_model=AiChatResponse)
@limiter.limit(AI_RATE_LIMIT)
async def ai_chat(
    request: Request,
    payload: AiChatRequest,
    user: CurrentUser,
    ai=Depends(_get_ai),
):
    try:
        reply = await ai.chat(payload.message, payload.history)
    except AIError as exc:
        raise _ai_error(exc) from exc
    return AiChatResponse(reply=reply)


@router.post("/summarize", response_model=AiSummarizeResponse)
@limiter.limit(AI_RATE_LIMIT)
async def ai_summarize(
    request: Request,
    payload: AiSummarizeRequest,
    user: CurrentUser,
    ai=Depends(_get_ai),
):
    try:
        summary = await ai.summarize(payload.text)
    except AIError as exc:
        raise _ai_error(exc) from exc
    return AiSummarizeResponse(summary=summary)


@router.post("/faq", response_model=AiFaqResponse)
@limiter.limit(AI_RATE_LIMIT)
async def ai_faq(
    request: Request,
    payload: AiFaqRequest,
    user: CurrentUser,
    ai=Depends(_get_ai),
):
    try:
        result = await ai.answer_faq(payload.question)
    except AIError as exc:
        raise _ai_error(exc) from exc
    related = [c for c in (result.get("related_categories") or []) if c in CATEGORY_KEYS]
    return AiFaqResponse(
        answer=result.get("answer", ""),
        related_categories=related,
        suggested_action=result.get("suggested_action", "") or "",
    )


@router.post("/predict-category", response_model=AiPredictResponse)
@limiter.limit(AI_RATE_LIMIT)
async def ai_predict_category(
    request: Request,
    payload: AiPredictRequest,
    user: CurrentUser,
    ai=Depends(_get_ai),
):
    categories = [c for c in (payload.categories or CATEGORY_KEYS) if c in CATEGORY_KEYS]
    if not categories:
        categories = CATEGORY_KEYS
    try:
        result = await ai.predict_category(payload.description, categories)
    except AIError as exc:
        raise _ai_error(exc) from exc
    category = result.get("category", "")
    if category not in categories:
        category = categories[0]
    confidence = float(result.get("confidence") or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    return AiPredictResponse(
        category=category,
        confidence=confidence,
        explanation=result.get("explanation", ""),
    )


@router.post("/recommend-lawyers", response_model=AiRecommendResponse)
@limiter.limit(AI_RATE_LIMIT)
async def ai_recommend_lawyers(
    request: Request,
    payload: AiRecommendRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    ai=Depends(_get_ai),
):
    repo = LawyerRepository(db)
    try:
        result = await ai.predict_category(payload.description, CATEGORY_KEYS)
    except AIError as exc:
        raise _ai_error(exc) from exc
    category = result.get("category", "")
    if category not in CATEGORY_KEYS:
        category = LegalCategory.OTHER.value
    try:
        legal_cat = LegalCategory(category)
    except ValueError:
        legal_cat = LegalCategory.OTHER
    search = await repo.search(
        category=legal_cat, verified_only=False, page=1, page_size=payload.limit
    )
    user_ids = [p["user_id"] for p in search["items"]]
    users = await UserRepository(db).find_by_ids(user_ids)
    user_map = {str(u["_id"]): u for u in users}
    items = [
        redact_lawyer_contact(serialize_lawyer_profile(p, user_map.get(p["user_id"])))
        for p in search["items"]
    ]
    return AiRecommendResponse(recommendations=items)


@router.post("/translate", response_model=AiTranslateResponse)
@limiter.limit(AI_RATE_LIMIT)
async def ai_translate(
    request: Request,
    payload: AiTranslateRequest,
    user: CurrentUser,
    ai=Depends(_get_ai),
):
    try:
        translated = await ai.translate(payload.text, payload.target_language)
    except AIError as exc:
        raise _ai_error(exc) from exc
    return AiTranslateResponse(translated=translated)


@router.get("/nearby-lawyers")
@limiter.limit(AI_RATE_LIMIT)
async def ai_nearby_lawyers(
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[float] = Query(None, ge=1, le=20000),
    verified_only: bool = False,
    sort: str = Query("rating", pattern="^(rating|distance)$"),
    limit: int = Query(100, ge=1, le=200),
):
    repo = LawyerRepository(db)
    if lat is not None and lng is not None:
        # Back-fill real office coordinates for lawyers who only published a
        # city name (e.g. "Nagpur"). Best-effort: profiles that cannot be
        # resolved simply stay out of the distance-based results.
        from app.services.geocoding_service import ensure_missing_coordinates

        await ensure_missing_coordinates(db)
    docs = await repo.list_with_geo(
        radius_km=radius_km,
        lat=lat,
        lng=lng,
        verified_only=verified_only,
        sort=sort,
        limit=limit,
    )
    user_ids = [p["user_id"] for p in docs]
    users = await UserRepository(db).find_by_ids(user_ids)
    user_map = {str(u["_id"]): u for u in users}
    items = [
        redact_lawyer_contact(serialize_lawyer_profile(p, user_map.get(p["user_id"])))
        for p in docs
    ]
    return {"items": items, "total": len(items)}
