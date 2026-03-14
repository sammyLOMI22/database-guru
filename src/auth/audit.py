"""Audit logging for security-sensitive operations (Phase 21)"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, select, desc
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
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

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
        await db.flush()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


async def get_audit_logs(
    db: AsyncSession,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    """Query audit logs with optional filters."""
    query = select(AuditLog).order_by(desc(AuditLog.timestamp))

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())
