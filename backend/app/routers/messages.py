from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import CurrentUser, require_db
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import (
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
    serialize_message,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/messages", tags=["messages"])


async def _get_conversation(db, conversation_id: str, user: dict):
    convos = ConversationRepository(db)
    conv = await convos.find_by_id(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    if user["id"] not in conv.get("participants", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation",
        )
    return conv


@router.get("/{conversation_id}", response_model=MessageListResponse)
async def list_messages(
    conversation_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
    before: Optional[str] = Query(None),
    page_size: int = Query(50, ge=1, le=100),
):
    conv = await _get_conversation(db, conversation_id, user)
    messages = MessageRepository(db)
    result = await messages.list_for_conversation(conversation_id, before, page_size)
    return {
        "items": [serialize_message(m) for m in result["items"]],
        "has_more": result["has_more"],
        "conversation_id": conversation_id,
    }


@router.post("/{conversation_id}", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    conv = await _get_conversation(db, conversation_id, user)
    recipient_id = next(
        (p for p in conv.get("participants", []) if p != user["id"]), None
    )
    if not recipient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation has only one participant",
        )
    chat = ChatService(ConversationRepository(db), MessageRepository(db))
    message = await chat.send_message(
        conversation=conv,
        sender_id=user["id"],
        recipient_id=recipient_id,
        content=body.content,
        message_type=body.message_type,
    )
    return serialize_message(message)


@router.post("/{conversation_id}/read")
async def mark_read(
    conversation_id: str,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    await _get_conversation(db, conversation_id, user)
    messages = MessageRepository(db)
    await messages.mark_read(conversation_id, user["id"])
    return {"status": "ok"}
