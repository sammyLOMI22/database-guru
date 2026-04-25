"""Admin user-management endpoints (Phase 24).

All endpoints are gated by `require_admin` and write to the audit log.
The `/api/auth/*` flow continues to handle self-service register/login —
this router exists for operator-driven CRUD against existing accounts.
"""
import logging
import secrets
import string
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth.audit import log_action
from src.auth.dependencies import get_auth_service, require_admin
from src.auth.models import User
from src.auth.service import AuthService
from src.middleware.rate_limit import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────


class AdminUserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    items: List[AdminUserResponse]
    total: int
    limit: int
    offset: int


class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=12, max_length=128)
    is_admin: bool = False


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class AdminPasswordResetResponse(BaseModel):
    user_id: int
    temporary_password: str
    detail: str = "Share this password securely. The user should change it on next login."


# ── Helpers ──────────────────────────────────────────────────────────


_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def _generate_temp_password(length: int = 16) -> str:
    """Generate a temporary password that satisfies the UserCreate complexity rules."""
    while True:
        candidate = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
        if (
            any(c.isupper() for c in candidate)
            and any(c.islower() for c in candidate)
            and any(c.isdigit() for c in candidate)
        ):
            return candidate


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List users with optional search/filters."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    base = select(User)
    if search:
        like = f"%{search}%"
        base = base.where(or_(User.username.ilike(like), User.email.ilike(like)))
    if is_active is not None:
        base = base.where(User.is_active == is_active)
    if is_admin is not None:
        base = base.where(User.is_admin == is_admin)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = int(total_result.scalar() or 0)

    rows = await db.execute(base.order_by(User.id).limit(limit).offset(offset))
    users = list(rows.scalars().all())

    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    admin: User = Depends(require_admin),
):
    """Create a user account on behalf of an operator."""
    try:
        user = await auth_service.register(db, data.email, data.username, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    if data.is_admin:
        user.is_admin = True
        await db.flush()

    await log_action(
        db,
        action="admin_create_user",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        username=admin.username,
        details={"created_username": user.username, "is_admin": user.is_admin},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    request: Request,
    user_id: int,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update is_active / is_admin for a user."""
    user = await _get_user_or_404(db, user_id)

    if user.id == admin.id:
        # Prevent the admin from locking themselves out via the same UI.
        if data.is_admin is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot demote themselves",
            )
        if data.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admins cannot deactivate themselves",
            )

    changes: dict = {}
    if data.is_active is not None and data.is_active != user.is_active:
        changes["is_active"] = {"from": user.is_active, "to": data.is_active}
        user.is_active = data.is_active
    if data.is_admin is not None and data.is_admin != user.is_admin:
        changes["is_admin"] = {"from": user.is_admin, "to": data.is_admin}
        user.is_admin = data.is_admin

    if changes:
        await log_action(
            db,
            action="admin_update_user",
            resource_type="user",
            resource_id=str(user.id),
            user_id=admin.id,
            username=admin.username,
            details={"target_username": user.username, "changes": changes},
            ip_address=get_client_ip(request),
        )

    await db.commit()
    await db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=AdminPasswordResetResponse)
async def reset_user_password(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    admin: User = Depends(require_admin),
):
    """Reset a user's password to a generated temporary value."""
    user = await _get_user_or_404(db, user_id)
    temp_password = _generate_temp_password()
    user.hashed_password = auth_service.hash_password(temp_password)

    await log_action(
        db,
        action="admin_reset_password",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        username=admin.username,
        details={"target_username": user.username},
        ip_address=get_client_ip(request),
    )
    await db.commit()

    return AdminPasswordResetResponse(
        user_id=user.id,
        temporary_password=temp_password,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Soft-delete a user (sets is_active=False). Idempotent."""
    user = await _get_user_or_404(db, user_id)

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate themselves",
        )

    if user.is_active:
        user.is_active = False
        await log_action(
            db,
            action="admin_deactivate_user",
            resource_type="user",
            resource_id=str(user.id),
            user_id=admin.id,
            username=admin.username,
            details={"target_username": user.username},
            ip_address=get_client_ip(request),
        )

    await db.commit()
    return None
