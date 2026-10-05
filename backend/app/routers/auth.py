from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, require_db
from app.middleware.rate_limit import limiter
from app.models.user import UserRole, UserStatus
from app.repositories.user_repository import UserRepository, serialize_user
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import auth_service
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(user: dict) -> AuthResponse:
    serialized = serialize_user(user)
    uid = serialized["id"]
    role = serialized["role"]
    access = auth_service.create_access_token(uid, role)
    refresh = auth_service.create_refresh_token(uid, role)
    return AuthResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(serialized),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(require_db)):
    repo = UserRepository(db)
    existing = await repo.find_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    if payload.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be registered. Contact an administrator.",
        )
    password_hash = auth_service.hash_password(payload.password)
    created = await repo.create(
        name=payload.name,
        email=payload.email,
        password_hash=password_hash,
        phone=payload.phone,
        role=payload.role,
    )
    user = await repo.find_by_id(str(created["_id"])) or {}
    verify_token = auth_service.generate_verify_email_token(payload.email)
    await email_service.send_verification(payload.email, verify_token)
    return await _issue_tokens(user)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(require_db)):
    repo = UserRepository(db)
    user = await repo.find_by_email(payload.email)
    if not user or not auth_service.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )
    await repo.update_last_login(str(user["_id"]))
    user = await repo.find_by_id(str(user["_id"])) or {}
    return await _issue_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: CurrentUser):
    # Client-side session clearing; JWT access tokens are short-lived by design.
    return None


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit("20/minute")
async def refresh(request: Request, payload: RefreshRequest, db: AsyncSession = Depends(require_db)):
    token_payload = auth_service.decode_token(payload.refresh_token)
    if token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    subject = token_payload.get("sub")
    repo = UserRepository(db)
    user = await repo.find_by_id(subject)
    if user is None or user.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token rejected",
        )
    return await _issue_tokens(user)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(require_db)):
    repo = UserRepository(db)
    user = await repo.find_by_email(payload.email)
    if user:
        token = auth_service.generate_reset_token(payload.email)
        await email_service.send_password_reset(payload.email, token)
    # Always return 200 even if the email is unknown (avoid user enumeration).
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(require_db)):
    token_payload = auth_service.decode_token(payload.token)
    if token_payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reset token",
        )
    email = token_payload.get("sub")
    repo = UserRepository(db)
    user = await repo.find_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    new_hash = auth_service.hash_password(payload.password)
    await repo.update(str(user["_id"]), {"password_hash": new_hash})
    return {"message": "Password has been reset."}


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(require_db)):
    token_payload = auth_service.decode_token(payload.token)
    if token_payload.get("type") != "verify_email":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification token",
        )
    email = token_payload.get("sub")
    repo = UserRepository(db)
    user = await repo.find_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )
    await repo.mark_email_verified(str(user["_id"]))
    return {"message": "Email verified successfully."}


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/change-password", status_code=status.HTTP_200_OK)
async def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: AsyncSession = Depends(require_db)):
    repo = UserRepository(db)
    current = await repo.find_by_id(user["id"])
    if not current or not auth_service.verify_password(
        payload.current_password, current["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    new_hash = auth_service.hash_password(payload.new_password)
    await repo.update(user["id"], {"password_hash": new_hash})
    return {"message": "Password changed successfully."}
