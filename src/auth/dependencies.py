"""FastAPI dependencies for authentication"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.common import get_db, get_settings
from src.auth.models import User
from src.auth.service import AuthService
from src.config.settings import Settings
from src.observability.logging_config import set_user_id

logger = logging.getLogger(__name__)

# tokenUrl matches the login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(settings)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Require a valid JWT token. Raises 401 if missing/invalid."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(db, uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Phase A token versioning. A token whose `pv` claim is older than the
    # user's current password_version is rejected — this is how a password
    # change / admin reset evicts every active session. Tokens minted while
    # the feature was off carry no `pv` and are accepted as legacy so flipping
    # the flag does not boot every signed-in user instantly.
    token_pv = payload.get("pv")
    if token_pv is not None and int(token_pv) != int(user.password_version):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidated, please sign in again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Bind into the structlog contextvar so every log line emitted later in
    # the request carries user_id (Phase 24.1, gated by LOG_INCLUDE_USER_ID
    # in the middleware — set_user_id is a no-op when nothing reads it).
    try:
        set_user_id(str(user.id))
    except Exception:  # noqa: BLE001
        pass
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require an active user (get_current_user already checks is_active)."""
    return user


def _raise_or_none(require_auth: bool, detail: str) -> None:
    """Raise 401 if auth is required, otherwise return None (caller returns)."""
    if require_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """Return the current user if a valid token is provided, else None.

    When REQUIRE_AUTH is True, behaves like get_current_user (raises 401).
    When REQUIRE_AUTH is False (default), allows unauthenticated access.
    """
    if token is None:
        _raise_or_none(settings.REQUIRE_AUTH, "Authentication required")
        return None

    auth_service = get_auth_service(settings)
    payload = auth_service.decode_token(token)
    if payload is None:
        _raise_or_none(settings.REQUIRE_AUTH, "Invalid or expired token")
        return None

    user_id = payload.get("sub")
    if user_id is None:
        _raise_or_none(settings.REQUIRE_AUTH, "Invalid token payload")
        return None

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        _raise_or_none(settings.REQUIRE_AUTH, "Invalid token payload")
        return None

    user = await auth_service.get_user_by_id(db, uid)
    if user is None:
        _raise_or_none(settings.REQUIRE_AUTH, "User not found")
        return None

    token_pv = payload.get("pv")
    if token_pv is not None and int(token_pv) != int(user.password_version):
        _raise_or_none(settings.REQUIRE_AUTH, "Session invalidated, please sign in again")
        return None

    if not user.is_active:
        _raise_or_none(settings.REQUIRE_AUTH, "User account is deactivated")
        return None

    try:
        set_user_id(str(user.id))
    except Exception:  # noqa: BLE001
        pass
    return user


async def require_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    """Require an active admin user."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
