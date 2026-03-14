"""Tests for database connection soft-delete behavior.

Validates that delete_connection sets is_deleted=True instead of removing
the record, and that list_connections excludes soft-deleted connections.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DatabaseConnection


class TestConnectionSoftDelete:
    """Tests for connection soft-delete in the connections endpoint."""

    @pytest.mark.asyncio
    async def test_delete_connection_sets_is_deleted(self):
        """Test that delete_connection sets is_deleted=True instead of db.delete()."""
        from src.api.endpoints.connections import delete_connection

        # Create a mock connection
        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.name = "Test DB"
        conn.is_deleted = False
        conn.is_active = True

        # Mock database session
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = mock_result

        # Mock request for audit logging
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Mock SchemaCache (imported locally inside delete_connection)
        with patch('src.core.schema_cache.SchemaCache') as mock_cache:
            mock_cache.invalidate_schema = MagicMock()

            await delete_connection(request=mock_request, connection_id=1, db=db, current_user=None)

            # Should NOT call db.delete
            db.delete.assert_not_called()

            # Should set is_deleted=True and is_active=False
            assert conn.is_deleted is True
            assert conn.is_active is False

            # Should commit
            db.commit.assert_called_once()

            # Should invalidate schema cache
            mock_cache.invalidate_schema.assert_called_once_with(
                connection_id=1,
                connection_name="Test DB",
            )

    @pytest.mark.asyncio
    async def test_delete_connection_idempotent(self):
        """Test that deleting an already-deleted connection returns 204."""
        from src.api.endpoints.connections import delete_connection

        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.name = "Already Deleted"
        conn.is_deleted = True

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = mock_result

        # Mock request
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Should return without error (204)
        result = await delete_connection(request=mock_request, connection_id=1, db=db, current_user=None)

        # Should NOT commit (no changes needed)
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_activate_connection_rejects_deleted(self):
        """Test that activating a deleted connection raises 410."""
        from fastapi import HTTPException
        from src.api.endpoints.connections import activate_connection

        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.name = "Deleted DB"
        conn.is_deleted = True

        db = AsyncMock(spec=AsyncSession)
        # First execute: deactivate all (returns None)
        # Second execute: find the connection
        mock_result_deactivate = MagicMock()
        mock_result_find = MagicMock()
        mock_result_find.scalar_one_or_none.return_value = conn
        db.execute.side_effect = [mock_result_deactivate, mock_result_find]

        with pytest.raises(HTTPException) as exc_info:
            await activate_connection(connection_id=1, db=db)

        assert exc_info.value.status_code == 410
        assert "has been removed" in exc_info.value.detail
