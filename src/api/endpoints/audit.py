"""Audit log endpoints (Phase 21 + Phase 24 admin UI)"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth.audit import (
    get_audit_facets,
    list_and_count_audit_logs,
)
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


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    limit: int
    offset: int


class AuditFacetsResponse(BaseModel):
    actions: List[str]
    resource_types: List[str]


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List audit logs (admin only) with filters and pagination."""
    logs, total = await list_and_count_audit_logs(
        db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/logs/me", response_model=AuditLogListResponse)
async def list_my_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """List audit logs for the current user."""
    logs, total = await list_and_count_audit_logs(
        db,
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/facets", response_model=AuditFacetsResponse)
async def list_audit_facets(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Return distinct action/resource_type values to populate filter dropdowns."""
    facets = await get_audit_facets(db)
    return AuditFacetsResponse(**facets)
