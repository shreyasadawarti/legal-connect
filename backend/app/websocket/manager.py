import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

from app.dependencies import decode_token
from app.db.compat import utcnow
from app.db.session import session_scope
from app.models.platform import AppointmentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_block_repository import UserBlockRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import serialize_message
from app.services.chat_service import ChatService
from app.models.user import UserStatus

logger = logging.getLogger("legalconnect.websocket")

SIGNALING_TYPES = {"call-request", "offer", "answer", "ice", "call-decline", "call-end"}
APPOINTMENT_CALL_TYPES = {"call-request", "call-end", "call-decline"}


def call_signal_target(appointment: dict | None, sender_id: str) -> str | None:
    """The other participant of a confirmed appointment, or None.

    Returns None when the appointment is missing, is not confirmed, or the
    sender is not one of its participants, so a call signal can only ever reach
    the correct counterpart of a confirmed appointment.
    """
    if not appointment or appointment.get("status") != AppointmentStatus.CONFIRMED.value:
        return None
    client_id = appointment.get("client_id")
    lawyer_id = appointment.get("lawyer_id")
    if sender_id == client_id:
        return lawyer_id
    if sender_id == lawyer_id:
        return client_id
    return None


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

    current_user_id = subject
    token_ver = payload.get("ver", 0)
    # A short-lived session authenticates the socket, then closes. Holding one
    # SQLAlchemy session open for the socket's whole lifetime would let its
    # identity map and transaction go stale, so every inbound frame below gets
    # its own session instead.
    async with session_scope() as db:
        user = await UserRepository(db).find_by_id(current_user_id)
        if not user or user.get("status") != UserStatus.ACTIVE.value:
            await websocket.close(code=4403, reason="Account not active")
            return
        # Mirror the HTTP layer: a password reset / logout bumps auth_version,
        # which must also invalidate any still-open socket for the old session.
        if int(token_ver) != int(user.get("auth_version", 0)):
            await websocket.close(code=4401, reason="Session expired")
            return

    await manager.connect(current_user_id, websocket)
    logger.info("WS connected: user=%s", current_user_id)
    await manager.send_to_user(
        current_user_id,
        {"type": "connected", "user_id": current_user_id},
    )

    # Anything queued while this user was offline is now reachable on a live
    # device, so mark it delivered and let each sender update its ticks.
    async with session_scope() as db:
        just_delivered = await MessageRepository(db).mark_all_delivered_for_recipient(
            current_user_id
        )
    for sender_id, delivered_conversation_id in just_delivered:
        await manager.send_to_user(
            sender_id,
            {
                "type": "delivered",
                "conversation_id": delivered_conversation_id,
                "user_id": current_user_id,
            },
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

            appointment_id = str(data.get("appointment_id", "") or "")
            if msg_type in APPOINTMENT_CALL_TYPES and appointment_id:
                async with session_scope() as db:
                    appointment = await AppointmentRepository(db).find_by_id(appointment_id)
                    sender = await UserRepository(db).find_by_id(current_user_id)
                target = call_signal_target(appointment, current_user_id)
                if target:
                    await manager.send_to_user(
                        target,
                        {
                            "type": msg_type,
                            "appointment_id": appointment_id,
                            "from_user_id": current_user_id,
                            "from_name": (sender or {}).get("name", ""),
                        },
                    )
                continue

            if msg_type == "text":
                async with session_scope() as db:
                    conversations = ConversationRepository(db)
                    messages = MessageRepository(db)
                    chat = ChatService(conversations, messages)
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
                    if await UserBlockRepository(db).either_blocked(
                        current_user_id, recipient_id
                    ):
                        await manager.send_to_user(
                            current_user_id,
                            {"type": "error", "error": "You cannot message this user"},
                        )
                        continue
                    message = await chat.send_message(
                        conversation=conversation,
                        sender_id=current_user_id,
                        recipient_id=recipient_id,
                        content=content,
                        message_type=str(data.get("message_type", "text")),
                    )
                # Delivered the moment the recipient has a live socket; otherwise
                # it stays merely "sent" until they next come online.
                delivered = manager.user_count(recipient_id) > 0
                if delivered:
                    async with session_scope() as db:
                        await MessageRepository(db).mark_delivered(
                            conversation_id, recipient_id
                        )
                    message["delivered"] = True
                    message["delivered_at"] = utcnow()
                serialized = serialize_message(message)
                await manager.send_to_user(
                    current_user_id,
                    {
                        "type": "message",
                        "message": serialized,
                        "status": "delivered" if delivered else "sent",
                    },
                )
                await manager.send_to_user(
                    recipient_id,
                    {"type": "message", "message": serialized, "status": "sent"},
                )
                await manager.send_to_user(
                    recipient_id,
                    {"type": "notice", "conversation_id": conversation_id},
                )
                if delivered:
                    # Also updates any earlier messages of this conversation that
                    # were still waiting for this recipient to appear.
                    await manager.send_to_user(
                        current_user_id,
                        {
                            "type": "delivered",
                            "conversation_id": conversation_id,
                            "user_id": recipient_id,
                        },
                    )
                continue

            if msg_type == "read":
                async with session_scope() as db:
                    conv = await ConversationRepository(db).find_by_id(conversation_id) if conversation_id else None
                    if conv and current_user_id in conv.get("participants", []):
                        await MessageRepository(db).mark_read(conversation_id, current_user_id)
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
                async with session_scope() as db:
                    conv = await ConversationRepository(db).find_by_id(conversation_id) if conversation_id else None
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
                async with session_scope() as db:
                    conv = await ConversationRepository(db).find_by_id(conversation_id) if conversation_id else None
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
