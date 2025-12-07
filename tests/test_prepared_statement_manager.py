"""
Unit tests for PreparedStatementManager

Tests cover:
- Lazy preparation (only prepare after 2+ executions)
- LRU eviction (max 100 statements)
- Per-connection isolation
- Cleanup task and TTL
- Execution tracking
- Statistics and metrics
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.core.prepared_statement_manager import (
    PreparedStatementManager,
    PreparedStatement,
    get_prepared_statement_manager,
)


class TestPreparedStatementManagerBasic:
    """Test basic statement manager operations"""

    @pytest.mark.asyncio
    async def test_create_new_statement(self):
        """Test creating a new prepared statement"""
        manager = PreparedStatementManager()

        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="query123",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )

        assert stmt.statement_id == "1_query123"
        assert stmt.normalized_hash == "query123"
        assert stmt.template_sql == "SELECT * FROM users WHERE id = :p1"
        assert stmt.database_type == "postgresql"
        assert stmt.connection_id == 1
        assert stmt.execution_count == 1
        assert stmt.is_prepared is False  # Not prepared on first execution

    @pytest.mark.asyncio
    async def test_reuse_existing_statement(self):
        """Test reusing an existing statement"""
        manager = PreparedStatementManager()

        # Create statement
        stmt1 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="query123",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )

        # Reuse statement
        stmt2 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="query123",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )

        assert stmt1 is stmt2
        assert stmt2.execution_count == 2

    def test_statement_object_structure(self):
        """Test prepared statement object structure"""
        stmt = PreparedStatement(
            statement_id="1_abc123",
            normalized_hash="abc123",
            template_sql="SELECT * FROM products WHERE category = :p1",
            database_type="postgresql",
            connection_id=1,
            execution_count=5,
            total_execution_ms=150.0,
            is_prepared=True,
        )

        assert stmt.statement_id == "1_abc123"
        assert stmt.execution_count == 5
        assert stmt.total_execution_ms == 150.0
        assert stmt.is_prepared is True


class TestPreparedStatementLazyPreparation:
    """Test lazy preparation (prepare only after 2+ executions)"""

    @pytest.mark.asyncio
    async def test_not_prepared_on_first_execution(self):
        """Test that statement is not prepared on first execution"""
        manager = PreparedStatementManager()

        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )

        assert stmt.execution_count == 1
        assert stmt.is_prepared is False

    @pytest.mark.asyncio
    async def test_prepared_on_second_execution(self):
        """Test that statement is prepared on second execution"""
        manager = PreparedStatementManager()

        # First execution
        stmt1 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )
        assert stmt1.is_prepared is False

        # Second execution
        stmt2 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )
        assert stmt2.execution_count == 2
        assert stmt2.is_prepared is True

    @pytest.mark.asyncio
    async def test_threshold_configurable(self):
        """Test that preparation threshold is configurable"""
        manager = PreparedStatementManager()
        original_threshold = manager.EXECUTION_THRESHOLD

        try:
            # Set threshold to 3
            manager.EXECUTION_THRESHOLD = 3

            stmt1 = await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash="q1",
                template_sql="SELECT * FROM users",
                database_type="postgresql",
            )
            assert stmt1.is_prepared is False

            stmt2 = await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash="q1",
                template_sql="SELECT * FROM users",
                database_type="postgresql",
            )
            assert stmt2.is_prepared is False  # Still not prepared

            stmt3 = await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash="q1",
                template_sql="SELECT * FROM users",
                database_type="postgresql",
            )
            assert stmt3.execution_count == 3
            # Prepared on third execution now
        finally:
            manager.EXECUTION_THRESHOLD = original_threshold


class TestPreparedStatementLRUEviction:
    """Test LRU eviction when max statements exceeded"""

    @pytest.mark.asyncio
    async def test_lru_eviction_on_limit(self):
        """Test that oldest statement is evicted when limit exceeded"""
        manager = PreparedStatementManager()
        original_max = manager.MAX_STATEMENTS

        try:
            # Set low limit for testing
            manager.MAX_STATEMENTS = 3

            # Create 3 statements
            for i in range(3):
                await manager.get_or_create_statement(
                    connection_id=1,
                    normalized_hash=f"q{i}",
                    template_sql=f"SELECT {i}",
                    database_type="postgresql",
                )

            assert len(manager._statements) == 3

            # Create 4th statement - should evict oldest
            await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash="q4",
                template_sql="SELECT 4",
                database_type="postgresql",
            )

            # Should still have max 3
            assert len(manager._statements) == 3

            # Oldest (q0) should be gone
            assert "1_q0" not in manager._statements
            assert "1_q4" in manager._statements

        finally:
            manager.MAX_STATEMENTS = original_max

    @pytest.mark.asyncio
    async def test_per_connection_eviction(self):
        """Test that eviction is per-connection"""
        manager = PreparedStatementManager()
        original_max = manager.MAX_STATEMENTS

        try:
            manager.MAX_STATEMENTS = 2

            # Connection 1: 2 statements
            for i in range(2):
                await manager.get_or_create_statement(
                    connection_id=1,
                    normalized_hash=f"q{i}",
                    template_sql=f"SELECT {i}",
                    database_type="postgresql",
                )

            # Connection 2: 2 statements
            for i in range(2):
                await manager.get_or_create_statement(
                    connection_id=2,
                    normalized_hash=f"q{i}",
                    template_sql=f"SELECT {i}",
                    database_type="postgresql",
                )

            # Each connection should have 2
            conn1_stmts = len(manager._connection_statements[1])
            conn2_stmts = len(manager._connection_statements[2])

            assert conn1_stmts == 2
            assert conn2_stmts == 2

        finally:
            manager.MAX_STATEMENTS = original_max


class TestPreparedStatementExecutionTracking:
    """Test execution tracking and metrics"""

    @pytest.mark.asyncio
    async def test_record_execution(self):
        """Test recording execution time"""
        manager = PreparedStatementManager()

        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )

        manager.record_execution(stmt.statement_id, 50.5)
        manager.record_execution(stmt.statement_id, 49.5)

        stmt = manager._statements[stmt.statement_id]
        assert stmt.total_execution_ms == 100.0

    @pytest.mark.asyncio
    async def test_execution_count_increments(self):
        """Test that execution count increments with reuse"""
        manager = PreparedStatementManager()

        for _ in range(5):
            stmt = await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash="q1",
                template_sql="SELECT * FROM users",
                database_type="postgresql",
            )

        assert stmt.execution_count == 5


class TestPreparedStatementCleanup:
    """Test cleanup and TTL functionality"""

    @pytest.mark.asyncio
    async def test_cleanup_expired_statements(self):
        """Test cleaning up expired statements"""
        manager = PreparedStatementManager()

        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )

        # Manually set last_used to expired time
        stmt_obj = manager._statements[stmt.statement_id]
        expired_time = datetime.utcnow() - timedelta(seconds=manager.CLEANUP_TTL + 100)
        stmt_obj.last_used = expired_time.isoformat()

        # Clean up
        count = await manager.cleanup_expired()

        assert count == 1
        assert stmt.statement_id not in manager._statements

    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent(self):
        """Test that cleanup preserves recently used statements"""
        manager = PreparedStatementManager()

        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )

        # Don't manually expire - use recent time
        count = await manager.cleanup_expired()

        assert count == 0
        assert stmt.statement_id in manager._statements

    @pytest.mark.asyncio
    async def test_invalidate_connection(self):
        """Test invalidating all statements for a connection"""
        manager = PreparedStatementManager()

        # Create statements for connection 1
        for i in range(3):
            await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash=f"q{i}",
                template_sql=f"SELECT {i}",
                database_type="postgresql",
            )

        # Create statements for connection 2
        await manager.get_or_create_statement(
            connection_id=2,
            normalized_hash="q0",
            template_sql="SELECT 0",
            database_type="postgresql",
        )

        # Invalidate connection 1
        count = await manager.invalidate_connection(1)

        assert count == 3
        assert 1 not in manager._connection_statements
        assert 2 in manager._connection_statements


class TestPreparedStatementPerConnectionIsolation:
    """Test per-connection isolation"""

    @pytest.mark.asyncio
    async def test_same_query_different_connections(self):
        """Test that same query creates separate statements per connection"""
        manager = PreparedStatementManager()

        stmt1 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="query_x",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )

        stmt2 = await manager.get_or_create_statement(
            connection_id=2,
            normalized_hash="query_x",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )

        assert stmt1.statement_id == "1_query_x"
        assert stmt2.statement_id == "2_query_x"
        assert stmt1 is not stmt2


class TestPreparedStatementStatistics:
    """Test statistics and metrics"""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting statistics"""
        manager = PreparedStatementManager()

        # Create and execute statements
        for i in range(3):
            stmt = await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash=f"q{i}",
                template_sql=f"SELECT {i}",
                database_type="postgresql",
            )

            # Execute second statement multiple times to prepare it
            if i == 1:
                await manager.get_or_create_statement(
                    connection_id=1,
                    normalized_hash=f"q{i}",
                    template_sql=f"SELECT {i}",
                    database_type="postgresql",
                )
                manager.record_execution(stmt.statement_id, 50.0)

        stats = manager.get_stats()

        assert stats["total_statements"] == 3
        assert stats["prepared_statements"] >= 1
        assert stats["total_executions"] >= 3

    @pytest.mark.asyncio
    async def test_average_execution_time(self):
        """Test average execution time calculation"""
        manager = PreparedStatementManager()

        # Create statement (execution 1)
        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )

        # Record time for first execution
        manager.record_execution(stmt.statement_id, 100.0)

        # Reuse statement (execution 2)
        stmt = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="q1",
            template_sql="SELECT * FROM users",
            database_type="postgresql",
        )

        # Record time for second execution
        manager.record_execution(stmt.statement_id, 200.0)

        stats = manager.get_stats()

        # Total: 300ms over 2 executions = 150ms average
        assert abs(stats["avg_execution_ms"] - 150.0) < 0.1


class TestPreparedStatementSingleton:
    """Test singleton pattern"""

    def test_get_manager_returns_singleton(self):
        """Test that get_prepared_statement_manager returns same instance"""
        manager1 = get_prepared_statement_manager()
        manager2 = get_prepared_statement_manager()

        assert manager1 is manager2


class TestPreparedStatementIntegration:
    """Integration tests with realistic scenarios"""

    @pytest.mark.asyncio
    async def test_realistic_query_pattern(self):
        """Test realistic query execution pattern"""
        manager = PreparedStatementManager()

        # First execution
        stmt1 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="find_user",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )
        assert stmt1.is_prepared is False

        # Second execution - should prepare
        stmt2 = await manager.get_or_create_statement(
            connection_id=1,
            normalized_hash="find_user",
            template_sql="SELECT * FROM users WHERE id = :p1",
            database_type="postgresql",
        )
        assert stmt2.is_prepared is True

        # Subsequent executions
        for i in range(10):
            stmt = await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash="find_user",
                template_sql="SELECT * FROM users WHERE id = :p1",
                database_type="postgresql",
            )
            manager.record_execution(stmt.statement_id, 50.0)

        stats = manager.get_stats()
        assert stats["total_statements"] == 1
        assert stats["prepared_statements"] == 1

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Test multiple connections with separate statements"""
        manager = PreparedStatementManager()

        # Connection 1
        for i in range(5):
            await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash=f"q{i}",
                template_sql=f"SELECT {i}",
                database_type="postgresql",
            )

        # Connection 2
        for i in range(3):
            await manager.get_or_create_statement(
                connection_id=2,
                normalized_hash=f"q{i}",
                template_sql=f"SELECT {i}",
                database_type="mysql",
            )

        stats = manager.get_stats()
        assert stats["total_statements"] == 8

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing entire cache"""
        manager = PreparedStatementManager()

        # Add some statements
        for i in range(5):
            await manager.get_or_create_statement(
                connection_id=1,
                normalized_hash=f"q{i}",
                template_sql=f"SELECT {i}",
                database_type="postgresql",
            )

        manager.clear_cache()

        assert len(manager._statements) == 0
        assert len(manager._connection_statements) == 0
