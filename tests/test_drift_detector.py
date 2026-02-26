"""Tests for DriftDetector (Phase 20.1)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.migration.drift_detector import DriftDetector
from src.migration.schema_comparator import SchemaDiff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_connection(id=1, name="test_db"):
    conn = MagicMock()
    conn.id = id
    conn.name = name
    return conn


def _simple_schema(tables=None):
    return {"tables": tables or {}, "relationships": [], "summary": {}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDriftDetector:
    def setup_method(self):
        self.detector = DriftDetector()

    @pytest.mark.asyncio
    async def test_no_drift_when_fingerprints_match(self):
        """When fingerprints match, return empty diff without re-comparing."""
        conn = _make_connection()
        baseline = _simple_schema({"users": {
            "columns": [{"name": "id", "type": "INT"}],
            "primary_keys": [], "foreign_keys": [], "indexes": [],
        }})
        fingerprint = "abc123"

        with patch.object(self.detector, '_get_current_schema', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = baseline
            with patch('src.migration.drift_detector.SchemaCache') as mock_cache:
                mock_cache.create_fingerprint_from_schema_dict.return_value = fingerprint

                result = await self.detector.detect_drift(conn, baseline, fingerprint)

        assert result.overall_risk == "none"
        assert result.diff_summary == "No differences found"
        assert result.source_connection_id == conn.id
        assert result.target_connection_id == conn.id

    @pytest.mark.asyncio
    async def test_drift_detected_when_fingerprints_differ(self):
        """When fingerprints differ, compare schemas and return diff."""
        conn = _make_connection()
        baseline = _simple_schema({"users": {
            "columns": [{"name": "id", "type": "INT"}],
            "primary_keys": [], "foreign_keys": [], "indexes": [],
        }})
        current = _simple_schema({
            "users": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "email", "type": "TEXT", "nullable": True},
                ],
                "primary_keys": [], "foreign_keys": [], "indexes": [],
            }
        })

        with patch.object(self.detector, '_get_current_schema', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = current
            with patch('src.migration.drift_detector.SchemaCache') as mock_cache:
                mock_cache.create_fingerprint_from_schema_dict.return_value = "different_fingerprint"

                result = await self.detector.detect_drift(conn, baseline, "original_fingerprint")

        assert result.source_fingerprint == "original_fingerprint"
        assert result.target_fingerprint == "different_fingerprint"
        assert len(result.table_diffs) > 0
        assert result.table_diffs[0].table_name == "users"

    @pytest.mark.asyncio
    async def test_drift_table_added(self):
        """Detect when a new table appears in the live schema."""
        conn = _make_connection()
        baseline = _simple_schema({})
        current = _simple_schema({"new_table": {
            "columns": [{"name": "id", "type": "INT"}],
            "primary_keys": [], "foreign_keys": [], "indexes": [],
        }})

        with patch.object(self.detector, '_get_current_schema', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = current
            with patch('src.migration.drift_detector.SchemaCache') as mock_cache:
                mock_cache.create_fingerprint_from_schema_dict.return_value = "new_fp"

                result = await self.detector.detect_drift(conn, baseline, "old_fp")

        assert any(td.diff_type == "added" and td.table_name == "new_table" for td in result.table_diffs)

    @pytest.mark.asyncio
    async def test_drift_table_removed(self):
        """Detect when a table is dropped from the live schema."""
        conn = _make_connection()
        baseline = _simple_schema({"gone_table": {
            "columns": [{"name": "id", "type": "INT"}],
            "primary_keys": [], "foreign_keys": [], "indexes": [],
        }})
        current = _simple_schema({})

        with patch.object(self.detector, '_get_current_schema', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = current
            with patch('src.migration.drift_detector.SchemaCache') as mock_cache:
                mock_cache.create_fingerprint_from_schema_dict.return_value = "new_fp"

                result = await self.detector.detect_drift(conn, baseline, "old_fp")

        assert any(td.diff_type == "removed" and td.table_name == "gone_table" for td in result.table_diffs)
        assert result.overall_risk == "critical"

    @pytest.mark.asyncio
    async def test_connection_ids_set(self):
        """Both source and target connection IDs should be the same connection."""
        conn = _make_connection(id=42)
        baseline = _simple_schema({})

        with patch.object(self.detector, '_get_current_schema', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = baseline
            with patch('src.migration.drift_detector.SchemaCache') as mock_cache:
                mock_cache.create_fingerprint_from_schema_dict.return_value = "same_fp"

                result = await self.detector.detect_drift(conn, baseline, "same_fp")

        assert result.source_connection_id == 42
        assert result.target_connection_id == 42
