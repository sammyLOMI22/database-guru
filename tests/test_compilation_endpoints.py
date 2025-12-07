"""
Tests for Query Compilation API Endpoints

Tests cover:
- GET /api/compilation/stats - Global compilation statistics
- GET /api/compilation/metrics/{connection_id} - Per-connection metrics
- DELETE /api/compilation/cache/connection/{connection_id} - Invalidate connection cache
- DELETE /api/compilation/cache/table/{connection_id}/{table_name} - Invalidate table cache
- GET /api/compilation/invalidation-log - Compilation invalidation log

Part of Phase 4.2: Query Compilation Implementation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession


class TestCompilationEndpoints:
    """Tests for compilation API endpoints"""

    @pytest.fixture
    def mock_plan_cache(self):
        """Create a mock plan cache"""
        mock_cache = MagicMock()
        mock_cache.get_stats = MagicMock(return_value={
            "total_plans": 25,
            "cached_plans": 15,
            "total_lookups": 500,
            "hits": 300,
            "misses": 200,
            "hit_rate_percent": 60.0,
            "avg_lookup_ms": 3.2,
        })
        return mock_cache

    @pytest.fixture
    def mock_stmt_manager(self):
        """Create a mock prepared statement manager"""
        mock_manager = MagicMock()
        mock_manager.get_stats = MagicMock(return_value={
            "total_statements": 40,
            "prepared_statements": 18,
            "total_executions": 800,
            "avg_executions_per_statement": 20,
            "total_execution_ms": 4500.0,
            "avg_execution_ms": 5.625,
        })
        return mock_manager

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.mark.asyncio
    async def test_get_compilation_stats_success(self, mock_plan_cache, mock_stmt_manager, mock_db_session):
        """Test GET /api/compilation/stats returns global statistics"""
        # Mock database results for active connections
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (1, "postgres_db"),
            (2, "mysql_db"),
        ]

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock compiled metrics
        mock_metrics_1 = MagicMock()
        mock_metrics_1.total_executions = 100
        mock_metrics_1.total_execution_ms = 500.0
        mock_metrics_1.is_prepared = True
        mock_metrics_1.is_plan_cached = True

        mock_metrics_2 = MagicMock()
        mock_metrics_2.total_executions = 50
        mock_metrics_2.total_execution_ms = 200.0
        mock_metrics_2.is_prepared = False
        mock_metrics_2.is_plan_cached = True

        # Patch dependencies
        with patch('src.api.endpoints.compilation.get_plan_cache', return_value=mock_plan_cache), \
             patch('src.api.endpoints.compilation.get_prepared_statement_manager', return_value=mock_stmt_manager):

            # Import after patching
            from src.api.endpoints.compilation import get_compilation_stats

            result = await get_compilation_stats(db=mock_db_session)

            # Verify response structure
            assert result["success"] is True
            assert "plan_cache" in result
            assert "statement_manager" in result
            assert "databases" in result
            assert "timestamp" in result
            assert result["plan_cache"]["hit_rate_percent"] == 60.0

    @pytest.mark.asyncio
    async def test_get_compilation_stats_error(self, mock_db_session):
        """Test GET /api/compilation/stats handles errors gracefully"""
        # Mock database exception
        mock_db_session.execute.side_effect = Exception("Database error")

        with patch('src.api.endpoints.compilation.get_plan_cache', side_effect=Exception("Cache error")):
            from src.api.endpoints.compilation import get_compilation_stats

            result = await get_compilation_stats(db=mock_db_session)

            # Verify error handling
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_connection_metrics_success(self, mock_db_session):
        """Test GET /api/compilation/metrics/{connection_id} returns connection metrics"""
        connection_id = 1

        # Mock database connection query
        mock_connection = MagicMock()
        mock_connection.id = connection_id
        mock_connection.name = "postgres_db"
        mock_connection.database_type = "postgresql"

        # Mock metrics result
        mock_result = AsyncMock()
        mock_metric = MagicMock()
        mock_metric.id = 1
        mock_metric.normalized_hash = "abc123def456"
        mock_metric.template_sql = "SELECT * FROM users WHERE id = :p1 AND status = :p2"
        mock_metric.is_prepared = True
        mock_metric.is_plan_cached = True
        mock_metric.total_executions = 10
        mock_metric.total_execution_ms = 100.5
        mock_metric.avg_execution_ms = 10.05
        mock_metric.plan_cache_hits = 8
        mock_metric.plan_cache_misses = 2
        mock_metric.prepared_statement_hits = 9
        mock_metric.last_executed_at = datetime.utcnow()

        # Setup mock to return connection on first query, then metrics on second
        mock_results = [
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=mock_connection)),
            AsyncMock(fetchall=AsyncMock(return_value=[(mock_metric,)]))
        ]

        mock_db_session.execute = AsyncMock(side_effect=mock_results)

        from src.api.endpoints.compilation import get_connection_metrics

        result = await get_connection_metrics(
            connection_id=connection_id,
            limit=50,
            offset=0,
            db=mock_db_session
        )

        # Verify response
        assert result["success"] is True
        assert result["connection"]["id"] == connection_id
        assert result["connection"]["name"] == "postgres_db"
        assert "metrics" in result
        assert "summary" in result
        assert "pagination" in result

    @pytest.mark.asyncio
    async def test_get_connection_metrics_not_found(self, mock_db_session):
        """Test GET /api/compilation/metrics/{connection_id} with non-existent connection"""
        connection_id = 999

        # Mock connection not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        from src.api.endpoints.compilation import get_connection_metrics

        # Should raise HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_connection_metrics(
                connection_id=connection_id,
                limit=50,
                offset=0,
                db=mock_db_session
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_invalidate_connection_cache_success(self, mock_plan_cache, mock_stmt_manager, mock_db_session):
        """Test DELETE /api/compilation/cache/connection/{connection_id}"""
        connection_id = 1

        # Mock connection found
        mock_connection = MagicMock()
        mock_connection.id = connection_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=mock_connection)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock cache invalidation
        mock_plan_cache.invalidate_connection = AsyncMock(return_value=5)
        mock_stmt_manager.invalidate_connection = AsyncMock(return_value=3)

        with patch('src.api.endpoints.compilation.get_plan_cache', return_value=mock_plan_cache), \
             patch('src.api.endpoints.compilation.get_prepared_statement_manager', return_value=mock_stmt_manager):

            from src.api.endpoints.compilation import invalidate_connection_cache

            result = await invalidate_connection_cache(
                connection_id=connection_id,
                db=mock_db_session
            )

            # Verify result
            assert result["success"] is True
            assert result["plans_invalidated"] == 5
            assert result["statements_invalidated"] == 3
            assert "log_id" in result

    @pytest.mark.asyncio
    async def test_invalidate_connection_cache_not_found(self, mock_plan_cache, mock_stmt_manager, mock_db_session):
        """Test DELETE /api/compilation/cache/connection/{connection_id} with non-existent connection"""
        connection_id = 999

        # Mock connection not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch('src.api.endpoints.compilation.get_plan_cache', return_value=mock_plan_cache), \
             patch('src.api.endpoints.compilation.get_prepared_statement_manager', return_value=mock_stmt_manager):

            from src.api.endpoints.compilation import invalidate_connection_cache

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await invalidate_connection_cache(
                    connection_id=connection_id,
                    db=mock_db_session
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_invalidate_table_cache_success(self, mock_plan_cache, mock_db_session):
        """Test DELETE /api/compilation/cache/table/{connection_id}/{table_name}"""
        connection_id = 1
        table_name = "products"

        # Mock connection found
        mock_connection = MagicMock()
        mock_connection.id = connection_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=mock_connection)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock table invalidation
        mock_plan_cache.invalidate_table = AsyncMock(return_value=3)

        with patch('src.api.endpoints.compilation.get_plan_cache', return_value=mock_plan_cache), \
             patch('src.api.endpoints.compilation.get_prepared_statement_manager'):

            from src.api.endpoints.compilation import invalidate_table_cache

            result = await invalidate_table_cache(
                connection_id=connection_id,
                table_name=table_name,
                db=mock_db_session
            )

            # Verify result
            assert result["success"] is True
            assert result["table_name"] == table_name
            assert result["plans_invalidated"] == 3
            assert "log_id" in result

    @pytest.mark.asyncio
    async def test_invalidate_table_cache_not_found(self, mock_plan_cache, mock_db_session):
        """Test DELETE /api/compilation/cache/table/{connection_id}/{table_name} with non-existent connection"""
        connection_id = 999
        table_name = "products"

        # Mock connection not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch('src.api.endpoints.compilation.get_plan_cache', return_value=mock_plan_cache), \
             patch('src.api.endpoints.compilation.get_prepared_statement_manager'):

            from src.api.endpoints.compilation import invalidate_table_cache

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await invalidate_table_cache(
                    connection_id=connection_id,
                    table_name=table_name,
                    db=mock_db_session
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_invalidation_log_success(self, mock_db_session):
        """Test GET /api/compilation/invalidation-log returns recent invalidation entries"""
        # Mock invalidation log entry
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.connection_id = 1
        mock_log.table_name = "products"
        mock_log.invalidation_reason = "schema_change"
        mock_log.plans_invalidated = 5
        mock_log.statements_invalidated = 2
        mock_log.invalidated_at = datetime.utcnow()

        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=[(mock_log,)])
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        from src.api.endpoints.compilation import get_invalidation_log

        result = await get_invalidation_log(
            connection_id=None,
            limit=50,
            offset=0,
            db=mock_db_session
        )

        # Verify response
        assert result["success"] is True
        assert "entries" in result
        assert len(result["entries"]) >= 1
        assert "pagination" in result

    @pytest.mark.asyncio
    async def test_get_invalidation_log_filtered_by_connection(self, mock_db_session):
        """Test GET /api/compilation/invalidation-log filtered by connection_id"""
        connection_id = 1

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.connection_id = connection_id
        mock_log.table_name = None
        mock_log.invalidation_reason = "manual"
        mock_log.plans_invalidated = 10
        mock_log.statements_invalidated = 5
        mock_log.invalidated_at = datetime.utcnow()

        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=[(mock_log,)])
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        from src.api.endpoints.compilation import get_invalidation_log

        result = await get_invalidation_log(
            connection_id=connection_id,
            limit=50,
            offset=0,
            db=mock_db_session
        )

        # Verify response
        assert result["success"] is True
        assert len(result["entries"]) >= 1
        assert result["entries"][0]["connection_id"] == connection_id

    @pytest.mark.asyncio
    async def test_get_invalidation_log_pagination(self, mock_db_session):
        """Test GET /api/compilation/invalidation-log pagination"""
        # Create 51 mock logs to test pagination
        mock_logs = []
        for i in range(51):
            mock_log = MagicMock()
            mock_log.id = i
            mock_log.connection_id = 1
            mock_log.table_name = f"table_{i}"
            mock_log.invalidation_reason = "schema_change"
            mock_log.plans_invalidated = i
            mock_log.statements_invalidated = i // 2
            mock_log.invalidated_at = datetime.utcnow()
            mock_logs.append((mock_log,))

        mock_result = AsyncMock()
        mock_result.fetchall = AsyncMock(return_value=mock_logs)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        from src.api.endpoints.compilation import get_invalidation_log

        result = await get_invalidation_log(
            connection_id=None,
            limit=50,
            offset=0,
            db=mock_db_session
        )

        # Verify pagination
        assert result["success"] is True
        assert result["pagination"]["has_more"] is True
        assert len(result["entries"]) == 50
        assert result["pagination"]["limit"] == 50
        assert result["pagination"]["offset"] == 0

    @pytest.mark.asyncio
    async def test_invalidation_log_error_handling(self, mock_db_session):
        """Test GET /api/compilation/invalidation-log error handling"""
        # Mock database exception
        mock_db_session.execute.side_effect = Exception("Database error")

        from src.api.endpoints.compilation import get_invalidation_log

        result = await get_invalidation_log(
            connection_id=None,
            limit=50,
            offset=0,
            db=mock_db_session
        )

        # Verify error handling
        assert result["success"] is False
        assert "error" in result
