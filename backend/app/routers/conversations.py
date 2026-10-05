from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import CurrentUser, require_db
from app.models.user import UserStatus
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    serialize_conversation,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    convos = ConversationRepository(db)
    messages = MessageRepository(db)
    users = UserRepository(db)
    result = await convos.list_for_user(user["id"], page, page_size)
    items = []
    for conv in result["items"]:
        peer_ids = [p for p in conv.get("participants", []) if p != user["id"]]
        peers = []
        for pid in peer_ids:
            u = await users.find_by_id(pid)
            if u:
                peers.append(
                    {"id": pid, "name": u.get("name", ""), "role": u.get("role", "")}
                )
        unread = 0
        for pid in peer_ids:
            unread += await messages.count_unread(str(conv["_id"]), user["id"])
        items.append(
            serialize_conversation(conv, user["id"], peers, unread_count=unread)
        )
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: CreateConversationRequest,
    user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(require_db),
):
    other_id = body.other_user_id
    if other_id == user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start a conversation with yourself",
        )
    users = UserRepository(db)
    other = await users.find_by_id(other_id)
    if not other or other.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    chat = ChatService(ConversationRepository(db), MessageRepository(db))
    conversation = await chat.get_or_create_conversation([user["id"], other_id])

    if body.initial_message:
        await chat.send_message(
            conversation=conversation,
            sender_id=user["id"],
            recipient_id=other_id,
            content=body.initial_message,
        )

    peers = [{"id": other_id, "name": other.get("name", ""), "role": other.get("role", "")}]
    return serialize_conversation(conversation, user["id"], peers)
