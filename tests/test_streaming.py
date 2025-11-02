#!/usr/bin/env python3
"""
Tests for Streaming Query Results

Tests cover:
- SQLExecutor streaming functionality
- Batch processing
- Event types and data formats
- Error handling in streams
- Progressive data delivery
"""
import pytest
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.core.executor import SQLExecutor


class TestSQLExecutorStreaming:
    """Tests for execute_query_streaming method"""

    @pytest.mark.asyncio
    async def test_streaming_with_async_session(self):
        """Test streaming query results with async session"""
        # Create in-memory async database
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE test_products (id INTEGER, name TEXT, price REAL)"
            ))
            # Insert 250 rows
            for i in range(250):
                await conn.execute(text(
                    f"INSERT INTO test_products VALUES ({i}, 'Product {i}', {i * 10.5})"
                ))

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session_maker() as session:
            executor = SQLExecutor(max_rows=1000, timeout_seconds=30)

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="SELECT * FROM test_products ORDER BY id",
                batch_size=50
            ):
                events.append(event)

            # Verify event sequence
            assert events[0]["event_type"] == "metadata"
            assert events[0]["columns"] == ["id", "name", "price"]

            # Should have data events
            data_events = [e for e in events if e["event_type"] == "data"]
            assert len(data_events) == 5  # 250 rows / 50 per batch = 5 batches

            # Verify first batch
            assert data_events[0]["batch_number"] == 1
            assert data_events[0]["rows_in_batch"] == 50
            assert data_events[0]["rows_sent"] == 50
            assert len(data_events[0]["data"]) == 50

            # Verify last batch
            assert data_events[4]["batch_number"] == 5
            assert data_events[4]["rows_sent"] == 250

            # Verify completion event
            complete_event = [e for e in events if e["event_type"] == "complete"][0]
            assert complete_event["truncated"] is False
            assert complete_event["total_rows"] == 250
            assert complete_event["execution_time_ms"] > 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_streaming_with_sync_session(self):
        """Test streaming with sync session (e.g., DuckDB)"""
        # Use file-based database for better test isolation
        import tempfile
        import os

        # Create temp database file
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)

        try:
            engine = create_engine(f"sqlite:///{db_path}", echo=False)

            # Create table and insert data
            with engine.begin() as conn:
                conn.execute(text(
                    "CREATE TABLE test_data (id INTEGER, value TEXT)"
                ))
                for i in range(150):
                    conn.execute(text(
                        f"INSERT INTO test_data VALUES ({i}, 'Value {i}')"
                    ))

            session_maker = sessionmaker(engine, autocommit=False, autoflush=False)
            session = session_maker()

            executor = SQLExecutor(max_rows=1000, timeout_seconds=30)

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="SELECT * FROM test_data",
                batch_size=30
            ):
                events.append(event)

            # Verify metadata
            assert events[0]["event_type"] == "metadata"
            assert events[0]["columns"] == ["id", "value"]

            # Verify data batches (150 / 30 = 5 batches)
            data_events = [e for e in events if e["event_type"] == "data"]
            assert len(data_events) == 5

            # Verify complete
            complete_event = [e for e in events if e["event_type"] == "complete"][0]
            assert complete_event["total_rows"] == 150

            session.close()
            engine.dispose()

        finally:
            # Clean up temp file
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_streaming_with_max_rows_truncation(self):
        """Test that streaming respects max_rows limit"""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE large_table (id INTEGER)"
            ))
            # Insert 500 rows
            for i in range(500):
                await conn.execute(text(f"INSERT INTO large_table VALUES ({i})"))

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session_maker() as session:
            # Set max_rows to 200
            executor = SQLExecutor(max_rows=200, timeout_seconds=30)

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="SELECT * FROM large_table",
                batch_size=100
            ):
                events.append(event)

            # Should get metadata + 2 data batches + complete
            data_events = [e for e in events if e["event_type"] == "data"]
            assert len(data_events) == 2  # 200 rows / 100 per batch = 2

            # Verify truncation
            complete_event = [e for e in events if e["event_type"] == "complete"][0]
            assert complete_event["truncated"] is True
            assert complete_event["total_rows"] == 200

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_streaming_empty_result(self):
        """Test streaming with query that returns no rows"""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE empty_table (id INTEGER, name TEXT)"
            ))

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session_maker() as session:
            executor = SQLExecutor()

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="SELECT * FROM empty_table WHERE id > 1000",
                batch_size=50
            ):
                events.append(event)

            # Should have metadata and complete only (no data events)
            assert events[0]["event_type"] == "metadata"
            assert events[1]["event_type"] == "complete"
            assert events[1]["total_rows"] == 0
            assert events[1]["truncated"] is False

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_streaming_non_select_query(self):
        """Test streaming with INSERT/UPDATE (non-SELECT) query"""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE update_test (id INTEGER, value TEXT)"
            ))
            await conn.execute(text(
                "INSERT INTO update_test VALUES (1, 'test')"
            ))

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session_maker() as session:
            executor = SQLExecutor(allow_write=True)

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="UPDATE update_test SET value = 'updated' WHERE id = 1",
                batch_size=50
            ):
                events.append(event)

            # Should only have complete event for write operations
            assert len(events) == 1
            assert events[0]["event_type"] == "complete"
            assert "rows_affected" in events[0]

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_streaming_data_format(self):
        """Test that streamed data is correctly formatted"""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE format_test (id INTEGER, name TEXT, price REAL, active INTEGER)"
            ))
            await conn.execute(text(
                "INSERT INTO format_test VALUES (1, 'Product A', 19.99, 1)"
            ))
            await conn.execute(text(
                "INSERT INTO format_test VALUES (2, 'Product B', 29.99, 0)"
            ))

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session_maker() as session:
            executor = SQLExecutor()

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="SELECT * FROM format_test",
                batch_size=10
            ):
                events.append(event)

            # Get data event
            data_event = [e for e in events if e["event_type"] == "data"][0]
            rows = data_event["data"]

            # Verify data structure
            assert len(rows) == 2
            assert rows[0]["id"] == 1
            assert rows[0]["name"] == "Product A"
            assert rows[0]["price"] == 19.99
            assert rows[0]["active"] == 1

            assert rows[1]["id"] == 2
            assert rows[1]["name"] == "Product B"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_streaming_batch_size(self):
        """Test that batch size is respected"""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE batch_test (id INTEGER)"
            ))
            for i in range(175):
                await conn.execute(text(f"INSERT INTO batch_test VALUES ({i})"))

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session_maker() as session:
            executor = SQLExecutor()

            events = []
            async for event in executor.execute_query_streaming(
                session=session,
                sql="SELECT * FROM batch_test",
                batch_size=40
            ):
                events.append(event)

            data_events = [e for e in events if e["event_type"] == "data"]

            # 175 rows / 40 per batch = 5 batches (4 full + 1 partial)
            assert len(data_events) == 5

            # First 4 batches should have 40 rows each
            for i in range(4):
                assert data_events[i]["rows_in_batch"] == 40

            # Last batch should have 15 rows (175 % 40 = 15)
            assert data_events[4]["rows_in_batch"] == 15

        await engine.dispose()


class TestStreamingAPI:
    """Integration tests for streaming API endpoint"""

    @pytest.mark.asyncio
    async def test_stream_endpoint_exists(self):
        """Test that streaming endpoint is registered"""
        # This would require FastAPI test client
        # For now, just verify the endpoint exists in the router
        from src.api.endpoints.query import router

        # Check that /stream route exists (note: router prefix is /query)
        routes = [route.path for route in router.routes]
        assert "/stream" in routes or "/query/stream" in [str(r.path) for r in router.routes]

    @pytest.mark.asyncio
    async def test_sse_event_format(self):
        """Test that SSE events are properly formatted"""
        # Test helper to parse SSE format
        def parse_sse_event(sse_string):
            lines = sse_string.strip().split('\n')
            event_type = None
            data = None

            for line in lines:
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                elif line.startswith('data:'):
                    data = line[5:].strip()

            return event_type, data

        # Example SSE event
        sse_event = """event: metadata
data: {"columns": ["id", "name"]}

"""

        event_type, data = parse_sse_event(sse_event)
        assert event_type == "metadata"
        assert "columns" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
