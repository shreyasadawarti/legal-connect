import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.compat import new_id, utcnow
from app.db.models import Conversation, ConversationParticipant
from app.db.session import session_scope
from app.repositories.conversation_repository import (
    ConversationRepository,
    pair_key,
)
from app.repositories.message_repository import MessageRepository
from app.services.chat_service import ChatService
from app.tests.helpers import auth_headers, register_user


@pytest.fixture
async def chat_users(client):
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    return client, alice, bob


async def test_create_conversation(chat_users):
    client, alice, bob = chat_users
    resp = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["peer"]["id"] == bob["user"]["id"]
    assert body["peer"]["name"] == "Bob"
    assert body["type"] == "direct"


async def test_create_conversation_with_self_rejected(chat_users):
    client, alice, _ = chat_users
    resp = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": alice["user"]["id"]},
    )
    assert resp.status_code == 400


async def test_create_conversation_missing_user_not_found(chat_users):
    client, alice, _ = chat_users
    resp = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": "000000000000000000000000"},
    )
    assert resp.status_code == 404


async def test_create_conversation_with_initial_message(chat_users):
    client, alice, bob = chat_users
    resp = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={
            "other_user_id": bob["user"]["id"],
            "initial_message": "Hello Bob",
        },
    )
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    history = await client.get(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(alice),
    )
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) == 1
    assert items[0]["content"] == "Hello Bob"
    assert items[0]["sender_id"] == alice["user"]["id"]


async def test_get_or_create_returns_existing_conversation(chat_users):
    client, alice, bob = chat_users
    first = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    second = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(bob),
        json={"other_user_id": alice["user"]["id"]},
    )
    assert first.json()["id"] == second.json()["id"]


async def test_list_conversations_shows_peer(chat_users):
    client, alice, bob = chat_users
    await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"], "initial_message": "hi"},
    )
    resp = await client.get("/api/v1/conversations", headers=auth_headers(alice))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["peer"]["id"] == bob["user"]["id"]


async def test_send_and_list_and_mark_read(chat_users):
    client, alice, bob = chat_users
    conv = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    conv_id = conv.json()["id"]

    sent = await client.post(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(alice),
        json={"content": "Are you available?"},
    )
    assert sent.status_code == 200
    assert sent.json()["content"] == "Are you available?"

    bob_list = await client.get("/api/v1/conversations", headers=auth_headers(bob))
    assert bob_list.json()["items"][0]["unread_count"] == 1

    read = await client.post(
        f"/api/v1/messages/{conv_id}/read",
        headers=auth_headers(bob),
    )
    assert read.status_code == 200

    bob_list2 = await client.get("/api/v1/conversations", headers=auth_headers(bob))
    assert bob_list2.json()["items"][0]["unread_count"] == 0


async def test_non_participant_cannot_send(chat_users):
    client, alice, bob = chat_users
    conv = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    conv_id = conv.json()["id"]
    eve = await register_user(client, name="Eve", email="eve@example.com")
    resp = await client.post(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(eve),
        json={"content": "intruder"},
    )
    assert resp.status_code == 403


async def test_non_participant_cannot_list_messages(chat_users):
    client, alice, bob = chat_users
    conv = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    conv_id = conv.json()["id"]
    eve = await register_user(client, name="Eve2", email="eve2@example.com")
    resp = await client.get(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(eve),
    )
    assert resp.status_code == 403


async def test_missing_conversation_returns_404(chat_users):
    client, alice, _ = chat_users
    resp = await client.get(
        "/api/v1/messages/000000000000000000000000",
        headers=auth_headers(alice),
    )
    assert resp.status_code == 404


async def test_duplicate_direct_pair_is_rejected_by_schema(chat_users, db):
    """One direct conversation per pair is now a database guarantee.

    MongoDB relied on application-level array matching to avoid duplicates, so
    the old test inserted two rows and asserted the list endpoint deduplicated
    them. The UNIQUE `pair_key` column makes the duplicate impossible, so that
    is what this asserts now -- a stronger guarantee, not a weaker test.
    """
    client, alice, bob = chat_users
    repo = ConversationRepository(db)
    participants = sorted([alice["user"]["id"], bob["user"]["id"]])

    await repo.create(participants)
    await db.commit()

    with pytest.raises(IntegrityError):
        db.add(
            Conversation(
                id=new_id(),
                type="direct",
                pair_key=pair_key(participants),
                last_message="",
                last_message_at=utcnow(),
                created_at=utcnow(),
                participants=[
                    ConversationParticipant(user_id=uid, position=idx)
                    for idx, uid in enumerate(participants)
                ],
            )
        )
        await db.commit()
    await db.rollback()

    resp = await client.get("/api/v1/conversations", headers=auth_headers(alice))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["total"] == 1


async def test_concurrent_get_or_create_creates_one_conversation(client, db):
    """Two racing requests for the same pair must yield one conversation.

    Each coroutine gets its own session: sharing one AsyncSession across
    concurrent tasks is not safe, and this also exercises the unique constraint
    the way two real HTTP requests would hit it.
    """
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    await db.commit()
    pair = [alice["user"]["id"], bob["user"]["id"]]

    async def attempt() -> dict:
        async with session_scope() as own:
            chat = ChatService(ConversationRepository(own), MessageRepository(own))
            return await chat.get_or_create_conversation(pair)

    first, second = await asyncio.gather(attempt(), attempt())
    assert str(first["_id"]) == str(second["_id"])

    remaining = await ConversationRepository(db).list_all()
    assert len(remaining) == 1


async def test_merge_duplicate_conversations_preserves_messages(client, db):
    """The repair routine for duplicate conversations imported from MongoDB.

    The `uq_conversations_pair_key` index means duplicates can no longer be
    created through the API, so this test drops the index to reconstruct the
    legacy state, runs the merge, and restores the index afterwards. That is
    exactly the situation `merge_duplicate_conversations` exists to fix.
    """
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    carol = await register_user(client, name="Carol", email="carol@example.com")
    await db.commit()

    convos = ConversationRepository(db)
    msgs = MessageRepository(db)
    u1, u2, u3 = alice["user"]["id"], bob["user"]["id"], carol["user"]["id"]

    await db.execute(text("ALTER TABLE conversations DROP INDEX uq_conversations_pair_key"))
    await db.commit()

    ids = []
    for i in range(3):
        now = utcnow()
        conv = Conversation(
            id=new_id(),
            type="direct",
            pair_key=pair_key(sorted([u1, u2])),
            last_message=f"m{i}",
            last_message_at=now,
            created_at=now,
            participants=[
                ConversationParticipant(user_id=uid, position=idx)
                for idx, uid in enumerate(sorted([u1, u2]))
            ],
        )
        db.add(conv)
        ids.append(conv.id)
    # Distinct pair, so this one must survive untouched.
    other = await convos.create([u1, u3], last_message="unrelated")

    for i in range(3):
        await msgs.create(
            conversation_id=ids[i],
            sender_id=u1,
            recipient_id=u2,
            content=f"msg-{i}",
        )
    await msgs.create(
        conversation_id=str(other["_id"]),
        sender_id=u1,
        recipient_id=u3,
        content="unrelated",
    )
    await db.commit()

    chat = ChatService(convos, msgs)
    removed = await chat.merge_duplicate_conversations()
    assert removed == 2

    remaining = await convos.list_all()
    assert len(remaining) == 2
    assert str(other["_id"]) in {str(c["_id"]) for c in remaining}
    keeper_id = next(str(c["_id"]) for c in remaining if str(c["_id"]) != str(other["_id"]))

    keeper_messages = await msgs.list_for_conversation(keeper_id, page_size=100)
    other_messages = await msgs.list_for_conversation(str(other["_id"]), page_size=100)
    moved = [m for m in keeper_messages["items"] if m["content"].startswith("msg-")]
    assert len(moved) == 3
    assert all(m["conversation_id"] == keeper_id for m in moved)
    assert [m["content"] for m in other_messages["items"]] == ["unrelated"]

    await db.execute(
        text("ALTER TABLE conversations ADD UNIQUE INDEX uq_conversations_pair_key (pair_key)")
    )
    await db.commit()
