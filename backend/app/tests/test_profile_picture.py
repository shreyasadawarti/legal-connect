from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient

from app.dependencies import get_document_storage
from app.main import app
from app.services.cloudinary_service import DocumentStorageError
from app.tests.helpers import (
    activate_lawyer,
    auth_headers,
    create_lawyer_profile,
    register_lawyer,
    register_user,
)


class PictureStorage:
    def __init__(self, *, configured: bool = True) -> None:
        self.configured = configured
        self.uploads: list[dict[str, Any]] = []
        self.deleted: list[tuple[str, str]] = []
        self._n = 0

    @property
    def is_configured(self) -> bool:
        return self.configured

    async def upload_bytes(self, **kwargs) -> dict[str, Any]:
        if not self.configured:
            raise DocumentStorageError("Cloudinary is not configured")
        self._n += 1
        info = {
            "public_id": f"picture_{self._n}",
            "url": f"http://fake/picture_{self._n}",
            "secure_url": f"https://fake/picture_{self._n}",
            "bytes": len(kwargs.get("data", b"")),
            "format": "png",
            "resource_type": kwargs.get("resource_type", "raw"),
        }
        self.uploads.append({**info, "requested_resource_type": kwargs.get("resource_type")})
        return info

    async def delete(self, public_id: str, resource_type: str = "raw") -> None:
        self.deleted.append((public_id, resource_type))


PNG_BYTES = b"\x89PNG\r\n\x1a\n fake portrait payload"


@pytest.fixture
async def picture_client(client, db):
    storage = PictureStorage()
    app.dependency_overrides[get_document_storage] = lambda: storage
    yield client, storage
    app.dependency_overrides.pop(get_document_storage, None)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _upload(
    client: AsyncClient,
    token: str,
    *,
    data: bytes = PNG_BYTES,
    filename: str = "me.png",
    mime: str = "image/png",
):
    return await client.post(
        "/api/v1/users/me/profile-picture",
        headers=_headers(token),
        files={"file": (filename, data, mime)},
    )


async def test_upload_picture_requires_auth(picture_client):
    client, _ = picture_client
    resp = await client.post(
        "/api/v1/users/me/profile-picture",
        files={"file": ("me.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 401


@pytest.mark.parametrize("mime", ["image/png", "image/jpeg", "image/webp"])
async def test_upload_accepts_supported_formats(picture_client, mime):
    client, storage = picture_client
    user = await register_user(client, email=f"{mime.replace('/', '.')}@example.com")

    resp = await _upload(client, user["access_token"], mime=mime)

    assert resp.status_code == 200, resp.text
    assert resp.json()["profile_picture_url"] == "https://fake/picture_1"
    assert storage.uploads[0]["requested_resource_type"] == "image"


async def test_upload_rejects_executable(picture_client):
    client, storage = picture_client
    user = await register_user(client, email="exe@example.com")

    resp = await _upload(
        client,
        user["access_token"],
        data=b"MZ not a picture",
        filename="payload.png",
        mime="application/x-msdownload",
    )

    assert resp.status_code == 422
    assert storage.uploads == []


async def test_upload_rejects_oversize(picture_client):
    client, storage = picture_client
    user = await register_user(client, email="big@example.com")

    resp = await _upload(client, user["access_token"], data=b"x" * (5 * 1024 * 1024 + 1))

    assert resp.status_code == 413
    assert storage.uploads == []


async def test_upload_rejects_empty_file(picture_client):
    client, _ = picture_client
    user = await register_user(client, email="empty@example.com")

    resp = await _upload(client, user["access_token"], data=b"")

    assert resp.status_code == 400


async def test_upload_reports_unconfigured_storage(picture_client):
    client, storage = picture_client
    storage.configured = False
    user = await register_user(client, email="nostorage@example.com")

    resp = await _upload(client, user["access_token"])

    assert resp.status_code == 503


async def test_picture_persists_and_appears_on_profile(picture_client):
    client, _ = picture_client
    user = await register_user(client, email="persist@example.com")

    await _upload(client, user["access_token"])
    resp = await client.get("/api/v1/users/me", headers=_headers(user["access_token"]))

    assert resp.status_code == 200
    assert resp.json()["profile_picture_url"] == "https://fake/picture_1"


async def test_replace_deletes_previous_asset(picture_client):
    client, storage = picture_client
    user = await register_user(client, email="replace@example.com")

    await _upload(client, user["access_token"])
    resp = await _upload(client, user["access_token"])

    assert resp.status_code == 200
    assert resp.json()["profile_picture_url"] == "https://fake/picture_2"
    assert ("picture_1", "image") in storage.deleted


async def test_remove_clears_picture_and_deletes_asset(picture_client):
    client, storage = picture_client
    user = await register_user(client, email="remove@example.com")
    await _upload(client, user["access_token"])

    resp = await client.delete(
        "/api/v1/users/me/profile-picture", headers=_headers(user["access_token"])
    )

    assert resp.status_code == 200
    assert resp.json()["profile_picture_url"] is None
    assert ("picture_1", "image") in storage.deleted


async def test_lawyer_picture_is_public_on_lawyer_profile(picture_client):
    client, _ = picture_client
    lawyer = await register_lawyer(client, email="pictured.lawyer@example.com")
    await create_lawyer_profile(client, lawyer)
    await _upload(client, lawyer["access_token"])

    resp = await client.get(f"/api/v1/lawyers/{lawyer['user']['id']}")

    assert resp.status_code == 200
    assert resp.json()["profile_picture_url"] == "https://fake/picture_1"


async def _book(client: AsyncClient, citizen: dict, lawyer_id: str) -> dict[str, Any]:
    start = (datetime.now(timezone.utc) + timedelta(days=3)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    resp = await client.post(
        "/api/v1/appointments",
        headers=_headers(citizen["access_token"]),
        json={
            "lawyer_id": lawyer_id,
            "category": "family",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "description": "Need advice",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _ready_lawyer(client: AsyncClient, db, email: str) -> dict[str, Any]:
    lawyer = await register_lawyer(client, email=email)
    await create_lawyer_profile(client, lawyer)
    await activate_lawyer(db, lawyer["user"]["id"])
    return lawyer


async def test_appointment_exposes_citizen_details_to_lawyer(picture_client, db):
    client, _ = picture_client
    lawyer = await _ready_lawyer(client, db, "client.details@example.com")
    citizen = await register_user(client, name="Priya Citizen", email="priya.citizen@example.com")
    resp = await client.patch(
        "/api/v1/users/me",
        headers=_headers(citizen["access_token"]),
        json={"phone": "+91 99999 00001", "city": "Pune"},
    )
    assert resp.status_code == 200, resp.text
    await _upload(client, citizen["access_token"])

    appt = await _book(client, citizen, lawyer["user"]["id"])
    listing = await client.get("/api/v1/appointments", headers=_headers(lawyer["access_token"]))

    assert listing.status_code == 200
    item = listing.json()["items"][0]
    assert item["client_name"] == "Priya Citizen"
    assert item["client_profile_picture_url"] == "https://fake/picture_1"
    assert item["client_phone"] == "+91 99999 00001"
    assert item["client_city"] == "Pune"
    assert item["id"] == appt["id"]


async def test_citizen_response_omits_own_contact_details(picture_client, db):
    client, _ = picture_client
    lawyer = await _ready_lawyer(client, db, "omit.lawyer@example.com")
    citizen = await register_user(client, email="quiet.citizen@example.com")
    await client.patch(
        "/api/v1/users/me",
        headers=_headers(citizen["access_token"]),
        json={"phone": "+91 99999 00002", "city": "Goa"},
    )
    await _upload(client, citizen["access_token"])
    await _book(client, citizen, lawyer["user"]["id"])

    resp = await client.get("/api/v1/appointments", headers=_headers(citizen["access_token"]))

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["client_name"] == "Test User"
    # Withheld entirely rather than null: a citizen reading their own request
    # gets no citizen-detail keys at all.
    assert "client_profile_picture_url" not in item
    assert "client_phone" not in item
    assert "client_city" not in item


async def test_outsider_cannot_read_appointment(picture_client, db):
    client, _ = picture_client
    lawyer = await _ready_lawyer(client, db, "outsider.lawyer@example.com")
    citizen = await register_user(client, email="victim@example.com")
    outsider = await register_user(client, email="nosy@example.com")
    appt = await _book(client, citizen, lawyer["user"]["id"])

    resp = await client.get(
        f"/api/v1/appointments/{appt['id']}", headers=_headers(outsider["access_token"])
    )

    assert resp.status_code == 403


async def test_public_lawyer_listing_never_exposes_citizen_pictures(picture_client, db):
    client, _ = picture_client
    await _ready_lawyer(client, db, "listing.lawyer@example.com")
    citizen = await register_user(client, email="listed.citizen@example.com")
    await _upload(client, citizen["access_token"])

    resp = await client.get("/api/v1/lawyers")

    assert resp.status_code == 200
    body = resp.text
    assert "listed.citizen@example.com" not in body
    assert "https://fake/picture_1" not in body