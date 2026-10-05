from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    other_user_id: str = Field(min_length=1)
    initial_message: Optional[str] = Field(default=None, max_length=4000)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    message_type: str = "text"


class PeerInfo(BaseModel):
    id: str
    name: str
    role: str = ""


class ConversationResponse(BaseModel):
    id: str
    type: str = "direct"
    peers: list[PeerInfo]
    peer: Optional[PeerInfo] = None
    last_message: str = ""
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    recipient_id: str
    content: str
    message_type: str = "text"
    is_read: bool = False
    created_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    has_more: bool = False
    conversation_id: str


def serialize_message(msg: dict[str, Any]) -> dict[str, Any]:
    m = dict(msg)
    m["id"] = str(m.pop("_id", ""))
    m["conversation_id"] = str(m.get("conversation_id", ""))
    return m


def serialize_conversation(
    conv: dict[str, Any],
    current_user_id: str,
    peers: list[dict[str, Any]],
    unread_count: int = 0,
) -> dict[str, Any]:
    c = dict(conv)
    c["id"] = str(c.pop("_id", ""))
    c["peers"] = [
        {"id": p.get("id", ""), "name": p.get("name", ""), "role": p.get("role", "")}
        for p in peers
        if p.get("id") != current_user_id
    ]
    c["peer"] = c["peers"][0] if c["peers"] else None
    c["unread_count"] = unread_count
    return c
