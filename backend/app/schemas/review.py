from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.platform import LegalCategory


class ReviewCreate(BaseModel):
    lawyer_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=3000)


class ReviewResponse(BaseModel):
    id: str
    lawyer_id: str
    lawyer_name: str = ""
    reviewer_id: str
    reviewer_name: str = ""
    rating: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def serialize_review(doc: dict[str, Any]) -> dict[str, Any]:
    if doc is None:
        return {}
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc
