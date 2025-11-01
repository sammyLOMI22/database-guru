"""Comprehensive tests for SQL Executor"""
import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.exc import SQLAlchemyError, DBAPIError, OperationalError

from src.core.executor import SQLExecutor, QueryTimeout


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def executor():
    """Create a basic SQLExecutor instance"""
    return SQLExecutor(max_rows=10, timeout_seconds=5, allow_write=False)


@pytest.fixture
def executor_with_write():
    """Create SQLExecutor that allows write operations"""
    return SQLExecutor(max_rows=10, timeout_seconds=5, allow_write=True)


@pytest.fixture
def sync_session():
    """Create a synchronous SQLite session for testing"""
    # Use StaticPool to share the connection across threads for :memory: database
    # This is needed because executor runs sync queries in a thread pool
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # Share the same connection across threads
    )

    # Create sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create and populate test table using the session
    session.execute(text("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER,
            created_at TIMESTAMP
        )
    """))
    session.execute(text("""
        INSERT INTO test_table (id, name, value, created_at)
        VALUES
            (1, 'Alice', 100, '2024-01-01 10:00:00'),
            (2, 'Bob', 200, '2024-01-02 11:00:00'),
            (3, 'Charlie', 300, '2024-01-03 12:00:00'),
            (4, 'David', 400, '2024-01-04 13:00:00'),
            (5, 'Eve', 500, '2024-01-05 14:00:00'),
            (6, 'Frank', 600, '2024-01-06 15:00:00'),
            (7, 'Grace', 700, '2024-01-07 16:00:00'),
            (8, 'Henry', 800, '2024-01-08 17:00:00'),
            (9, 'Ivy', 900, '2024-01-09 18:00:00'),
            (10, 'Jack', 1000, '2024-01-10 19:00:00'),
            (11, 'Kate', 1100, '2024-01-11 20:00:00'),
            (12, 'Leo', 1200, '2024-01-12 21:00:00')
    """))
    session.commit()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
async def async_session():
    """Create an async SQLite session for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create test table
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER,
                created_at TIMESTAMP
            )
        """))
        await conn.execute(text("""
            INSERT INTO test_table (id, name, value, created_at)
            VALUES
                (1, 'Alice', 100, '2024-01-01 10:00:00'),
                (2, 'Bob', 200, '2024-01-02 11:00:00'),
                (3, 'Charlie', 300, '2024-01-03 12:00:00'),
                (4, 'David', 400, '2024-01-04 13:00:00'),
                (5, 'Eve', 500, '2024-01-05 14:00:00')
        """))

    from sqlalchemy.ext.asyncio import async_sessionmaker
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    session = AsyncSessionLocal()

    yield session

    await session.close()
    await engine.dispose()


# ============================================================================
# Initialization Tests
# ============================================================================

def test_executor_initialization_defaults():
    """Test executor initializes with default values"""
    executor = SQLExecutor()
    assert executor.max_rows == 1000
    assert executor.timeout_seconds == 30
    assert executor.allow_write == False


def test_executor_initialization_custom():
    """Test executor initializes with custom values"""
    executor = SQLExecutor(max_rows=500, timeout_seconds=60, allow_write=True)
    assert executor.max_rows == 500
    assert executor.timeout_seconds == 60
    assert executor.allow_write == True


# ============================================================================
# Query Execution Tests (Sync Session)
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_sync_session_basic_select(executor, sync_session):
    """Test basic SELECT query with sync session"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table WHERE id <= 3"
    )

    assert result["success"] == True
    assert result["row_count"] == 3
    assert len(result["data"]) == 3
    assert result["columns"] == ["id", "name", "value", "created_at"]
    assert result["truncated"] == False
    assert result["error"] is None
    assert result["execution_time_ms"] > 0

    # Verify data content
    assert result["data"][0]["name"] == "Alice"
    assert result["data"][1]["name"] == "Bob"
    assert result["data"][2]["name"] == "Charlie"


@pytest.mark.asyncio
async def test_execute_query_sync_session_with_params(executor, sync_session):
    """Test parameterized query with sync session"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table WHERE id = :id",
        params={"id": 2}
    )

    assert result["success"] == True
    assert result["row_count"] == 1
    assert result["data"][0]["name"] == "Bob"
    assert result["data"][0]["id"] == 2


@pytest.mark.asyncio
async def test_execute_query_sync_session_truncation(executor, sync_session):
    """Test result truncation with sync session (max_rows=10)"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table"  # 12 rows in total
    )

    assert result["success"] == True
    assert result["row_count"] == 10  # Truncated to max_rows
    assert len(result["data"]) == 10
    assert result["truncated"] == True


@pytest.mark.asyncio
async def test_execute_query_sync_session_no_truncation(executor, sync_session):
    """Test no truncation when results under max_rows"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table WHERE id <= 5"
    )

    assert result["success"] == True
    assert result["row_count"] == 5
    assert result["truncated"] == False


@pytest.mark.asyncio
async def test_execute_query_sync_session_insert(executor_with_write, sync_session):
    """Test INSERT query with sync session"""
    result = await executor_with_write.execute_query(
        sync_session,
        "INSERT INTO test_table (id, name, value) VALUES (99, 'TestUser', 999)"
    )

    assert result["success"] == True
    assert result["row_count"] == 1  # 1 row inserted
    assert result["data"] == []  # No data returned for INSERT
    assert result["columns"] == []
    assert result["truncated"] == False


@pytest.mark.asyncio
async def test_execute_query_sync_session_update(executor_with_write, sync_session):
    """Test UPDATE query with sync session"""
    result = await executor_with_write.execute_query(
        sync_session,
        "UPDATE test_table SET value = 999 WHERE id = 1"
    )

    assert result["success"] == True
    assert result["row_count"] == 1  # 1 row updated
    assert result["data"] == []


@pytest.mark.asyncio
async def test_execute_query_sync_session_delete(executor_with_write, sync_session):
    """Test DELETE query with sync session"""
    result = await executor_with_write.execute_query(
        sync_session,
        "DELETE FROM test_table WHERE id > 10"
    )

    assert result["success"] == True
    assert result["row_count"] == 2  # 2 rows deleted (11, 12)
    assert result["data"] == []


# ============================================================================
# Query Execution Tests (Async Session)
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_async_session_basic_select(executor, async_session):
    """Test basic SELECT query with async session"""
    result = await executor.execute_query(
        async_session,
        "SELECT * FROM test_table WHERE id <= 3"
    )

    assert result["success"] == True
    assert result["row_count"] == 3
    assert len(result["data"]) == 3
    assert result["columns"] == ["id", "name", "value", "created_at"]
    assert result["truncated"] == False
    assert result["error"] is None


@pytest.mark.asyncio
async def test_execute_query_async_session_with_params(executor, async_session):
    """Test parameterized query with async session"""
    result = await executor.execute_query(
        async_session,
        "SELECT * FROM test_table WHERE name = :name",
        params={"name": "Alice"}
    )

    assert result["success"] == True
    assert result["row_count"] == 1
    assert result["data"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_execute_query_async_session_insert(executor_with_write, async_session):
    """Test INSERT query with async session"""
    result = await executor_with_write.execute_query(
        async_session,
        "INSERT INTO test_table (id, name, value) VALUES (99, 'AsyncUser', 999)"
    )

    assert result["success"] == True
    assert result["row_count"] == 1
    assert result["data"] == []


# ============================================================================
# Timeout Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_timeout(executor):
    """Test query timeout handling"""
    # Create a mock async session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock execute to delay longer than timeout
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(10)  # Longer than 5s timeout
        return Mock()

    mock_session.execute = slow_execute

    # Execute with short timeout (5s from executor fixture)
    result = await executor.execute_query(mock_session, "SELECT * FROM test")

    assert result["success"] == False
    assert "timeout" in result["error"].lower()
    assert result["row_count"] == 0
    assert result["data"] == []


@pytest.mark.asyncio
async def test_execute_query_no_timeout_fast_query(executor, async_session):
    """Test that fast queries complete without timeout"""
    result = await executor.execute_query(
        async_session,
        "SELECT 1"
    )

    assert result["success"] == True
    # When success is True, error is None
    assert result.get("error") is None or "timeout" not in result.get("error", "").lower()


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_operational_error(executor):
    """Test handling of OperationalError"""
    # Create a mock session that raises OperationalError
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(side_effect=OperationalError("statement", {}, Exception("Connection error")))

    result = await executor.execute_query(
        mock_session,
        "SELECT * FROM test_table"
    )

    assert result["success"] == False
    assert "error" in result["error"].lower()
    assert result["row_count"] == 0


@pytest.mark.asyncio
async def test_execute_query_syntax_error(executor, sync_session):
    """Test handling of SQL syntax error"""
    result = await executor.execute_query(
        sync_session,
        "SELCT * FORM invalid_syntax"  # Intentional syntax error
    )

    assert result["success"] == False
    assert result["error"] is not None
    assert result["row_count"] == 0


@pytest.mark.asyncio
async def test_execute_query_table_not_found(executor, sync_session):
    """Test handling of table not found error"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM nonexistent_table"
    )

    assert result["success"] == False
    assert "error" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_query_dbapi_error(executor):
    """Test handling of DBAPIError"""
    mock_session = Mock(spec=Session)

    # Create a mock DBAPIError
    mock_error = DBAPIError("statement", {}, Exception("DB API error"))
    mock_session.execute.side_effect = mock_error

    result = await executor.execute_query(
        mock_session,
        "SELECT * FROM test"
    )

    assert result["success"] == False
    assert "error" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_query_unexpected_error(executor):
    """Test handling of unexpected exceptions"""
    mock_session = Mock(spec=Session)
    mock_session.execute.side_effect = ValueError("Unexpected error")

    result = await executor.execute_query(
        mock_session,
        "SELECT * FROM test"
    )

    assert result["success"] == False
    assert "error" in result["error"].lower()


# ============================================================================
# Value Serialization Tests
# ============================================================================

def test_serialize_value_none():
    """Test serialization of None"""
    assert SQLExecutor._serialize_value(None) is None


def test_serialize_value_datetime():
    """Test serialization of datetime"""
    dt = datetime(2024, 1, 15, 10, 30, 45)
    result = SQLExecutor._serialize_value(dt)
    assert result == "2024-01-15T10:30:45"


def test_serialize_value_date():
    """Test serialization of date"""
    d = date(2024, 1, 15)
    result = SQLExecutor._serialize_value(d)
    assert result == "2024-01-15"


def test_serialize_value_decimal():
    """Test serialization of Decimal"""
    dec = Decimal("123.45")
    result = SQLExecutor._serialize_value(dec)
    assert result == 123.45
    assert isinstance(result, float)


def test_serialize_value_float():
    """Test serialization of float"""
    result = SQLExecutor._serialize_value(123.45)
    assert result == 123.45


def test_serialize_value_bytes_utf8():
    """Test serialization of UTF-8 bytes"""
    b = b"Hello World"
    result = SQLExecutor._serialize_value(b)
    assert result == "Hello World"


def test_serialize_value_bytes_non_utf8():
    """Test serialization of non-UTF-8 bytes"""
    b = bytes([0xFF, 0xFE, 0xFD])
    result = SQLExecutor._serialize_value(b)
    assert isinstance(result, str)


def test_serialize_value_string():
    """Test serialization of string"""
    result = SQLExecutor._serialize_value("test string")
    assert result == "test string"


def test_serialize_value_integer():
    """Test serialization of integer"""
    result = SQLExecutor._serialize_value(42)
    # Integers have __float__, so they convert to float
    assert result == 42.0


def test_serialize_value_boolean():
    """Test serialization of boolean"""
    # Booleans have __float__, so they convert to float (1.0, 0.0)
    assert SQLExecutor._serialize_value(True) == 1.0
    assert SQLExecutor._serialize_value(False) == 0.0


def test_serialize_value_with_isoformat():
    """Test serialization of objects with isoformat method"""
    class CustomDate:
        def isoformat(self):
            return "2024-01-15"

    result = SQLExecutor._serialize_value(CustomDate())
    assert result == "2024-01-15"


def test_serialize_value_with_float_conversion():
    """Test serialization of objects convertible to float"""
    class CustomNumber:
        def __float__(self):
            return 42.5

    result = SQLExecutor._serialize_value(CustomNumber())
    assert result == 42.5


def test_serialize_value_exception_handling():
    """Test serialization handles exceptions gracefully"""
    class UnserializableObject:
        def __str__(self):
            raise Exception("Cannot serialize")

    result = SQLExecutor._serialize_value(UnserializableObject())
    assert result is None


# ============================================================================
# Pagination Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_with_pagination_first_page(executor, async_session):
    """Test pagination - first page"""
    result = await executor.execute_with_pagination(
        async_session,
        "SELECT * FROM test_table ORDER BY id",
        page=1,
        page_size=2
    )

    assert result["success"] == True
    assert result["row_count"] == 2
    assert result["data"][0]["id"] == 1
    assert result["data"][1]["id"] == 2
    assert result["pagination"]["page"] == 1
    assert result["pagination"]["page_size"] == 2
    assert result["pagination"]["has_more"] == True


@pytest.mark.asyncio
async def test_execute_with_pagination_second_page(executor, async_session):
    """Test pagination - second page"""
    result = await executor.execute_with_pagination(
        async_session,
        "SELECT * FROM test_table ORDER BY id",
        page=2,
        page_size=2
    )

    assert result["success"] == True
    assert result["row_count"] == 2
    assert result["data"][0]["id"] == 3
    assert result["data"][1]["id"] == 4
    assert result["pagination"]["page"] == 2


@pytest.mark.asyncio
async def test_execute_with_pagination_last_page(executor, async_session):
    """Test pagination - last page with fewer results"""
    result = await executor.execute_with_pagination(
        async_session,
        "SELECT * FROM test_table ORDER BY id",
        page=3,
        page_size=2
    )

    assert result["success"] == True
    assert result["row_count"] == 1  # Only 1 row left (5 total, 2+2+1)
    assert result["data"][0]["id"] == 5
    assert result["pagination"]["has_more"] == False


@pytest.mark.asyncio
async def test_execute_with_pagination_page_size_limit(executor, async_session):
    """Test pagination respects max_rows limit"""
    result = await executor.execute_with_pagination(
        async_session,
        "SELECT * FROM test_table",
        page=1,
        page_size=100  # Exceeds max_rows (10)
    )

    assert result["success"] == True
    # page_size should be capped at executor.max_rows (10)
    assert result["pagination"]["page_size"] == 10


@pytest.mark.asyncio
async def test_execute_with_pagination_invalid_page(executor, async_session):
    """Test pagination handles invalid page numbers"""
    result = await executor.execute_with_pagination(
        async_session,
        "SELECT * FROM test_table ORDER BY id",
        page=0,  # Invalid (should be >= 1)
        page_size=2
    )

    assert result["success"] == True
    assert result["pagination"]["page"] == 1  # Corrected to 1


@pytest.mark.asyncio
async def test_execute_with_pagination_sql_with_semicolon(executor, async_session):
    """Test pagination handles SQL with trailing semicolon"""
    result = await executor.execute_with_pagination(
        async_session,
        "SELECT * FROM test_table ORDER BY id;",
        page=1,
        page_size=2
    )

    assert result["success"] == True
    assert result["row_count"] == 2


# ============================================================================
# Query Safety Validation Tests
# ============================================================================

def test_validate_query_safety_select_allowed(executor):
    """Test that SELECT queries are allowed"""
    is_safe, error = executor.validate_query_safety("SELECT * FROM users")
    assert is_safe == True
    assert error is None


def test_validate_query_safety_insert_blocked(executor):
    """Test that INSERT is blocked when allow_write=False"""
    is_safe, error = executor.validate_query_safety("INSERT INTO users VALUES (1, 'test')")
    assert is_safe == False
    assert "INSERT" in error


def test_validate_query_safety_update_blocked(executor):
    """Test that UPDATE is blocked when allow_write=False"""
    is_safe, error = executor.validate_query_safety("UPDATE users SET name='test'")
    assert is_safe == False
    assert "UPDATE" in error


def test_validate_query_safety_delete_blocked(executor):
    """Test that DELETE is blocked when allow_write=False"""
    is_safe, error = executor.validate_query_safety("DELETE FROM users")
    assert is_safe == False
    assert "DELETE" in error


def test_validate_query_safety_drop_always_blocked(executor_with_write):
    """Test that DROP is always blocked even with allow_write=True"""
    is_safe, error = executor_with_write.validate_query_safety("DROP TABLE users")
    assert is_safe == False
    assert "DROP" in error


def test_validate_query_safety_truncate_always_blocked(executor_with_write):
    """Test that TRUNCATE is always blocked"""
    is_safe, error = executor_with_write.validate_query_safety("TRUNCATE TABLE users")
    assert is_safe == False
    assert "TRUNCATE" in error


def test_validate_query_safety_alter_always_blocked(executor_with_write):
    """Test that ALTER TABLE is always blocked"""
    is_safe, error = executor_with_write.validate_query_safety("ALTER TABLE users ADD COLUMN age INT")
    assert is_safe == False
    assert "ALTER" in error


def test_validate_query_safety_create_always_blocked(executor_with_write):
    """Test that CREATE TABLE is always blocked"""
    is_safe, error = executor_with_write.validate_query_safety("CREATE TABLE test (id INT)")
    assert is_safe == False
    assert "CREATE" in error


def test_validate_query_safety_insert_allowed_with_write(executor_with_write):
    """Test that INSERT is allowed when allow_write=True"""
    is_safe, error = executor_with_write.validate_query_safety("INSERT INTO users VALUES (1, 'test')")
    # Should still be blocked by dangerous operations check
    assert is_safe == True
    assert error is None


def test_validate_query_safety_case_insensitive(executor):
    """Test that validation is case-insensitive"""
    is_safe, error = executor.validate_query_safety("insert into users values (1)")
    assert is_safe == False
    assert "INSERT" in error


def test_validate_query_safety_keyword_at_start(executor):
    """Test detection of keywords at start of query"""
    is_safe, error = executor.validate_query_safety("DELETE FROM users")
    assert is_safe == False


def test_validate_query_safety_keyword_in_middle(executor):
    """Test detection of keywords in middle of query"""
    is_safe, error = executor.validate_query_safety("WITH cte AS (SELECT 1) DELETE FROM users")
    assert is_safe == False


def test_validate_query_safety_multiline_query(executor):
    """Test validation of multiline queries"""
    query = """
    SELECT *
    FROM users
    WHERE active = true
    """
    is_safe, error = executor.validate_query_safety(query)
    assert is_safe == True


def test_validate_query_safety_with_whitespace(executor):
    """Test validation handles extra whitespace"""
    is_safe, error = executor.validate_query_safety("  \n  SELECT * FROM users  \n  ")
    assert is_safe == True


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_workflow_sync_session(executor, sync_session):
    """Test complete workflow with sync session"""
    # 1. Validate query
    is_safe, error = executor.validate_query_safety("SELECT * FROM test_table WHERE value > 500")
    assert is_safe == True

    # 2. Execute query
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table WHERE value > 500"
    )

    # 3. Verify results
    assert result["success"] == True
    assert result["row_count"] > 0
    assert all(row["value"] > 500 for row in result["data"])


@pytest.mark.asyncio
async def test_full_workflow_async_session(executor, async_session):
    """Test complete workflow with async session"""
    # 1. Validate query
    is_safe, error = executor.validate_query_safety("SELECT name, value FROM test_table ORDER BY value DESC")
    assert is_safe == True

    # 2. Execute query
    result = await executor.execute_query(
        async_session,
        "SELECT name, value FROM test_table ORDER BY value DESC"
    )

    # 3. Verify results
    assert result["success"] == True
    assert result["columns"] == ["name", "value"]
    # First row should have highest value
    assert result["data"][0]["value"] == 500


@pytest.mark.asyncio
async def test_execution_time_tracking(executor, sync_session):
    """Test that execution time is properly tracked"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table"
    )

    assert result["success"] == True
    assert result["execution_time_ms"] > 0
    assert isinstance(result["execution_time_ms"], (int, float))


@pytest.mark.asyncio
async def test_empty_result_set(executor, sync_session):
    """Test handling of empty result sets"""
    result = await executor.execute_query(
        sync_session,
        "SELECT * FROM test_table WHERE id = 999"  # No such ID
    )

    assert result["success"] == True
    assert result["row_count"] == 0
    assert result["data"] == []
    assert len(result["columns"]) > 0  # Columns should still be present


@pytest.mark.asyncio
async def test_concurrent_queries(executor, async_session):
    """Test handling of concurrent query executions"""
    queries = [
        "SELECT * FROM test_table WHERE id = 1",
        "SELECT * FROM test_table WHERE id = 2",
        "SELECT * FROM test_table WHERE id = 3",
    ]

    # Execute all queries concurrently
    results = await asyncio.gather(
        *[executor.execute_query(async_session, q) for q in queries]
    )

    # All should succeed
    assert all(r["success"] for r in results)
    assert results[0]["data"][0]["id"] == 1
    assert results[1]["data"][0]["id"] == 2
    assert results[2]["data"][0]["id"] == 3
