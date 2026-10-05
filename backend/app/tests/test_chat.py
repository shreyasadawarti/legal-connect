import asyncio
from datetime import datetime, timezone

import pytest

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


async def test_list_conversations_dedups_duplicate_pairs(chat_users, fake_db):
    client, alice, bob = chat_users
    convos = fake_db["conversations"]
    now = datetime.now(timezone.utc)
    participants = sorted([alice["user"]["id"], bob["user"]["id"]])
    for _ in range(2):
        await convos.insert_one(
            {
                "participants": participants,
                "type": "direct",
                "last_message": "",
                "last_message_at": now,
                "created_at": now,
            }
        )
    resp = await client.get("/api/v1/conversations", headers=auth_headers(alice))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["total"] == 1


async def test_concurrent_get_or_create_creates_one_conversation(fake_db):
    from app.repositories.conversation_repository import ConversationRepository
    from app.repositories.message_repository import MessageRepository
    from app.services.chat_service import ChatService

    chat = ChatService(ConversationRepository(fake_db), MessageRepository(fake_db))
    first, second = await asyncio.gather(
        chat.get_or_create_conversation(["u1", "u2"]),
        chat.get_or_create_conversation(["u1", "u2"]),
    )
    assert str(first["_id"]) == str(second["_id"])
    remaining = await fake_db["conversations"].find().to_list(length=None)
    assert len(remaining) == 1


async def test_merge_duplicate_conversations_preserves_messages(fake_db):
    from app.repositories.conversation_repository import ConversationRepository
    from app.repositories.message_repository import MessageRepository
    from app.services.chat_service import ChatService

    convos = fake_db["conversations"]
    msgs = fake_db["messages"]
    now = datetime.now(timezone.utc)
    ids = []
    for i in range(3):
        res = await convos.insert_one(
            {
                "participants": ["u1", "u2"],
                "type": "direct",
                "last_message": f"m{i}",
                "last_message_at": now,
                "created_at": now,
            }
        )
        ids.append(str(res.inserted_id))
    for i in range(3):
        await msgs.insert_one(
            {
                "conversation_id": ids[i],
                "sender_id": "u1",
                "recipient_id": "u2",
                "content": f"msg-{i}",
                "is_read": False,
                "created_at": now,
            }
        )
    await msgs.insert_one(
        {
            "conversation_id": "irelevant",
            "sender_id": "u1",
            "recipient_id": "u3",
            "content": "unrelated",
            "is_read": False,
            "created_at": now,
        }
    )

    chat = ChatService(ConversationRepository(fake_db), MessageRepository(fake_db))
    removed = await chat.merge_duplicate_conversations()
    assert removed == 2

    remaining = await convos.find().to_list(length=None)
    assert len(remaining) == 1
    keeper_id = str(remaining[0]["_id"])
    all_messages = await msgs.find().to_list(length=None)
    assert len(all_messages) == 4
    moved = [m for m in all_messages if m["content"].startswith("msg-")]
    assert len(moved) == 3
    assert all(m["conversation_id"] == keeper_id for m in moved)
