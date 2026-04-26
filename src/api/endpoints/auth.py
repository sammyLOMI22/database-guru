"""Authentication endpoints — register, login, me"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth.dependencies import get_current_active_user, get_auth_service
from src.auth.models import User
from src.auth.schemas import (
    PasswordChangeRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.auth.audit import log_action
from src.auth.service import AuthService, bump_password_version
from src.api.dependencies.common import get_settings
from src.config.settings import Settings
from src.middleware.rate_limit import auth_rate_limiter, get_client_ip

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
    _rate_limit: None = Depends(auth_rate_limiter),
):
    """Authenticate and return a JWT token."""
    user = await auth_service.authenticate(db, data.username, data.password)
    if user is None:
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
):
    """Change the current user's password.

    Required after an admin password reset (User.must_change_password=True),
    but available to any authenticated user. Verifies the current password,
    enforces complexity on the new one, clears the must-change flag, bumps
    ``password_version`` to evict other sessions, and returns a fresh token
    so the caller stays signed in on this device.
    """
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
