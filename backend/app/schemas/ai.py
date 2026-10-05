from typing import Any, Optional

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: Optional[list[dict[str, str]]] = None


class AiChatResponse(BaseModel):
    reply: str


class AiSummarizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=60000)


class AiSummarizeResponse(BaseModel):
    summary: str


class AiFaqRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AiFaqResponse(BaseModel):
    answer: str
    related_categories: list[str] = Field(default_factory=list)
    suggested_action: str = ""


class AiPredictRequest(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    categories: Optional[list[str]] = None


class AiPredictResponse(BaseModel):
    category: str
    confidence: float = 0.0
    explanation: str = ""


class AiRecommendRequest(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=5, ge=1, le=20)


class AiRecommendResponse(BaseModel):
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


class AiTranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    target_language: str = Field(min_length=1, max_length=100)


class AiTranslateResponse(BaseModel):
    translated: str
