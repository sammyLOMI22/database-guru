"""Audit log endpoints (Phase 21)"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth.audit import get_audit_logs
from src.auth.dependencies import get_current_active_user, require_admin
from src.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get("/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all audit logs (admin only)."""
    logs = await get_audit_logs(
        db, action=action, resource_type=resource_type, limit=limit, offset=offset,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/logs/me", response_model=List[AuditLogResponse])
async def list_my_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """List audit logs for the current user."""
    logs = await get_audit_logs(
        db, user_id=user.id, action=action, resource_type=resource_type,
        limit=limit, offset=offset,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]
