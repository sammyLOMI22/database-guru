"""Authentication endpoints — register, login, me"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth.dependencies import get_current_active_user, get_auth_service
from src.auth.models import PasswordResetToken, User
from src.auth.schemas import (
    PasswordChangeRequest,
    PasswordResetRedeemRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.auth.audit import log_action
from src.auth.service import (
    AuthService,
    bump_password_version,
    check_password_history,
    record_password_history,
)
from src.api.dependencies.common import get_settings
from src.config.settings import Settings
from src.middleware.rate_limit import (
    auth_rate_limiter,
    enforce_change_password_limit,
    get_client_ip,
    login_attempt_tracker,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    _rate_limit: None = Depends(auth_rate_limiter),
):
    """Register a new user and return a JWT token."""
    try:
        user = await auth_service.register(db, data.email, data.username, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    await log_action(
        db, action="register", resource_type="user", resource_id=str(user.id),
        user_id=user.id, username=user.username,
        ip_address=get_client_ip(request),
    )
    await db.commit()

    token, expires_in = auth_service.create_access_token(
        user.id, user.username, password_version=user.password_version,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
    _rate_limit: None = Depends(auth_rate_limiter),
):
    """Authenticate and return a JWT token."""
    # Phase B: per-username lockout. Check before bcrypt so a locked account
    # short-circuits without burning a hash. Threshold/window are configurable
    # and the tracker keys by lowercase username so casing can't dodge it.
    if settings.AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED:
        locked, retry_after = await login_attempt_tracker.is_locked(
            data.username,
            threshold=settings.AUTH_LOGIN_LOCKOUT_THRESHOLD,
            window_s=settings.AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS,
        )
        if locked:
            await log_action(
                db, action="account_locked", resource_type="user",
                details={"username": data.username, "retry_after_seconds": retry_after},
                ip_address=get_client_ip(request),
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Account temporarily locked after too many failed attempts. "
                    f"Try again in {retry_after} seconds."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    user = await auth_service.authenticate(db, data.username, data.password)
    if user is None:
        if settings.AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED:
            await login_attempt_tracker.record_failure(
                data.username,
                window_s=settings.AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS,
            )
        await log_action(
            db, action="login_failed", resource_type="user",
            details={"username": data.username},
            ip_address=get_client_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Successful auth — clear any failure counter for this username.
    if settings.AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED:
        had_failures = await login_attempt_tracker.record_success(data.username)
        if had_failures:
            await log_action(
                db, action="account_unlocked", resource_type="user",
                resource_id=str(user.id), user_id=user.id, username=user.username,
                ip_address=get_client_ip(request),
            )

    await log_action(
        db, action="login", resource_type="user", resource_id=str(user.id),
        user_id=user.id, username=user.username,
        ip_address=get_client_ip(request),
    )
    await db.commit()

    token, expires_in = auth_service.create_access_token(
        user.id, user.username, password_version=user.password_version,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    settings: Settings = Depends(get_settings),
):
    """Log out the current user.

    Records the event in the audit log. The client should discard its token.
    When ``AUTH_INVALIDATE_TOKENS_ON_LOGOUT`` is on, also bumps the user's
    ``password_version`` so every device they're signed in on is evicted —
    this is the explicit kill-switch for "log me out everywhere."
    """
    if settings.AUTH_INVALIDATE_TOKENS_ON_LOGOUT:
        bump_password_version(user)
    await log_action(
        db, action="logout", resource_type="user", resource_id=str(user.id),
        user_id=user.id, username=user.username,
        details={"invalidated_all_sessions": settings.AUTH_INVALIDATE_TOKENS_ON_LOGOUT},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_active_user)):
    """Return the current authenticated user."""
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    request: Request,
    data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    user: User = Depends(get_current_active_user),
    settings: Settings = Depends(get_settings),
):
    """Change the current user's password.

    Required after an admin password reset (User.must_change_password=True),
    but available to any authenticated user. Verifies the current password,
    enforces complexity on the new one, clears the must-change flag, bumps
    ``password_version`` to evict other sessions, and returns a fresh token
    so the caller stays signed in on this device.
    """
    # Phase B: rate-limit per-user. Runs before the bcrypt compare so a
    # caller that's already over-limit can't keep burning hashes.
    await enforce_change_password_limit(user.id, settings)

    if not auth_service.verify_password(data.current_password, user.hashed_password):
        await log_action(
            db, action="password_change_failed", resource_type="user",
            resource_id=str(user.id), user_id=user.id, username=user.username,
            ip_address=get_client_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password",
        )

    # Phase D1: reject reuse against the last N hashes (no-op when depth=0).
    if await check_password_history(
        db, user, data.new_password, depth=settings.AUTH_PASSWORD_HISTORY_DEPTH,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"This password was used recently. "
                f"Pick one you haven't used in the last "
                f"{settings.AUTH_PASSWORD_HISTORY_DEPTH} change(s)."
            ),
        )

    # Capture the previous hash before we overwrite it.
    await record_password_history(db, user, depth=settings.AUTH_PASSWORD_HISTORY_DEPTH)
    user.hashed_password = auth_service.hash_password(data.new_password)
    forced = user.must_change_password
    user.must_change_password = False
    # Phase A: invalidate every other outstanding session for this user. The
    # bump is a no-op when token versioning is off; when it's on, the caller
    # gets a fresh token below so their current session keeps working.
    bump_password_version(user)

    await log_action(
        db,
        action="password_change",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        username=user.username,
        details={"forced_reset": forced},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    token, expires_in = auth_service.create_access_token(
        user.id, user.username, password_version=user.password_version,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/redeem-reset", response_model=TokenResponse)
async def redeem_password_reset(
    request: Request,
    data: PasswordResetRedeemRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
    _rate_limit: None = Depends(auth_rate_limiter),
):
    """Redeem an admin-issued one-shot password reset token (Phase C).

    The endpoint is unauthenticated by design — the token IS the credential.
    Lookup walks the user's outstanding tokens and verifies each via bcrypt
    so the plaintext token is never compared as a string. After a successful
    redemption the token is marked used, the password is rotated, the
    must-change flag clears, password_version bumps to evict any other
    sessions, and a fresh JWT is returned so the user lands signed in.

    Rejection paths return generic 401s so the caller can't tell whether
    the token was unknown, expired, or already used.
    """
    if settings.AUTH_PASSWORD_RESET_MODE not in ("reset_token", "both"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password reset tokens are not enabled on this server",
        )

    now = datetime.now(timezone.utc)
    rows = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    candidates = list(rows.scalars().all())
    matched = None
    for record in candidates:
        if auth_service.verify_password(data.token, record.token_hash):
            matched = record
            break

    if matched is None:
        await log_action(
            db, action="password_reset_redeem_failed", resource_type="password_reset_token",
            details={"reason": "unknown_or_expired"},
            ip_address=get_client_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reset token is invalid, expired, or already used",
        )

    user = await auth_service.get_user_by_id(db, matched.user_id)
    if user is None or not user.is_active:
        await log_action(
            db, action="password_reset_redeem_failed", resource_type="user",
            resource_id=str(matched.user_id),
            details={"reason": "user_missing_or_inactive"},
            ip_address=get_client_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reset token is invalid, expired, or already used",
        )

    if await check_password_history(
        db, user, data.new_password, depth=settings.AUTH_PASSWORD_HISTORY_DEPTH,
    ):
        # Don't burn the token on a recoverable input error — the operator
        # can issue a fresh one if reuse blocks the user out repeatedly.
        # Roll back first so the matched token's pending mutations don't
        # leak, then re-open a transaction just to record the audit entry —
        # security forensics want to see "user attempted reuse on token X."
        await db.rollback()
        try:
            await log_action(
                db, action="password_reset_redeem_failed", resource_type="user",
                resource_id=str(user.id), user_id=user.id, username=user.username,
                details={"reason": "password_reused", "token_id": matched.id},
                ip_address=get_client_ip(request),
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            # log_action already swallows its own errors; this guards the
            # commit() for paranoia. The user-facing 400 must always go out.
            await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"This password was used recently. "
                f"Pick one you haven't used in the last "
                f"{settings.AUTH_PASSWORD_HISTORY_DEPTH} change(s)."
            ),
        )

    await record_password_history(db, user, depth=settings.AUTH_PASSWORD_HISTORY_DEPTH)
    user.hashed_password = auth_service.hash_password(data.new_password)
    user.must_change_password = False
    bump_password_version(user)
    matched.used_at = now

    await log_action(
        db, action="password_reset_redeemed", resource_type="user",
        resource_id=str(user.id), user_id=user.id, username=user.username,
        details={"token_id": matched.id},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)

    token, expires_in = auth_service.create_access_token(
        user.id, user.username, password_version=user.password_version,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )
