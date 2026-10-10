from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.platform import LegalCategory


class ReviewCreate(BaseModel):
    lawyer_id: str
    appointment_id: Optional[str] = Field(default=None, min_length=24, max_length=24)
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def _require_written_review(self) -> "ReviewCreate":
        # Appointment reviews must carry a written comment as well as a rating.
        if self.appointment_id and not (self.comment and self.comment.strip()):
            raise ValueError("A written review is required")
        return self


class ReviewResponse(BaseModel):
    id: str
    lawyer_id: str
    lawyer_name: str = ""
    reviewer_id: str
    reviewer_name: str = ""
    appointment_id: Optional[str] = None
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
