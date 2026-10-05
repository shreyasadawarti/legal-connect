from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import require_db
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
from app.schemas.lawyer import serialize_lawyer_profile
from app.services.ai_service import AIError

router = APIRouter(prefix="/ai", tags=["ai"])

CATEGORY_KEYS = [c.value for c in LegalCategory]


def _get_ai():
    from app.services.ai_service import ai_service

    return ai_service


def _ai_error(exc: AIError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
    )


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(
    payload: AiChatRequest,
    ai=Depends(_get_ai),
):
    try:
        reply = await ai.chat(payload.message, payload.history)
    except AIError as exc:
        raise _ai_error(exc) from exc
    return AiChatResponse(reply=reply)


@router.post("/summarize", response_model=AiSummarizeResponse)
async def ai_summarize(
    payload: AiSummarizeRequest,
    ai=Depends(_get_ai),
):
    try:
        summary = await ai.summarize(payload.text)
    except AIError as exc:
        raise _ai_error(exc) from exc
    return AiSummarizeResponse(summary=summary)


@router.post("/faq", response_model=AiFaqResponse)
async def ai_faq(
    payload: AiFaqRequest,
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
async def ai_predict_category(
    payload: AiPredictRequest,
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
async def ai_recommend_lawyers(
    payload: AiRecommendRequest,
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
        serialize_lawyer_profile(p, user_map.get(p["user_id"]))
        for p in search["items"]
    ]
    return AiRecommendResponse(recommendations=items)


@router.post("/translate", response_model=AiTranslateResponse)
async def ai_translate(
    payload: AiTranslateRequest,
    ai=Depends(_get_ai),
):
    try:
        translated = await ai.translate(payload.text, payload.target_language)
    except AIError as exc:
        raise _ai_error(exc) from exc
    return AiTranslateResponse(translated=translated)


@router.get("/nearby-lawyers")
async def ai_nearby_lawyers(
    db: AsyncSession = Depends(require_db),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[float] = Query(None, ge=1, le=20000),
    verified_only: bool = False,
    limit: int = Query(100, ge=1, le=200),
):
    repo = LawyerRepository(db)
    docs = await repo.list_with_geo(
        radius_km=radius_km,
        lat=lat,
        lng=lng,
        verified_only=verified_only,
        limit=limit,
    )
    user_ids = [p["user_id"] for p in docs]
    users = await UserRepository(db).find_by_ids(user_ids)
    user_map = {str(u["_id"]): u for u in users}
    items = [
        serialize_lawyer_profile(p, user_map.get(p["user_id"]))
        for p in docs
    ]
    return {"items": items, "total": len(items)}
