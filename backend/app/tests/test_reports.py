from httpx import AsyncClient

from app.tests.helpers import auth_headers, register_lawyer, register_user


async def _conversation(client: AsyncClient, a, b) -> str:
    resp = await client.post(
        "/api/v1/conversations",
        headers=auth_headers(a),
        json={"other_user_id": b["user"]["id"]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_user_reports_counterpart_from_conversation(client: AsyncClient):
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    conv_id = await _conversation(client, alice, bob)

    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(alice),
        json={
            "subject": "Harassment",
            "description": "Abusive messages.",
            "conversation_id": conv_id,
            "category": "harassment",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["target_user_id"] == bob["user"]["id"]
    assert body["conversation_id"] == conv_id
    assert body["category"] == "harassment"


async def test_lawyer_reports_counterpart_from_conversation(client: AsyncClient):
    lawyer = await register_lawyer(client)
    user = await register_user(client)
    conv_id = await _conversation(client, lawyer, user)

    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(lawyer),
        json={
            "subject": "Abusive client",
            "description": "The client threatened me.",
            "conversation_id": conv_id,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["target_user_id"] == user["user"]["id"]


async def test_report_rejects_non_participant(client: AsyncClient):
    alice = await register_user(client, name="Alice", email="alice@example.com")
    bob = await register_user(client, name="Bob", email="bob@example.com")
    eve = await register_user(client, name="Eve", email="eve@example.com")
    conv_id = await _conversation(client, alice, bob)

    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(eve),
        json={
            "subject": "Not mine",
            "description": "I am not in this conversation.",
            "conversation_id": conv_id,
        },
    )
    assert resp.status_code == 403


async def test_report_unknown_conversation_returns_404(client: AsyncClient):
    alice = await register_user(client)
    resp = await client.post(
        "/api/v1/complaints",
        headers=auth_headers(alice),
        json={
            "subject": "Missing",
            "description": "No such conversation.",
            "conversation_id": "000000000000000000000000",
        },
    )
    assert resp.status_code == 404
