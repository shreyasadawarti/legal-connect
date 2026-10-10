import pytest

from app.tests.helpers import auth_headers, register_user


@pytest.fixture
async def chat_users(client):
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    return client, alice, bob


async def _create(client, sender, other_id, initial=None):
    payload = {"other_user_id": other_id}
    if initial:
        payload["initial_message"] = initial
    resp = await client.post(
        "/api/v1/conversations", headers=auth_headers(sender), json=payload
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_delete_conversation_hides_it_only_for_the_deleter(chat_users):
    client, alice, bob = chat_users
    conv_id = await _create(client, alice, bob["user"]["id"], initial="hello")

    deleted = await client.delete(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers(alice)
    )
    assert deleted.status_code == 204

    alice_list = await client.get("/api/v1/conversations", headers=auth_headers(alice))
    assert alice_list.json()["items"] == []

    bob_list = await client.get("/api/v1/conversations", headers=auth_headers(bob))
    assert len(bob_list.json()["items"]) == 1


async def test_new_message_revives_a_deleted_conversation(chat_users):
    client, alice, bob = chat_users
    conv_id = await _create(client, alice, bob["user"]["id"])
    await client.delete(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers(alice)
    )

    sent = await client.post(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(bob),
        json={"content": "are you there?"},
    )
    assert sent.status_code == 200

    alice_list = await client.get("/api/v1/conversations", headers=auth_headers(alice))
    assert len(alice_list.json()["items"]) == 1


async def test_reopening_a_deleted_conversation_restores_it_for_caller(chat_users):
    client, alice, bob = chat_users
    conv_id = await _create(client, alice, bob["user"]["id"], initial="hi")
    await client.delete(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers(alice)
    )
    await client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers(bob))
    assert (
        await client.get("/api/v1/conversations", headers=auth_headers(alice))
    ).json()["items"] == []

    reopened = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    assert reopened.status_code == 201
    assert reopened.json()["id"] == conv_id

    alice_list = await client.get("/api/v1/conversations", headers=auth_headers(alice))
    assert len(alice_list.json()["items"]) == 1
    bob_list = await client.get("/api/v1/conversations", headers=auth_headers(bob))
    assert bob_list.json()["items"] == []


async def test_clear_history_hides_old_messages_for_caller_only(chat_users):
    client, alice, bob = chat_users
    conv_id = await _create(client, alice, bob["user"]["id"], initial="first")

    cleared = await client.post(
        f"/api/v1/conversations/{conv_id}/clear", headers=auth_headers(bob)
    )
    assert cleared.status_code == 204

    bob_view = await client.get(
        f"/api/v1/messages/{conv_id}", headers=auth_headers(bob)
    )
    assert bob_view.json()["items"] == []

    alice_view = await client.get(
        f"/api/v1/messages/{conv_id}", headers=auth_headers(alice)
    )
    assert [m["content"] for m in alice_view.json()["items"]] == ["first"]

    await client.post(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(alice),
        json={"content": "second"},
    )
    bob_view2 = await client.get(
        f"/api/v1/messages/{conv_id}", headers=auth_headers(bob)
    )
    assert [m["content"] for m in bob_view2.json()["items"]] == ["second"]


async def test_non_participant_cannot_delete_or_clear(chat_users):
    client, alice, bob = chat_users
    conv_id = await _create(client, alice, bob["user"]["id"])
    eve = await register_user(client, name="Eve", email="eve@example.com")

    deleted = await client.delete(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers(eve)
    )
    assert deleted.status_code == 403

    cleared = await client.post(
        f"/api/v1/conversations/{conv_id}/clear", headers=auth_headers(eve)
    )
    assert cleared.status_code == 403


async def test_delete_unknown_conversation_returns_404(chat_users):
    client, alice, _ = chat_users
    resp = await client.delete(
        "/api/v1/conversations/000000000000000000000000",
        headers=auth_headers(alice),
    )
    assert resp.status_code == 404
