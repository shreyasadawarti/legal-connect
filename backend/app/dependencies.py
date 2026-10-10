from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models.user import UserRole, UserStatus
from app.repositories.user_repository import UserRepository, serialize_user

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseDep = Annotated[AsyncSession, Depends(get_session)]


async def require_db(db: AsyncSession = Depends(get_session)) -> AsyncSession:
    """Yield a request-scoped SQLAlchemy session.

    Kept under the original `require_db` name and signature shape so the
    thirteen routers that depend on it need only a type-annotation change.

    Uncommitted work is rolled back on the way out. Individual repositories
    only `flush()`, so the routers keep controlling transactions and an
    exception part-way through a request cannot leave half-written rows behind
    (MongoDB had no such failure mode).
    """
    if not settings.is_mysql_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database is not configured. Set MYSQL_HOST, MYSQL_USER and "
                "MYSQL_DATABASE in your .env file."
            ),
        )
    try:
        yield db
    except SQLAlchemyError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
    else:
        await db.commit()
    finally:
        await db.close()


def get_document_storage():
    """Return the active document storage backend (Cloudinary)."""
    from app.services.cloudinary_service import cloudinary_service

    return cloudinary_service


def get_payment_gateway():
    """Return the active payment gateway (Razorpay)."""
    from app.services.payment_gateway import payment_gateway

    return payment_gateway


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
    db: Annotated[AsyncSession, Depends(require_db)],
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # `db` already arrived via the require_db dependency, which has confirmed
    # MySQL is configured.
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
    token_ver = payload.get("ver", 0)
    if int(token_ver) != int(user.get("auth_version", 0)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
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
