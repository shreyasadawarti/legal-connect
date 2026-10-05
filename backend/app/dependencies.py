from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_database
from app.models.user import UserRole, UserStatus
from app.repositories.user_repository import UserRepository, serialize_user

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseDep = Annotated[AsyncIOMotorDatabase | None, Depends(get_database)]


def require_db(db: AsyncIOMotorDatabase | None = Depends(get_database)) -> AsyncIOMotorDatabase:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Set MONGODB_URI in your .env file.",
        )
    return db


def get_document_storage():
    """Return the active document storage backend (Cloudinary)."""
    from app.services.cloudinary_service import cloudinary_service

    return cloudinary_service


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncIOMotorDatabase | None, Depends(get_database)],
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db = require_db(db)
    payload = decode_token(credentials.credentials, expected_type="access")
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
    repo = UserRepository(db)
    user = await repo.find_by_id(subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    if user.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )
    return serialize_user(user)


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def dependency(user: CurrentUser) -> dict:
        if user["role"] not in {r.value for r in roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency
