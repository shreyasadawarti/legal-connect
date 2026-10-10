import pytest

from app.tests.helpers import auth_headers, register_user


@pytest.fixture
async def pair(client):
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    return client, alice, bob


async def test_block_prevents_starting_a_conversation(pair):
    client, alice, bob = pair
    resp = await client.post(
        f"/api/v1/users/{bob['user']['id']}/block", headers=auth_headers(alice)
    )
    assert resp.status_code == 204

    created = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    assert created.status_code == 403


async def test_block_prevents_sending_in_existing_conversation(pair):
    client, alice, bob = pair
    conv = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    conv_id = conv.json()["id"]

    await client.post(
        f"/api/v1/users/{bob['user']['id']}/block", headers=auth_headers(alice)
    )
    sent = await client.post(
        f"/api/v1/messages/{conv_id}",
        headers=auth_headers(alice),
        json={"content": "hello?"},
    )
    assert sent.status_code == 403


async def test_block_is_bidirectional(pair):
    client, alice, bob = pair
    await client.post(
        f"/api/v1/users/{bob['user']['id']}/block", headers=auth_headers(alice)
    )
    # Bob never blocked Alice, but Alice blocking Bob stops Bob from messaging too.
    created = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(bob),
        json={"other_user_id": alice["user"]["id"]},
    )
    assert created.status_code == 403


async def test_unblock_restores_messaging(pair):
    client, alice, bob = pair
    await client.post(
        f"/api/v1/users/{bob['user']['id']}/block", headers=auth_headers(alice)
    )
    unblocked = await client.delete(
        f"/api/v1/users/{bob['user']['id']}/block", headers=auth_headers(alice)
    )
    assert unblocked.status_code == 204

    created = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(alice),
        json={"other_user_id": bob["user"]["id"]},
    )
    assert created.status_code == 201


async def test_cannot_block_self(pair):
    client, alice, _ = pair
    resp = await client.post(
        f"/api/v1/users/{alice['user']['id']}/block", headers=auth_headers(alice)
    )
    assert resp.status_code == 400


async def test_block_unknown_user_returns_404(pair):
    client, alice, _ = pair
    resp = await client.post(
        "/api/v1/users/000000000000000000000000/block",
        headers=auth_headers(alice),
    )
    assert resp.status_code == 404


async def test_list_blocks(pair):
    client, alice, bob = pair
    await client.post(
        f"/api/v1/users/{bob['user']['id']}/block", headers=auth_headers(alice)
    )
    resp = await client.get("/api/v1/users/me/blocks", headers=auth_headers(alice))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == bob["user"]["id"]
    assert body["items"][0]["name"] == "Bob"
