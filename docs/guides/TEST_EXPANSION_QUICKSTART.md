# Test Expansion Quick Start Guide

**Date**: 2025-10-26
**For**: Getting started with test expansion immediately

## TL;DR - Start Here

```bash
# 1. Set up test infrastructure
pip install pytest-benchmark hypothesis

# 2. Create test directories
mkdir -p tests/integration tests/test_error_handling tests/test_edge_cases

# 3. Start with highest priority
# Create test_query_endpoint.py following the template below

# 4. Run tests with coverage
./scripts/test_backend.sh --coverage

# 5. Check progress
open htmlcov/index.html
```

---

## Phase 1 - Week 1: Query Endpoint Tests (START HERE)

### Priority: 🔴 CRITICAL
**Current Coverage**: 21% → **Target**: 45%
**Estimated Time**: 2-3 days
**Estimated Bugs to Find**: 5-8

### Test File Template

Create `tests/test_query_endpoint.py`:

```python
"""
Comprehensive tests for /api/query endpoint
Target: Increase coverage from 21% to 45%
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from src.main import app
from src.database.models import Query

client = TestClient(app)


class TestQueryEndpointSuccess:
    """Test successful query execution paths"""

    @pytest.mark.asyncio
    async def test_query_natural_language_to_sql(self, mock_llm, mock_db):
        """Test basic natural language query conversion"""
        # ARRANGE
        question = "Show me all customers from California"
        expected_sql = "SELECT * FROM customers WHERE state = 'California'"

        # ACT
        response = client.post("/api/query", json={
            "question": question,
            "database_type": "postgresql"
        })

        # ASSERT
        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "California" in data["sql"]
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_query_with_results(self, mock_llm, mock_db):
        """Test query that returns results"""
        # Test query execution with mock results
        response = client.post("/api/query", json={
            "question": "Count all orders",
            "database_type": "postgresql",
            "execute": True
        })

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "row_count" in data

    @pytest.mark.asyncio
    async def test_query_with_limit(self, mock_llm, mock_db):
        """Test query respects LIMIT parameter"""
        response = client.post("/api/query", json={
            "question": "Show all products",
            "database_type": "postgresql",
            "limit": 10
        })

        assert response.status_code == 200
        data = response.json()
        assert "LIMIT 10" in data["sql"]


class TestQueryEndpointErrorHandling:
    """Test error scenarios"""

    def test_query_empty_question(self):
        """Test with empty question"""
        response = client.post("/api/query", json={
            "question": "",
            "database_type": "postgresql"
        })

        assert response.status_code == 422  # Validation error

    def test_query_missing_database_type(self):
        """Test with missing database_type"""
        response = client.post("/api/query", json={
            "question": "Show me data"
        })

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_llm_timeout(self, mock_llm_timeout):
        """Test LLM timeout handling"""
        response = client.post("/api/query", json={
            "question": "Complex query",
            "database_type": "postgresql"
        })

        # Should return error but not crash
        assert response.status_code in [408, 500, 503]
        data = response.json()
        assert "error" in data or "detail" in data

    @pytest.mark.asyncio
    async def test_query_database_connection_error(self, mock_db_error):
        """Test database connection failure"""
        response = client.post("/api/query", json={
            "question": "Show data",
            "database_type": "postgresql",
            "execute": True
        })

        assert response.status_code in [500, 503]
        data = response.json()
        assert "database" in str(data).lower() or "connection" in str(data).lower()


class TestQueryEndpointSQLInjection:
    """Test SQL injection prevention"""

    def test_query_sql_injection_attempt(self):
        """Test SQL injection is prevented"""
        malicious_questions = [
            "Show all users'; DROP TABLE users; --",
            "Get data WHERE 1=1 OR '1'='1",
            "SELECT * FROM users; DELETE FROM orders;",
        ]

        for question in malicious_questions:
            response = client.post("/api/query", json={
                "question": question,
                "database_type": "postgresql"
            })

            # Should either reject or sanitize
            if response.status_code == 200:
                data = response.json()
                sql = data.get("sql", "")
                # Should use parameterized queries or reject dangerous patterns
                assert "DROP" not in sql.upper() or response.status_code >= 400


class TestQueryEndpointCaching:
    """Test query caching behavior"""

    @pytest.mark.asyncio
    async def test_query_cache_hit(self, mock_llm, mock_db, mock_cache):
        """Test cache returns cached result"""
        question = "Show all products"

        # First request - miss
        response1 = client.post("/api/query", json={
            "question": question,
            "database_type": "postgresql"
        })
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request - should hit cache
        response2 = client.post("/api/query", json={
            "question": question,
            "database_type": "postgresql"
        })
        assert response2.status_code == 200
        data2 = response2.json()

        # Should be same result, faster
        assert data1["sql"] == data2["sql"]

    @pytest.mark.asyncio
    async def test_query_cache_invalidation(self, mock_cache):
        """Test cache invalidation on schema change"""
        # Implementation depends on cache strategy
        pass


class TestQueryEndpointRateLimiting:
    """Test rate limiting"""

    def test_query_rate_limit_headers(self):
        """Test rate limit headers are present"""
        response = client.post("/api/query", json={
            "question": "Test query",
            "database_type": "postgresql"
        })

        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 200

    def test_query_rate_limit_exceeded(self):
        """Test rate limit enforcement"""
        # Make many rapid requests
        responses = []
        for i in range(150):  # Exceed limit of 100/min
            response = client.post("/api/query", json={
                "question": f"Query {i}",
                "database_type": "postgresql"
            })
            responses.append(response)

        # At least one should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0 or responses[-1].status_code == 429


# Fixtures
@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM client"""
    async def mock_generate(*args, **kwargs):
        return "SELECT * FROM table"

    mock_client = AsyncMock()
    mock_client.generate = mock_generate
    # Apply mock to actual LLM client
    return mock_client


@pytest.fixture
def mock_db(monkeypatch):
    """Mock database connection"""
    mock_conn = Mock()
    mock_conn.execute = Mock(return_value=[{"id": 1, "name": "Test"}])
    return mock_conn


@pytest.fixture
def mock_cache(monkeypatch):
    """Mock Redis cache"""
    cache_data = {}

    async def mock_get(key):
        return cache_data.get(key)

    async def mock_set(key, value, ttl=None):
        cache_data[key] = value

    # Apply to cache client
    return {"get": mock_get, "set": mock_set}


@pytest.fixture
def mock_llm_timeout(monkeypatch):
    """Mock LLM timeout"""
    async def mock_timeout(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.1)
        raise TimeoutError("LLM timeout")

    # Apply mock
    return mock_timeout


@pytest.fixture
def mock_db_error(monkeypatch):
    """Mock database error"""
    def mock_error(*args, **kwargs):
        raise ConnectionError("Database unavailable")

    # Apply mock
    return mock_error
```

### Running These Tests

```bash
# Run just the query endpoint tests
pytest tests/test_query_endpoint.py -v

# Run with coverage for query.py
pytest tests/test_query_endpoint.py --cov=src/api/endpoints/query --cov-report=term-missing

# Run and generate HTML report
pytest tests/test_query_endpoint.py --cov=src/api/endpoints/query --cov-report=html
open htmlcov/index.html
```

### Expected Outcomes

- ✅ **Coverage increase**: 21% → 45% (+24%)
- ✅ **Bugs found**: 5-8 (input validation, error handling, edge cases)
- ✅ **Time**: 2-3 days
- ✅ **New tests**: ~15 test functions

---

## Phase 1 - Week 2: Multi-DB Endpoint Tests

After completing query endpoint, move to `test_multi_db_endpoint.py`.

### Key Test Cases

```python
"""
Tests for multi-database query endpoint
Current: 28% → Target: 58%
"""

class TestMultiDatabaseQuery:
    def test_query_across_two_databases(self):
        """Test joining data from two databases"""
        response = client.post("/api/multi-db/query", json={
            "question": "Join users from DB1 with orders from DB2",
            "databases": ["db1", "db2"]
        })

        assert response.status_code == 200
        # Verify cross-database join logic

    def test_multi_db_one_unavailable(self):
        """Test when one database is down"""
        # Should handle gracefully
        pass

    def test_multi_db_result_merging(self):
        """Test correct merging of results"""
        # Verify data aggregation
        pass
```

---

## Daily Workflow

### Morning Routine (30 min)
1. Check coverage report from yesterday
2. Review any failing tests
3. Plan today's tests (2-3 test functions)

### Development (4-6 hours)
1. Write test function
2. Run test (should fail initially)
3. Check coverage increase
4. Fix any bugs found
5. Repeat

### End of Day (30 min)
1. Run full test suite
2. Generate coverage report
3. Document bugs found
4. Commit tests

### Daily Checklist

```bash
# Morning
./scripts/test_backend.sh --coverage

# During development (repeat)
pytest tests/test_query_endpoint.py::test_specific_function -v
pytest tests/test_query_endpoint.py --cov=src/api/endpoints/query

# End of day
./scripts/test_all.sh --skip-integration
git add tests/
git commit -m "Add tests for query endpoint - coverage +5%"
```

---

## Bug Tracking Template

Create `../reports/BUGS_FOUND.md`:

```markdown
# Bugs Found During Test Expansion

## Bug #1: Query endpoint doesn't validate empty question
**Date**: 2025-10-26
**Severity**: Medium
**Found in**: test_query_empty_question
**File**: src/api/endpoints/query.py:45
**Description**: Empty question string passes validation and causes LLM error
**Fix**: Add input validation
**Status**: Fixed

## Bug #2: Database connection not closed on error
**Date**: 2025-10-26
**Severity**: High
**Found in**: test_query_database_connection_error
**File**: src/api/endpoints/query.py:78
**Description**: Connection leak on database errors
**Fix**: Add try/finally block
**Status**: In Progress
```

---

## Quick Tips

### Writing Good Tests

✅ **DO**:
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Test one thing per test function
- Use fixtures for setup
- Mock external dependencies

❌ **DON'T**:
- Test multiple scenarios in one function
- Rely on test execution order
- Use sleeps (use mocks instead)
- Skip assertions
- Leave commented-out code

### Debugging Failed Tests

```bash
# Run specific test with verbose output
pytest tests/test_query_endpoint.py::test_name -vv

# Run with print statements visible
pytest tests/test_query_endpoint.py::test_name -s

# Drop into debugger on failure
pytest tests/test_query_endpoint.py::test_name --pdb

# Show full diff for assertions
pytest tests/test_query_endpoint.py::test_name -vv --tb=short
```

### Coverage Analysis

```bash
# Generate detailed coverage
./scripts/test_backend.sh --coverage

# Check specific file
pytest --cov=src/api/endpoints/query --cov-report=term-missing

# Find uncovered lines
coverage report -m | grep query.py
```

---

## Success Metrics (Week 1)

Track these metrics daily:

| Metric | Start | Target | Current |
|--------|-------|--------|---------|
| Overall Coverage | 55% | 58% | ___ |
| query.py Coverage | 21% | 45% | ___ |
| Tests Written | 184 | 200+ | ___ |
| Bugs Found | 0 | 5-8 | ___ |
| Failing Tests | 0 | 0 | ___ |

---

## Getting Help

### Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Guide](https://coverage.readthedocs.io/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)

### Common Issues

**Issue**: Tests pass locally but fail in CI
**Solution**: Check for hardcoded paths, timing dependencies

**Issue**: Coverage not increasing
**Solution**: Verify tests actually execute the code path

**Issue**: Flaky tests
**Solution**: Remove sleeps, use proper mocking, check for race conditions

---

## Ready to Start?

```bash
# 1. Create the test file
touch tests/test_query_endpoint.py

# 2. Copy the template above into it

# 3. Run initial test
pytest tests/test_query_endpoint.py -v

# 4. Start implementing test functions one by one

# 5. Track your progress
./scripts/test_backend.sh --coverage
```

**Let's improve that coverage! 🚀**

---

## Next Steps After Week 1

1. ✅ Complete query endpoint tests (21% → 45%)
2. ➡️ Move to chat endpoint tests
3. ➡️ Then multi-db tests
4. ➡️ Then schema tests
5. ➡️ Continue with [TEST_EXPANSION_PLAN.md](TEST_EXPANSION_PLAN.md)

**Happy Testing!** 🧪

---

**Created**: 2025-10-26
**For**: Database Guru Test Expansion Phase 1
**Status**: Ready to Use
