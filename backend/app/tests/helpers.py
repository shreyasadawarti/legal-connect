from typing import Any

from fastapi.testclient import TestClient  # noqa: F401  (re-export parity)
from httpx import AsyncClient

from app.main import app
from app.models.user import LawyerStatus, UserRole
from app.repositories.lawyer_repository import LawyerRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import hash_password


async def _get_app_db():
    """Resolve the database session the app currently uses (test override or real MySQL)."""
    test_session = getattr(app.state, "test_db_session", None)
    if test_session is not None:
        return test_session
    from app.db.session import get_session_factory

    factory = get_session_factory()
    return factory()


async def register(client: AsyncClient, *, name: str, email: str, role: str) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "StrongPass123",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()["user"]
    db = await _get_app_db()
    if db is None:
        raise RuntimeError("Database is not configured; cannot verify email")
    await UserRepository(db).mark_email_verified(user["id"])
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def register_user(client: AsyncClient, *, name: str = "Test User", email: str = "user@example.com") -> dict[str, Any]:
    return await register(client, name=name, email=email, role=UserRole.USER.value)


async def register_lawyer(
    client: AsyncClient,
    *,
    name: str = "Test Lawyer",
    email: str = "lawyer@example.com",
) -> dict[str, Any]:
    return await register(client, name=name, email=email, role=UserRole.LAWYER.value)


async def register_admin(
    client: AsyncClient,
    *,
    name: str = "Test Admin",
    email: str = "admin@example.com",
) -> dict[str, Any]:
    # Admins are created only via the secure mechanism (mirrors scripts/create_admin.py),
    # never through the public registration endpoint (which rejects role=admin).
    db = await _get_app_db()
    if db is None:
        raise RuntimeError("Database is not configured; cannot create admin")
    repo = UserRepository(db)
    created = await repo.create(
        name=name,
        email=email,
        password_hash=hash_password("StrongPass123"),
        role=UserRole.ADMIN,
    )
    await repo.mark_email_verified(str(created["_id"]))
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(data: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {data['access_token']}"}


async def create_lawyer_profile(client: AsyncClient, lawyer: dict[str, Any]) -> dict[str, Any]:
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={
            "bio": "Experienced family lawyer",
            "years_of_experience": 5,
            "categories": ["family"],
            "specializations": ["Divorce", "Custody"],
            "languages": ["English"],
            "hourly_rate": 100.0,
            "city": "Mumbai",
            "availability": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def activate_lawyer(db: Any, lawyer_id: str) -> None:
    await LawyerRepository(db).set_verification_status(
        lawyer_id, LawyerStatus.ACTIVE
    )
    await db.commit()


class _FakeDocumentStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self._n = 0

    @property
    def is_configured(self) -> bool:
        return True

    async def upload_bytes(self, **kwargs) -> dict[str, Any]:
        self._n += 1
        info = {
            "public_id": f"verif_{self._n}",
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
        return f"https://fake/signed/{public_id}"


async def add_verification_document(
    client: AsyncClient, lawyer: dict[str, Any], name: str = "license.pdf"
) -> tuple[Any, str]:
    """Upload a verification document as the lawyer and attach it to their profile.

    Installs a fake document storage dependency for the current test; the shared
    client fixture clears all dependency overrides during teardown.
    """
    from app.dependencies import get_document_storage
    from app.main import app

    storage = _FakeDocumentStorage()
    app.dependency_overrides[get_document_storage] = lambda: storage
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers(lawyer),
        files={"file": (name, b"%PDF-1.4 fake bar council license", "application/pdf")},
        data={"title": "Bar council license", "doc_type": "verification"},
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    link = await client.put(
        "/api/v1/lawyers/me/verification-document",
        headers=auth_headers(lawyer),
        json={"document_id": doc_id},
    )
    assert link.status_code == 200, link.text
    return storage, doc_id
