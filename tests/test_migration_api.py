"""Tests for Migration API Endpoints (Phase 20)"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database.models import MigrationProject, DatabaseConnection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_diff_snapshot():
    return {
        "source_connection_id": 1,
        "target_connection_id": 2,
        "source_fingerprint": "abc",
        "target_fingerprint": "def",
        "table_diffs": [
            {
                "table_name": "users",
                "diff_type": "modified",
                "column_diffs": [
                    {
                        "table_name": "users",
                        "column_name": "email",
                        "diff_type": "added",
                        "source_state": None,
                        "target_state": {"name": "email", "type": "VARCHAR(255)", "nullable": True},
                        "is_breaking": False,
                        "risk_level": "low",
                    }
                ],
                "constraint_diffs": [],
                "risk_level": "low",
            }
        ],
        "total_breaking_changes": 0,
        "total_safe_changes": 1,
        "overall_risk": "low",
        "diff_summary": "1 table modified",
        "compared_at": "2026-01-01T00:00:00",
    }


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    return session


# ---------------------------------------------------------------------------
# Project CRUD tests (unit-level with mocks)
# ---------------------------------------------------------------------------

class TestMigrationProjectCRUD:
    """Test the endpoint logic via direct function calls with mocked DB."""

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, mock_db_session):
        """_get_project raises 404 for missing project."""
        from src.api.endpoints.migration import _get_project
        from fastapi import HTTPException

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await _get_project(mock_db_session, 999)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_connection_not_found(self, mock_db_session):
        """_get_connection raises 404 for missing connection."""
        from src.api.endpoints.migration import _get_connection
        from fastapi import HTTPException

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await _get_connection(mock_db_session, 999)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Script download tests
# ---------------------------------------------------------------------------

class TestScriptDownload:
    @pytest.mark.asyncio
    async def test_download_invalid_filename(self, mock_db_session):
        """download_script raises 400 for invalid filename."""
        from src.api.endpoints.migration import download_script
        from fastapi import HTTPException

        # Mock project exists
        project = MagicMock()
        project.up_sql = "UP"
        project.down_sql = "DOWN"
        project.verify_sql = "VERIFY"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await download_script(1, "bad.sql", mock_db_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_download_not_generated(self, mock_db_session):
        """download_script raises 404 when script not yet generated."""
        from src.api.endpoints.migration import download_script
        from fastapi import HTTPException

        project = MagicMock()
        project.up_sql = None
        project.down_sql = None
        project.verify_sql = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await download_script(1, "up.sql", mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_download_valid_script(self, mock_db_session):
        """download_script returns PlainTextResponse for valid script."""
        from src.api.endpoints.migration import download_script

        project = MagicMock()
        project.up_sql = "CREATE TABLE test;"
        project.down_sql = "DROP TABLE test;"
        project.verify_sql = "SELECT 1;"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        response = await download_script(1, "up.sql", mock_db_session)
        assert response.body.decode() == "CREATE TABLE test;"


# ---------------------------------------------------------------------------
# Plan generation tests
# ---------------------------------------------------------------------------

class TestPlanGeneration:
    @pytest.mark.asyncio
    async def test_generate_plan_no_diff(self, mock_db_session):
        """generate_plan raises 400 when project has no diff snapshot."""
        from src.api.endpoints.migration import generate_plan
        from fastapi import HTTPException

        project = MagicMock()
        project.diff_snapshot = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await generate_plan(1, mock_db_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_plan_not_generated(self, mock_db_session):
        """get_plan raises 404 when no plan exists."""
        from src.api.endpoints.migration import get_plan
        from fastapi import HTTPException

        project = MagicMock()
        project.migration_plan = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_plan(1, mock_db_session)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Scripts generation tests
# ---------------------------------------------------------------------------

class TestScriptsGeneration:
    @pytest.mark.asyncio
    async def test_generate_scripts_no_diff(self, mock_db_session):
        """generate_scripts raises 400 when project has no diff."""
        from src.api.endpoints.migration import generate_scripts
        from src.models.schemas import GenerateScriptsRequest
        from fastapi import HTTPException

        project = MagicMock()
        project.diff_snapshot = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        request = GenerateScriptsRequest(target_dialect="postgresql")

        with pytest.raises(HTTPException) as exc_info:
            await generate_scripts(1, request, mock_db_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_scripts_not_generated(self, mock_db_session):
        """get_scripts raises 404 when no scripts exist."""
        from src.api.endpoints.migration import get_scripts
        from fastapi import HTTPException

        project = MagicMock()
        project.up_sql = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_scripts(1, mock_db_session)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Data migration tests
# ---------------------------------------------------------------------------

class TestDataMigrationEndpoint:
    @pytest.mark.asyncio
    async def test_generate_data_migration_no_diff(self, mock_db_session):
        """generate_data_migration raises 400 when project has no diff."""
        from src.api.endpoints.migration import generate_data_migration
        from fastapi import HTTPException

        project = MagicMock()
        project.diff_snapshot = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await generate_data_migration(1, 1000, mock_db_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_data_migration_not_generated(self, mock_db_session):
        """get_data_migration raises 404 when no plan exists."""
        from src.api.endpoints.migration import get_data_migration
        from fastapi import HTTPException

        project = MagicMock()
        project.data_migration_plan = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_data_migration(1, mock_db_session)
        assert exc_info.value.status_code == 404
