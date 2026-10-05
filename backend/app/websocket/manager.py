import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

from app.database import get_database
from app.dependencies import decode_token
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import serialize_message
from app.services.chat_service import ChatService
from app.models.user import UserStatus

logger = logging.getLogger("legalconnect.websocket")

SIGNALING_TYPES = {"call-request", "offer", "answer", "ice", "call-decline", "call-end"}


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def user_count(self, user_id: str) -> int:
        return len(self._connections.get(user_id, ()))

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        self._connections.get(user_id, set()).discard(websocket)
        if not self._connections.get(user_id):
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        sockets = list(self._connections.get(user_id, ()))
        if not sockets:
            return
        text = json_dumps(payload)
        lock = self._locks[user_id]
        async with lock:
            for ws in sockets:
                try:
                    await ws.send_text(text)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("WS send failed to %s: %s", user_id, exc)
                    self._connections.get(user_id, set()).discard(ws)


def json_dumps(payload: dict) -> str:
    import json

    return json.dumps(payload, default=str)


manager = ConnectionManager()


async def _load_peer(db, user_id: str):
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        return None
    return {"id": user_id, "name": user.get("name", ""), "role": user.get("role", "")}


async def websocket_endpoint(websocket: WebSocket) -> None:
    db = get_database()
    if db is None:
        await websocket.close(code=4403, reason="Database not configured")
        return

    token = websocket.query_params.get("token", "")
    try:
        payload = decode_token(token, expected_type="access")
    except Exception:  # noqa: BLE001
        await websocket.close(code=4401, reason="Unauthorized")
        return

    subject = payload.get("sub")
    if not subject:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(subject)
    if not user or user.get("status") != UserStatus.ACTIVE.value:
        await websocket.close(code=4403, reason="Account not active")
        return

    current_user_id = subject
    conversations = ConversationRepository(db)
    messages = MessageRepository(db)
    chat = ChatService(conversations, messages)

    await manager.connect(current_user_id, websocket)
    logger.info("WS connected: user=%s", current_user_id)
    await manager.send_to_user(
        current_user_id,
        {"type": "connected", "user_id": current_user_id},
    )

    try:
        while True:
            raw = await websocket.receive_text()
            import json

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:  # noqa: BLE001
                await manager.send_to_user(
                    current_user_id,
                    {"type": "error", "error": "Malformed message"},
                )
                continue

            msg_type = data.get("type", "")
            conversation_id = data.get("conversation_id", "")

            if msg_type == "text":
                conversation = await conversations.find_by_id(conversation_id)
                if not conversation or current_user_id not in conversation.get("participants", []):
                    await manager.send_to_user(
                        current_user_id,
                        {"type": "error", "error": "Conversation not found"},
                    )
                    continue
                content = str(data.get("content", "")).strip()
                if not content:
                    continue
                recipient_id = next(
                    (p for p in conversation["participants"] if p != current_user_id), None
                )
                if not recipient_id:
                    continue
                message = await chat.send_message(
                    conversation=conversation,
                    sender_id=current_user_id,
                    recipient_id=recipient_id,
                    content=content,
                    message_type=str(data.get("message_type", "text")),
                )
                serialized = serialize_message(message)
                await manager.send_to_user(
                    current_user_id,
                    {"type": "message", "message": serialized, "status": "delivered"},
                )
                await manager.send_to_user(
                    recipient_id,
                    {"type": "message", "message": serialized, "status": "sent"},
                )
                await manager.send_to_user(
                    recipient_id,
                    {"type": "notice", "conversation_id": conversation_id},
                )
                continue

            if msg_type == "read":
                conv = await conversations.find_by_id(conversation_id) if conversation_id else None
                if conv and current_user_id in conv.get("participants", []):
                    await messages.mark_read(conversation_id, current_user_id)
                    peer = next(
                        (p for p in conv["participants"] if p != current_user_id), None
                    )
                    if peer:
                        await manager.send_to_user(
                            peer,
                            {"type": "read", "conversation_id": conversation_id, "reader_id": current_user_id},
                        )
                continue

            if msg_type == "typing":
                conv = await conversations.find_by_id(conversation_id) if conversation_id else None
                if conv and current_user_id in conv.get("participants", []):
                    peer = next(
                        (p for p in conv["participants"] if p != current_user_id), None
                    )
                    if peer:
                        await manager.send_to_user(
                            peer,
                            {"type": "typing", "conversation_id": conversation_id, "user_id": current_user_id},
                        )
                continue

            if msg_type in SIGNALING_TYPES:
                conv = await conversations.find_by_id(conversation_id) if conversation_id else None
                if conv and current_user_id in conv.get("participants", []):
                    peer = next(
                        (p for p in conv["participants"] if p != current_user_id), None
                    )
                    if peer:
                        await manager.send_to_user(
                            peer,
                            {
                                "type": msg_type,
                                "conversation_id": conversation_id,
                                "from_user_id": current_user_id,
                                "sdp": data.get("sdp"),
                                "candidate": data.get("candidate"),
                                "to_user_id": data.get("to_user_id") or peer,
                            },
                        )
                continue

            await manager.send_to_user(
                current_user_id,
                {"type": "error", "error": f"Unknown message type: {msg_type}"},
            )
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(current_user_id, websocket)
        logger.info("WS disconnected: user=%s", current_user_id)
