from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, require_db
from app.models.user import UserStatus
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_block_repository import UserBlockRepository
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
    db: AsyncSession = Depends(require_db),
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
    db: AsyncSession = Depends(require_db),
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
    if await UserBlockRepository(db).either_blocked(user["id"], other_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot message this user",
        )

    chat = ChatService(ConversationRepository(db), MessageRepository(db))
    conversation = await chat.get_or_create_conversation([user["id"], other_id])

    # Reopening a chat the caller previously deleted must bring it back for them
    # so it reappears in their conversation list.
    await ConversationRepository(db).set_hidden(conversation["_id"], user["id"], False)

    if body.initial_message:
        await chat.send_message(
            conversation=conversation,
            sender_id=user["id"],
            recipient_id=other_id,
            content=body.initial_message,
        )

    peers = [{"id": other_id, "name": other.get("name", ""), "role": other.get("role", "")}]
    return serialize_conversation(conversation, user["id"], peers)


async def _load_participant_conversation(db, conversation_id: str, user: dict):
    conv = await ConversationRepository(db).find_by_id(conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    if user["id"] not in conv.get("participants", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation",
        )
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    """Delete (hide) a conversation for the calling user only."""
    await _load_participant_conversation(db, conversation_id, user)
    await ConversationRepository(db).set_hidden(conversation_id, user["id"], True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{conversation_id}/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_conversation(
    conversation_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(require_db),
):
    """Clear the message history of a conversation for the calling user only."""
    await _load_participant_conversation(db, conversation_id, user)
    await ConversationRepository(db).set_cleared(conversation_id, user["id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)
