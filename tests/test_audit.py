"""Tests for Phase 21: Audit logging"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.audit import AuditLog, log_action, get_audit_logs


class TestLogAction:
    @pytest.mark.asyncio
    async def test_creates_audit_entry(self):
        db = AsyncMock(spec=AsyncSession)
        await log_action(
            db,
            action="create",
            resource_type="connection",
            resource_id="42",
            user_id=1,
            username="alice",
            ip_address="127.0.0.1",
        )
        db.add.assert_called_once()
        entry = db.add.call_args[0][0]
        assert isinstance(entry, AuditLog)
        assert entry.action == "create"
        assert entry.resource_type == "connection"
        assert entry.resource_id == "42"
        assert entry.user_id == 1
        assert entry.username == "alice"

    @pytest.mark.asyncio
    async def test_log_action_with_details(self):
        db = AsyncMock(spec=AsyncSession)
        details = {"name": "my-db", "type": "postgresql"}
        await log_action(
            db, action="delete", resource_type="connection",
            details=details,
        )
        entry = db.add.call_args[0][0]
        assert entry.details == details

    @pytest.mark.asyncio
    async def test_log_action_never_raises(self):
        """Even if DB fails, log_action should not raise."""
        db = AsyncMock(spec=AsyncSession)
        db.add.side_effect = RuntimeError("DB down")
        # Should not raise
        await log_action(db, action="test", resource_type="test")

    @pytest.mark.asyncio
    async def test_log_action_without_user(self):
        db = AsyncMock(spec=AsyncSession)
        await log_action(
            db, action="anonymous_action", resource_type="query",
        )
        entry = db.add.call_args[0][0]
        assert entry.user_id is None
        assert entry.username is None


class TestAuditLogModel:
    def test_audit_log_attributes(self):
        log = AuditLog(
            user_id=1,
            username="alice",
            action="login",
            resource_type="user",
            resource_id="1",
            ip_address="192.168.1.1",
        )
        assert log.action == "login"
        assert log.resource_type == "user"
        assert log.ip_address == "192.168.1.1"

    def test_audit_log_nullable_fields(self):
        log = AuditLog(action="test", resource_type="test")
        assert log.user_id is None
        assert log.details is None
        assert log.ip_address is None


class TestGetAuditLogs:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            AuditLog(id=1, action="login", resource_type="user"),
        ]
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        logs = await get_audit_logs(db)
        assert len(logs) == 1
        assert logs[0].action == "login"

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self):
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        await get_audit_logs(db, user_id=42)
        # Verify execute was called (filter applied)
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_by_action(self):
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        await get_audit_logs(db, action="login")
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_by_resource_type(self):
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        await get_audit_logs(db, resource_type="connection")
        db.execute.assert_called_once()


# ── Admin endpoint authorization ──────────────────────────────────

class TestAuditEndpointAuthorization:
    """Verify admin-only access control on audit log endpoints."""

    @pytest.mark.asyncio
    async def test_require_admin_rejects_non_admin(self):
        """Non-admin user gets 403 on require_admin dependency."""
        from src.auth.dependencies import require_admin
        from fastapi import HTTPException

        user = MagicMock()
        user.is_admin = False
        user.is_active = True

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=user)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin(self):
        """Admin user passes require_admin dependency."""
        from src.auth.dependencies import require_admin

        user = MagicMock()
        user.is_admin = True
        user.is_active = True

        result = await require_admin(user=user)
        assert result == user


class TestLogActionSavepointOnFailure:
    """Verify log_action uses a savepoint so failures don't roll back the caller's transaction."""

    @pytest.mark.asyncio
    async def test_log_action_does_not_rollback_main_transaction(self):
        """If the audit insert fails, the main session transaction is preserved."""
        db = AsyncMock(spec=AsyncSession)
        # Simulate begin_nested raising (e.g. missing audit_logs table)
        nested_ctx = AsyncMock()
        nested_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("DB write error"))
        nested_ctx.__aexit__ = AsyncMock(return_value=False)
        db.begin_nested.return_value = nested_ctx

        await log_action(db, action="test", resource_type="test")

        # Must NOT call rollback on the main session
        db.rollback.assert_not_called()
        # Should have attempted a savepoint
        db.begin_nested.assert_called_once()
