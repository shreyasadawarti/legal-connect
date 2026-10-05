from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentShareRequest(BaseModel):
    user_ids: list[str] = Field(min_length=1, max_length=50)


class DocumentResponse(BaseModel):
    id: str
    owner_id: str
    owner_name: str = ""
    title: str
    original_name: str
    mime_type: str
    size_bytes: int
    public_id: str
    resource_type: str = "raw"
    related_appointment_id: Optional[str] = None
    doc_type: str = "general"
    shared_with: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


def serialize_document(
    doc: dict[str, Any],
    owner_name: str = "",
) -> dict[str, Any]:
    d = dict(doc)
    d["id"] = str(d.pop("_id", ""))
    d["owner_name"] = owner_name
    d["shared_with"] = d.get("shared_with", [])
    d.setdefault("original_name", d.get("filename", ""))
    return d
