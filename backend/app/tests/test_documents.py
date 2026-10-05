from typing import Any

import pytest
from httpx import AsyncClient

from app.dependencies import get_document_storage
from app.main import app
from app.services.cloudinary_service import DocumentStorageError
from app.tests.helpers import auth_headers, register_user


class FakeStorage:
    def __init__(self, *, configured: bool = True) -> None:
        self.configured = configured
        self.uploads: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self._n = 0

    @property
    def is_configured(self) -> bool:
        return self.configured

    async def upload_bytes(self, **kwargs) -> dict[str, Any]:
        if not self.configured:
            raise DocumentStorageError("not configured")
        self._n += 1
        info = {
            "public_id": f"doc_{self._n}",
            "url": "http://fake/doc",
            "secure_url": "https://fake/doc",
            "bytes": len(kwargs.get("data", b"")),
            "format": None,
            "resource_type": "raw",
        }
        self.uploads.append(info)
        return info

    async def delete(self, public_id: str, resource_type: str = "raw") -> None:
        self.deleted.append(public_id)

    def signed_url(self, public_id: str, resource_type: str = "raw") -> str:
        if not self.configured:
            raise DocumentStorageError("not configured")
        return f"https://fake/signed/{public_id}"


@pytest.fixture
async def doc_client(client, fake_db):
    storage = FakeStorage()
    app.dependency_overrides[get_document_storage] = lambda: storage
    yield client, storage
    # clear only the storage override; db override cleared by client fixture
    app.dependency_overrides.pop(get_document_storage, None)


async def _upload(client: AsyncClient, token: str, name: str = "note.txt", title: str = "My note") -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers({"access_token": token}),
        files={"file": (name, b"hello world", "text/plain")},
        data={"title": title},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_upload_requires_auth(doc_client):
    client, _ = doc_client
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.txt", b"x", "text/plain")},
    )
    assert resp.status_code == 401


async def test_upload_and_list(doc_client):
    client, storage = doc_client
    user = await register_user(client, email="u1@example.com")
    token = user["access_token"]

    doc = await _upload(client, token, title="First doc")
    assert doc["title"] == "First doc"
    assert doc["owner_id"] == user["user"]["id"]
    assert doc["original_name"] == "note.txt"
    assert doc["size_bytes"] == 11
    assert doc["shared_with"] == []
    assert doc["owner_name"] == user["user"]["name"]

    resp = await client.get("/api/v1/documents", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == doc["id"]


async def test_empty_upload_rejected(doc_client):
    client, _ = doc_client
    user = await register_user(client, email="u2@example.com")
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(user),
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


async def test_upload_with_verification_doc_type(doc_client):
    client, _ = doc_client
    user = await register_user(client, email="u2b@example.com")
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(user),
        files={"file": ("license.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"title": "License", "doc_type": "verification"},
    )
    assert resp.status_code == 201
    assert resp.json()["doc_type"] == "verification"


async def test_upload_rejects_invalid_doc_type(doc_client):
    client, _ = doc_client
    user = await register_user(client, email="u2c@example.com")
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(user),
        files={"file": ("license.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"title": "License", "doc_type": "bogus"},
    )
    assert resp.status_code == 422


async def test_verification_upload_rejects_invalid_mime(doc_client):
    client, _ = doc_client
    user = await register_user(client, email="u2d@example.com")
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(user),
        files={"file": ("license.txt", b"hello", "text/plain")},
        data={"title": "License", "doc_type": "verification"},
    )
    assert resp.status_code == 422


async def test_download_returns_signed_url(doc_client):
    client, storage = doc_client
    user = await register_user(client, email="u3@example.com")
    doc = await _upload(client, user["access_token"])
    resp = await client.get(
        f"/api/v1/documents/{doc['id']}/download",
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    assert "signed" in resp.json()["url"]


async def test_share_and_access(doc_client):
    client, _ = doc_client
    owner = await register_user(client, email="o@example.com")
    peer = await register_user(client, email="p@example.com")
    doc = await _upload(client, owner["access_token"])

    # Peer cannot access before share
    resp = await client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers(peer))
    assert resp.status_code == 403

    # Owner shares with peer
    resp = await client.post(
        f"/api/v1/documents/{doc['id']}/share",
        headers=auth_headers(owner),
        json={"user_ids": [peer["user"]["id"]]},
    )
    assert resp.status_code == 200
    assert peer["user"]["id"] in resp.json()["shared_with"]

    # Peer can now access
    resp = await client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers(peer))
    assert resp.status_code == 200

    # Peer receives a notification
    notifs = await client.get("/api/v1/notifications", headers=auth_headers(peer))
    assert notifs.json()["total"] == 1


async def test_non_owner_cannot_share(doc_client):
    client, _ = doc_client
    owner = await register_user(client, email="o2@example.com")
    peer = await register_user(client, email="p2@example.com")
    stranger = await register_user(client, email="s2@example.com")
    doc = await _upload(client, owner["access_token"])

    resp = await client.post(
        f"/api/v1/documents/{doc['id']}/share",
        headers=auth_headers(stranger),
        json={"user_ids": [peer["user"]["id"]]},
    )
    assert resp.status_code == 403


async def test_revoke_access(doc_client):
    client, _ = doc_client
    owner = await register_user(client, email="o3@example.com")
    peer = await register_user(client, email="p3@example.com")
    doc = await _upload(client, owner["access_token"])

    await client.post(
        f"/api/v1/documents/{doc['id']}/share",
        headers=auth_headers(owner),
        json={"user_ids": [peer["user"]["id"]]},
    )
    resp = await client.post(
        f"/api/v1/documents/{doc['id']}/revoke",
        headers=auth_headers(owner),
        json={"user_ids": [peer["user"]["id"]]},
    )
    assert resp.status_code == 200
    assert peer["user"]["id"] not in resp.json()["shared_with"]

    resp = await client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers(peer))
    assert resp.status_code == 403


async def test_delete_document(doc_client):
    client, storage = doc_client
    owner = await register_user(client, email="o4@example.com")
    doc = await _upload(client, owner["access_token"])

    resp = await client.delete(f"/api/v1/documents/{doc['id']}", headers=auth_headers(owner))
    assert resp.status_code == 204
    assert "doc_1" in storage.deleted

    resp = await client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers(owner))
    assert resp.status_code == 404


async def test_storage_unconfigured_returns_503(doc_client):
    client, storage = doc_client
    storage.configured = False
    user = await register_user(client, email="u5@example.com")
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(user),
        files={"file": ("a.txt", b"x", "text/plain")},
    )
    assert resp.status_code == 503


async def test_user_lookup_by_email(doc_client):
    client, _ = doc_client
    user = await register_user(client, email="lookup-target@example.com", name="Lookup")
    resp = await client.get(
        "/api/v1/users/lookup",
        params={"email": "LOOKUP-TARGET@example.com"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == user["user"]["id"]
    assert body["name"] == "Lookup"


async def test_user_lookup_not_found(doc_client):
    client, _ = doc_client
    user = await register_user(client, email="lookup-src@example.com")
    resp = await client.get(
        "/api/v1/users/lookup",
        params={"email": "missing@example.com"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 404
