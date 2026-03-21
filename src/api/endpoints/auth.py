"""Authentication endpoints — register, login, me"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth.dependencies import get_current_active_user, get_auth_service
from src.auth.models import User
from src.auth.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from src.auth.audit import log_action
from src.auth.service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user and return a JWT token."""
    try:
        user = await auth_service.register(db, data.email, data.username, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    await log_action(
        db, action="register", resource_type="user", resource_id=str(user.id),
        user_id=user.id, username=user.username,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    token, expires_in = auth_service.create_access_token(user.id, user.username)
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
):
    """Authenticate and return a JWT token."""
    user = await auth_service.authenticate(db, data.username, data.password)
    if user is None:
        await log_action(
            db, action="login_failed", resource_type="user",
            details={"username": data.username},
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    await log_action(
        db, action="login", resource_type="user", resource_id=str(user.id),
        user_id=user.id, username=user.username,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    token, expires_in = auth_service.create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_active_user)):
    """Return the current authenticated user."""
    return UserResponse.model_validate(user)
