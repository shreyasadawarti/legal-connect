from httpx import AsyncClient

from app.models.user import UserRole
from app.tests.helpers import (
    activate_lawyer,
    add_verification_document,
    auth_headers,
    create_lawyer_profile,
    register,
    register_lawyer,
    register_user,
)


async def _setup_activated_lawyer(client: AsyncClient, fake_db):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(fake_db, lawyer["user"]["id"])
    return lawyer


async def test_lawyer_creates_and_reads_profile(client: AsyncClient):
    lawyer = await register_lawyer(client)
    profile = await create_lawyer_profile(client, lawyer)
    assert profile["user_id"] == lawyer["user"]["id"]
    assert profile["name"] == "Test Lawyer"
    assert profile["categories"] == ["family"]

    me = await client.get("/api/v1/lawyers/me/profile", headers=auth_headers(lawyer))
    assert me.status_code == 200
    assert me.json()["user_id"] == lawyer["user"]["id"]


async def test_lawyer_updates_profile(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    resp = await client.patch(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={"hourly_rate": 150.0, "bio": "Updated bio"},
    )
    assert resp.status_code == 200
    assert resp.json()["hourly_rate"] == 150.0
    assert resp.json()["bio"] == "Updated bio"


async def test_non_lawyer_cannot_create_profile(client: AsyncClient):
    user = await register_user(client)
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(user),
        json={"bio": "nope"},
    )
    assert resp.status_code == 403


async def test_public_profile_by_user_id(client: AsyncClient, fake_db):
    lawyer = await _setup_activated_lawyer(client, fake_db)
    resp = await client.get(f"/api/v1/lawyers/{lawyer['user']['id']}")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == lawyer["user"]["id"]
    assert resp.json()["name"] == "Test Lawyer"


async def test_public_profile_missing_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/lawyers/000000000000000000000000")
    assert resp.status_code == 404


async def test_search_filters_and_returns_verified(client: AsyncClient, fake_db):
    await _setup_activated_lawyer(client, fake_db)
    resp = await client.get("/api/v1/lawyers", params={"category": "family"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["categories"] == ["family"]

    resp = await client.get("/api/v1/lawyers", params={"verified_only": "true"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_search_excludes_unverified_by_default_filter(client: AsyncClient, fake_db):
    # A lawyer who has a profile but is PENDING_VERIFICATION should be returned
    # by the directory list (it only excludes REJECTED/SUSPENDED).
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    resp = await client.get("/api/v1/lawyers")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["is_verified"] is False


async def test_unknown_category_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/lawyers", params={"category": "bogus"})
    assert resp.status_code == 422


async def test_legal_categories_list(client: AsyncClient):
    resp = await client.get("/api/v1/legal-categories")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "family" in names and "criminal" in names


async def test_link_verification_document(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    storage, doc_id = await add_verification_document(client, lawyer)
    me = await client.get("/api/v1/lawyers/me/profile", headers=auth_headers(lawyer))
    assert me.status_code == 200
    assert me.json()["verification_document_id"] == doc_id
    assert storage.uploads


async def test_link_verification_document_requires_profile(client: AsyncClient):
    lawyer = await register_lawyer(client)
    resp = await client.put(
        "/api/v1/lawyers/me/verification-document",
        headers=auth_headers(lawyer),
        json={"document_id": "000000000000000000000000"},
    )
    assert resp.status_code == 404


async def test_link_requires_owned_document(client: AsyncClient):
    owner = await register_lawyer(client)
    await create_lawyer_profile(client, owner)
    _, doc_id = await add_verification_document(client, owner)

    other = await register_lawyer(client, email="secondlawyer@example.com")
    await create_lawyer_profile(client, other)
    resp = await client.put(
        "/api/v1/lawyers/me/verification-document",
        headers=auth_headers(other),
        json={"document_id": doc_id},
    )
    assert resp.status_code == 403


async def test_link_rejects_non_verification_document(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    upload = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(lawyer),
        files={"file": ("note.txt", b"hello world", "text/plain")},
        data={"title": "General note"},
    )
    assert upload.status_code == 201
    resp = await client.put(
        "/api/v1/lawyers/me/verification-document",
        headers=auth_headers(lawyer),
        json={"document_id": upload.json()["id"]},
    )
    assert resp.status_code == 422


async def test_link_missing_document_returns_404(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    resp = await client.put(
        "/api/v1/lawyers/me/verification-document",
        headers=auth_headers(lawyer),
        json={"document_id": "000000000000000000000000"},
    )
    assert resp.status_code == 404


async def test_public_directory_hides_verification_document_id(client: AsyncClient):
    lawyer = await register_lawyer(client)
    await create_lawyer_profile(client, lawyer)
    _, doc_id = await add_verification_document(client, lawyer)

    directory = await client.get("/api/v1/lawyers")
    assert directory.status_code == 200
    assert "verification_document_id" not in directory.json()["items"][0]

    public = await client.get(f"/api/v1/lawyers/{lawyer['user']['id']}")
    assert public.status_code == 200
    assert public.json().get("verification_document_id") is None
