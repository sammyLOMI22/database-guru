"""Audit logging for security-sensitive operations (Phase 21)"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """Record of security-relevant actions for compliance and debugging."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'timestamp'),
        Index('idx_audit_action_resource', 'action', 'resource_type'),
    )


async def log_action(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Write an audit log entry. Never raises — failures are logged and swallowed."""
    try:
        async with db.begin_nested():
            entry = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                details=details,
                ip_address=ip_address,
            )
            db.add(entry)
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def _apply_audit_filters(
    query,
    *,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date is not None:
        query = query.where(AuditLog.timestamp >= start_date)
    if end_date is not None:
        query = query.where(AuditLog.timestamp <= end_date)
    return query


async def get_audit_logs(
    db: AsyncSession,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    """Query audit logs with optional filters."""
    query = _apply_audit_filters(
        select(AuditLog).order_by(desc(AuditLog.timestamp)),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_audit_logs(
    db: AsyncSession,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> int:
    """Count audit logs matching the same filters as get_audit_logs."""
    query = _apply_audit_filters(
        select(func.count()).select_from(AuditLog),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def get_audit_facets(db: AsyncSession) -> Dict[str, list]:
    """Return distinct action/resource_type values for filter dropdowns."""
    actions_q = select(AuditLog.action).distinct().order_by(AuditLog.action)
    resources_q = select(AuditLog.resource_type).distinct().order_by(AuditLog.resource_type)
    actions = (await db.execute(actions_q)).scalars().all()
    resources = (await db.execute(resources_q)).scalars().all()
    return {
        "actions": [a for a in actions if a],
        "resource_types": [r for r in resources if r],
    }
