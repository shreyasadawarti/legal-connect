from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.compat import utcnow
from app.dependencies import CurrentUser, require_db
from app.middleware.rate_limit import limiter
from app.models.platform import RevenueEventType
from app.models.user import UserRole, UserStatus
from app.repositories.revenue_repository import REGISTRATION_FEE, RevenueRepository
from app.repositories.user_repository import UserRepository, serialize_user
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import auth_service
from app.services.email_service import EmailDeliveryError, email_service

router = APIRouter(prefix="/auth", tags=["auth"])

UNVERIFIED_DETAIL = "Email not verified. Check your inbox for the verification link."
GENERIC_SEND_MESSAGE = (
    "If that email is registered, we will send a link if the mail service is available."
)


async def _issue_tokens(user: dict) -> AuthResponse:
    serialized = serialize_user(user)
    uid = serialized["id"]
    role = serialized["role"]
    ver = int(serialized.get("auth_version", 0))
    access = auth_service.create_access_token(uid, role, ver)
    refresh = auth_service.create_refresh_token(uid, role, ver)
    return AuthResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(serialized),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
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
    if payload.role in (UserRole.USER, UserRole.LAWYER):
        await RevenueRepository(db).record_idempotent(
            RevenueEventType.REGISTRATION,
            str(created["_id"]),
            REGISTRATION_FEE,
        )
    user = await repo.find_by_id(str(created["_id"])) or {}
    verify_token = auth_service.generate_verify_email_token(payload.email)
    try:
        await email_service.send_verification(payload.email, verify_token)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send the verification email. Please try again later.",
        ) from exc
    return RegisterResponse(
        message="Account created. Check your email to verify your address before logging in.",
        user=UserResponse.model_validate(serialize_user(user)),
    )


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
    if not user.get("is_email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=UNVERIFIED_DETAIL,
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
    if not user.get("is_email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token rejected",
        )
    token_ver = int(token_payload.get("ver", 0))
    if token_ver != int(user.get("auth_version", 0)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    return await _issue_tokens(user)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(require_db)):
    repo = UserRepository(db)
    user = await repo.find_by_email(payload.email)
    if user:
        token = auth_service.generate_reset_token()
        token_hash = auth_service.hash_reset_token(token)
        expires_at = utcnow() + timedelta(minutes=auth_service.RESET_TOKEN_TTL_MINUTES)
        await repo.set_reset_token(str(user["_id"]), token_hash, expires_at)
        try:
            await email_service.send_password_reset(payload.email, token)
        except EmailDeliveryError:
            pass
    # Always the same message for registered and unregistered emails; the page
    # cannot be used to discover accounts. Forgot-password never claims an email
    # was sent, so a delivery failure is never falsely reported as a success.
    return {"message": GENERIC_SEND_MESSAGE}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def reset_password(request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(require_db)):
    repo = UserRepository(db)
    token_hash = auth_service.hash_reset_token(payload.token)
    user = await repo.find_by_reset_token(token_hash)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )
    expires_at = user.get("reset_token_expires_at")
    if expires_at is None or utcnow() > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )
    new_hash = auth_service.hash_password(payload.password)
    user_id = str(user["_id"])
    await repo.update(user_id, {"password_hash": new_hash})
    await repo.clear_reset_token(user_id)
    await repo.increment_auth_version(user_id)
    return {"message": "Password has been reset successfully."}


@router.post("/verify-email", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(request: Request, payload: VerifyEmailRequest, db: AsyncSession = Depends(require_db)):
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


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(require_db),
):
    repo = UserRepository(db)
    user = await repo.find_by_email(payload.email)
    if user and not user.get("is_email_verified"):
        verify_token = auth_service.generate_verify_email_token(payload.email)
        try:
            await email_service.send_verification(payload.email, verify_token)
        except EmailDeliveryError:
            pass
    # Uniform response: the endpoint cannot reveal whether an address is
    # registered or already verified.
    return {
        "message": "If that email is registered and unverified, we will send a verification link.",
    }


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
    await repo.increment_auth_version(user["id"])
    return {"message": "Password changed successfully."}