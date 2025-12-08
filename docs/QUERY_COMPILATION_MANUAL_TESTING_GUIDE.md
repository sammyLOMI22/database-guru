# Query Compilation System - Manual Testing Guide

**Purpose**: Comprehensive manual testing procedures to validate the query compilation system functionality, performance, and integration.

**Target Audience**: QA engineers, developers, and DevOps personnel testing the compilation features.

**Estimated Duration**: 45-60 minutes for complete suite

---

## Table of Contents

1. [Setup & Prerequisites](#setup--prerequisites)
2. [Layer 1: SQL Normalization Testing](#layer-1-sql-normalization-testing)
3. [Layer 2: EXPLAIN Plan Caching Testing](#layer-2-explain-plan-caching-testing)
4. [Layer 3: Prepared Statement Management Testing](#layer-3-prepared-statement-management-testing)
5. [API Endpoint Testing](#api-endpoint-testing)
6. [Frontend Dashboard Testing](#frontend-dashboard-testing)
7. [End-to-End Integration Testing](#end-to-end-integration-testing)
8. [Performance Validation](#performance-validation)
9. [Error Handling & Edge Cases](#error-handling--edge-cases)
10. [Troubleshooting](#troubleshooting)

---

## Setup & Prerequisites

### Required Environment

- Backend running: `python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend running: `cd frontend && npm run dev`
- Database connection configured (PostgreSQL or SQLite for testing)
- Ollama running locally for LLM integration

### Test Database Setup

```bash
# Create a test database (PostgreSQL)
createdb test_database_guru

# Or use SQLite
sqlite3 database_guru_test.db

# Create sample tables
psql test_database_guru < scripts/create_sample_db.sql
```

### Verify System Health

1. Check backend health: `curl http://localhost:8000/api/health`
   - Expected: `{"status": "ok"}`
2. Check frontend: `http://localhost:3000`
   - Expected: Application loads successfully
3. Check Ollama: `curl http://localhost:11434/api/tags`
   - Expected: List of available models

---

## Layer 1: SQL Normalization Testing

### Test 1.1: Simple Query Normalization

**Objective**: Verify basic literal extraction to parameters

**Steps**:
1. Start backend server
2. Open Python REPL and test normalization:

```python
from src.core.sql_normalizer import SQLNormalizer

normalizer = SQLNormalizer()

# Test simple query
query = "SELECT * FROM products WHERE id = 123 AND category = 'electronics'"
result = normalizer.normalize(query)

print(f"Original: {query}")
print(f"Normalized: {result.template}")
print(f"Parameters: {result.parameters}")
print(f"Hash: {result.normalization_hash}")
```

**Expected Output**:
```
Original: SELECT * FROM products WHERE id = 123 AND category = 'electronics'
Normalized: SELECT * FROM products WHERE id = :p1 AND category = :p2
Parameters: {'p1': 123, 'p2': 'electronics'}
Hash: a3f8b2c4d5e6f7a8b9c0d1e2f3a4b5c6
```

**Validation Checklist**:
- [ ] Numeric literals converted to parameters
- [ ] String literals converted to parameters
- [ ] Hash is consistent (same query = same hash)
- [ ] Parameters dictionary populated correctly
- [ ] Parameter types tracked correctly

**Pass/Fail Criteria**: All literals converted, hash generated, no semantic changes

---

### Test 1.2: Complex Query Normalization

**Objective**: Verify normalization preserves JOIN logic and aggregations

**Steps**:
1. Test complex query with JOINs:

```python
complex_query = """
    SELECT p.name, COUNT(o.id) as order_count
    FROM products p
    LEFT JOIN orders o ON p.id = o.product_id
    WHERE p.category = 'electronics'
    AND o.created_at > '2024-01-01'
    GROUP BY p.id, p.name
    LIMIT 50
"""

result = normalizer.normalize(complex_query)
print(f"Parameters extracted: {len(result.parameters)}")
print(f"Tables detected: {result.metadata.get('tables', [])}")
print(f"Has aggregation: {result.metadata.get('has_aggregation', False)}")
```

**Expected Output**:
- 3 parameters extracted ('electronics', '2024-01-01', 50 for LIMIT)
- Tables: ['products', 'orders']
- has_aggregation: True

**Validation Checklist**:
- [ ] Multiple literals in WHERE clause converted
- [ ] LIMIT clause preserved (not converted)
- [ ] JOIN conditions preserved
- [ ] Aggregation metadata captured
- [ ] Query structure unchanged

---

### Test 1.3: Parameter Type Tracking

**Objective**: Verify that parameter types are correctly identified

**Steps**:
```python
queries = [
    "SELECT * FROM users WHERE age = 25",  # int
    "SELECT * FROM products WHERE price = 99.99",  # float
    "SELECT * FROM orders WHERE status = 'completed'",  # string
    "SELECT * FROM events WHERE created_at = '2024-01-01'",  # date
    "SELECT * FROM flags WHERE is_active = TRUE",  # boolean
]

for query in queries:
    result = normalizer.normalize(query)
    print(f"{query}")
    print(f"  Types: {result.parameter_types}\n")
```

**Expected Output**:
```
Types for each query showing correct type inference
```

**Validation Checklist**:
- [ ] Integers identified as 'int'
- [ ] Floats identified as 'float'
- [ ] Strings identified as 'str'
- [ ] Dates identified as 'str' (string representation)
- [ ] Booleans identified as 'bool'

---

### Test 1.4: Normalization Consistency

**Objective**: Verify same query always produces same hash (deterministic)

**Steps**:
```python
query = "SELECT * FROM products WHERE id = 123"

hashes = []
for i in range(10):
    result = normalizer.normalize(query)
    hashes.append(result.normalization_hash)

# Check all hashes are identical
assert len(set(hashes)) == 1, "Hashes should be identical"
print(f"✓ All 10 normalizations produced same hash: {hashes[0]}")
```

**Validation Checklist**:
- [ ] Same query produces identical hash every time
- [ ] Hash is deterministic and reproducible

---

### Test 1.5: Edge Cases - IN Clauses

**Objective**: Verify normalization handles IN clauses correctly

**Steps**:
```python
in_query = "SELECT * FROM users WHERE status IN ('active', 'pending', 'verified')"
result = normalizer.normalize(in_query)

print(f"Original: {in_query}")
print(f"Normalized: {result.template}")
print(f"Parameters: {result.parameters}")
```

**Expected**: IN clause values converted to parameters

**Validation Checklist**:
- [ ] IN values extracted as parameters
- [ ] IN clause structure preserved
- [ ] Multiple IN values handled correctly

---

## Layer 2: EXPLAIN Plan Caching Testing

### Test 2.1: Plan Cache Basic Flow

**Objective**: Verify EXPLAIN plan fetching and caching

**Steps**:
1. Setup test database with sample data
2. Test plan cache flow:

```python
from src.cache.plan_cache import PlanCache
import asyncio

async def test_plan_cache():
    cache = PlanCache()

    # Query to EXPLAIN
    normalized_hash = "a3f8b2c4d5e6f7a8b9c0d1e2f3a4b5c6"
    connection_id = 1
    schema_fingerprint = "5f3a8b2c"
    database_type = "postgresql"

    # First call - should miss cache and fetch EXPLAIN
    plan1 = await cache.get_cached_plan(
        normalized_hash=normalized_hash,
        connection_id=connection_id,
        schema_fingerprint=schema_fingerprint,
        database_type=database_type
    )
    print(f"First call: Cache {'HIT' if plan1 else 'MISS'}")

    # If plan was cached, verify it
    if plan1:
        print(f"  Estimated cost: {plan1.estimated_cost}")
        print(f"  Scan type: {plan1.scan_type}")
        print(f"  Uses indexes: {plan1.uses_indexes}")

asyncio.run(test_plan_cache())
```

**Validation Checklist**:
- [ ] First call fetches EXPLAIN plan
- [ ] Plan data extracted correctly
- [ ] Estimated cost captured
- [ ] Scan type identified (Sequential/Index)
- [ ] Indexes detected

---

### Test 2.2: Schema Fingerprinting

**Objective**: Verify schema changes are detected

**Steps**:
1. Create schema fingerprint for test database:

```python
from src.core.schema_inspector import SchemaInspector

async def test_fingerprinting():
    inspector = SchemaInspector(connection_id=1, database_type="postgresql")

    # Get initial fingerprint
    fingerprint1 = inspector.create_schema_fingerprint()
    print(f"Initial fingerprint: {fingerprint1}")

    # Simulate schema change (add column)
    # fingerprint2 = inspector.create_schema_fingerprint()
    # print(f"After change: {fingerprint2}")

    # Fingerprints should differ if schema changed
    # assert fingerprint1 != fingerprint2

asyncio.run(test_fingerprinting())
```

**Validation Checklist**:
- [ ] Fingerprint generated from schema
- [ ] Same schema = same fingerprint
- [ ] Different schema = different fingerprint
- [ ] All tables included
- [ ] Column order matters

---

### Test 2.3: Plan Cache Invalidation

**Objective**: Verify cache invalidation on schema changes

**Steps**:
1. Cache a plan
2. Simulate schema change
3. Verify cache is invalidated:

```python
async def test_invalidation():
    cache = PlanCache()
    connection_id = 1

    # Invalidate all plans for connection
    result = await cache.invalidate_connection(connection_id=connection_id)
    print(f"Invalidated {result['plans_invalidated']} plans")

    # Verify cache is empty
    plan = await cache.get_cached_plan(...)
    assert plan is None, "Cache should be empty after invalidation"
```

**Validation Checklist**:
- [ ] Invalidation clears cache
- [ ] Invalidation count correct
- [ ] Subsequent cache lookups miss

---

### Test 2.4: EXPLAIN Parsing

**Objective**: Verify EXPLAIN output parsing for different databases

**Steps**:
1. For PostgreSQL:

```python
explain_output = [
    "Seq Scan on products  (cost=0.00..35.50 rows=1000 width=32)",
    "  Filter: (category = 'electronics')"
]

# Verify parsing extracts cost, scan type
assert "35.50" in str(explain_output)  # Cost extracted
assert "Seq Scan" in str(explain_output)  # Scan type identified
```

2. For MySQL:

```python
explain_output = [
    "id|select_type|table|type|possible_keys|key|key_len|ref|rows|Extra",
    "1|SIMPLE|products|ALL|category_idx|NULL|NULL|NULL|1000|Using where"
]

# Verify parsing extracts type and keys
assert "ALL" in str(explain_output)  # Scan type
assert "Using where" in str(explain_output)  # Extra info
```

**Validation Checklist**:
- [ ] PostgreSQL EXPLAIN parsed correctly
- [ ] MySQL EXPLAIN parsed correctly
- [ ] Cost/rows estimated
- [ ] Scan type identified
- [ ] Index usage detected

---

## Layer 3: Prepared Statement Management Testing

### Test 3.1: Lazy Preparation

**Objective**: Verify statements only prepared after 2+ executions

**Steps**:
```python
from src.core.prepared_statement_manager import PreparedStatementManager

async def test_lazy_preparation():
    manager = PreparedStatementManager()
    normalized_hash = "a3f8b2c4"
    template_sql = "SELECT * FROM products WHERE id = :p1"

    # First execution - should not prepare
    result1 = await manager.should_prepare(normalized_hash)
    print(f"After 1 execution: Prepared = {result1}")
    assert result1 == False, "Should not prepare after 1 execution"

    # Second execution - should trigger preparation
    result2 = await manager.should_prepare(normalized_hash)
    print(f"After 2 executions: Prepared = {result2}")
    assert result2 == True, "Should prepare after 2 executions"

asyncio.run(test_lazy_preparation())
```

**Validation Checklist**:
- [ ] First execution tracked but not prepared
- [ ] Second execution triggers preparation
- [ ] Execution count incremented
- [ ] Preparation flag set

---

### Test 3.2: LRU Eviction

**Objective**: Verify LRU eviction when max statements reached

**Steps**:
```python
async def test_lru_eviction():
    manager = PreparedStatementManager()
    max_statements = manager.max_statements_per_pool

    # Create statements up to limit
    for i in range(max_statements + 1):
        normalized_hash = f"hash_{i}"
        await manager.prepare_statement(
            normalized_hash=normalized_hash,
            template_sql=f"SELECT * FROM table_{i} WHERE id = :p1",
            database_type="postgresql",
            connection_id=1
        )

    # Should have evicted one
    assert len(manager.statements) == max_statements
    print(f"✓ LRU eviction working: {len(manager.statements)} statements")

asyncio.run(test_lru_eviction())
```

**Validation Checklist**:
- [ ] Statements added until limit reached
- [ ] Additional statement triggers eviction
- [ ] Least recently used evicted
- [ ] Total stays at max

---

### Test 3.3: Background Cleanup

**Objective**: Verify cleanup task removes unused statements

**Steps**:
```python
async def test_cleanup():
    manager = PreparedStatementManager()

    # Create statement with old timestamp
    old_timestamp = datetime.utcnow() - timedelta(minutes=35)
    await manager._add_statement(normalized_hash="old_hash", ...)

    # Run cleanup (removes statements unused for 30+ minutes)
    cleaned = await manager._cleanup_task()
    print(f"Cleaned {cleaned} unused statements")

    # Verify old statement removed
    assert "old_hash" not in manager.statements

asyncio.run(test_cleanup())
```

**Validation Checklist**:
- [ ] Cleanup task runs periodically
- [ ] Old statements identified
- [ ] Unused statements removed
- [ ] Recent statements preserved

---

### Test 3.4: Per-Connection Isolation

**Objective**: Verify statements isolated by connection

**Steps**:
```python
async def test_connection_isolation():
    manager = PreparedStatementManager()
    normalized_hash = "same_hash"

    # Prepare for connection 1
    stmt1 = await manager.prepare_statement(
        normalized_hash=normalized_hash,
        template_sql="...",
        connection_id=1
    )

    # Prepare for connection 2
    stmt2 = await manager.prepare_statement(
        normalized_hash=normalized_hash,
        template_sql="...",
        connection_id=2
    )

    # Should have 2 separate statements (same hash, different connections)
    assert stmt1.statement_id != stmt2.statement_id
    print("✓ Statements isolated by connection")

asyncio.run(test_connection_isolation())
```

**Validation Checklist**:
- [ ] Same query hash in different connections = different prepared statements
- [ ] Statement IDs differ
- [ ] Connection ID tracked
- [ ] No cross-pool sharing

---

## API Endpoint Testing

### Test 4.1: GET /api/compilation/stats

**Objective**: Verify compilation statistics endpoint

**Steps**:
1. Open terminal and test endpoint:

```bash
curl -X GET "http://localhost:8000/api/compilation/stats" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "plan_cache": {
    "total_plans": 10,
    "cached_plans": 8,
    "cache_hits": 24,
    "cache_misses": 6,
    "avg_lookup_ms": 2.5
  },
  "statement_manager": {
    "total_statements": 5,
    "prepared_statements": 3,
    "total_executions": 45,
    "avg_execution_ms": 12.3
  },
  "databases": {
    "postgres_db": {
      "total_queries": 30,
      "prepared_statements": 2,
      "cached_plans": 6
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Validation Checklist**:
- [ ] Endpoint returns 200 OK
- [ ] Statistics object populated
- [ ] Plan cache metrics present
- [ ] Statement manager metrics present
- [ ] Per-database breakdown included
- [ ] Timestamp present

---

### Test 4.2: GET /api/compilation/metrics/{connection_id}

**Objective**: Verify per-connection metrics endpoint

**Steps**:
```bash
curl -X GET "http://localhost:8000/api/compilation/metrics/1?limit=10&offset=0" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "connection": {
    "id": 1,
    "name": "postgres_db",
    "database_type": "postgresql"
  },
  "metrics": [
    {
      "normalized_hash": "a3f8b2c4",
      "template_sql": "SELECT * FROM products WHERE...",
      "total_executions": 15,
      "avg_execution_ms": 12.5,
      "is_prepared": true,
      "is_plan_cached": true,
      "last_executed_at": "2024-01-15T10:20:00Z"
    }
  ],
  "summary": {
    "total_compiled_queries": 8,
    "prepared_statements": 3,
    "cached_plans": 6,
    "avg_speedup_ms": 35.2
  },
  "pagination": {
    "limit": 10,
    "offset": 0,
    "has_more": false
  }
}
```

**Validation Checklist**:
- [ ] Connection details returned
- [ ] Metrics array populated
- [ ] Each metric includes compilation data
- [ ] Summary statistics correct
- [ ] Pagination working

---

### Test 4.3: DELETE /api/compilation/cache/connection/{connection_id}

**Objective**: Verify cache invalidation endpoint

**Steps**:
```bash
# First check stats
curl http://localhost:8000/api/compilation/stats

# Invalidate connection 1
curl -X DELETE "http://localhost:8000/api/compilation/cache/connection/1"

# Check stats again - should be reset
curl http://localhost:8000/api/compilation/stats
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Cache invalidated for connection 1",
  "plans_invalidated": 8,
  "statements_invalidated": 3
}
```

**Validation Checklist**:
- [ ] Returns 200 OK
- [ ] Invalidation counts correct
- [ ] Cache actually cleared (stats reset)
- [ ] Only target connection affected

---

### Test 4.4: GET /api/compilation/invalidation-log

**Objective**: Verify invalidation audit trail endpoint

**Steps**:
```bash
curl -X GET "http://localhost:8000/api/compilation/invalidation-log?connection_id=1&limit=20" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "success": true,
  "entries": [
    {
      "id": 1,
      "connection_id": 1,
      "table_name": "products",
      "invalidation_reason": "schema_change",
      "plans_invalidated": 5,
      "statements_invalidated": 2,
      "invalidated_at": "2024-01-15T09:30:00Z"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

**Validation Checklist**:
- [ ] Returns invalidation entries
- [ ] Each entry includes timestamp and counts
- [ ] Connection filter works
- [ ] Pagination working

---

## Frontend Dashboard Testing

### Test 5.1: Compilation Tab Navigation

**Objective**: Verify Compilation tab accessible and loads

**Steps**:
1. Open http://localhost:3000
2. Look for main navigation tabs
3. Click "⚡ Compilation" tab

**Expected Behavior**:
- [ ] Tab becomes active (red color)
- [ ] CompilationStats component loads
- [ ] No console errors
- [ ] Auto-refresh starts (5-second interval)

---

### Test 5.2: Overview Tab Display

**Objective**: Verify statistics display correctly

**Steps**:
1. Click Compilation tab
2. Look at Overview sub-tab (should be active)
3. Observe displayed statistics

**Expected Display**:
- [ ] "Plan Cache" card showing:
  - Hit rate percentage
  - Cached plans count
- [ ] "Prepared Statements" card showing:
  - Prepared statement count
  - Avg execution time
- [ ] "Speedup" card showing:
  - Average speedup ms
  - Queries compiled count
- [ ] "Databases" card showing:
  - Number of connected databases

**Validation Checklist**:
- [ ] All 4 stat cards displayed
- [ ] Numbers update when data changes
- [ ] Color coding correct (blue, green, purple, orange)
- [ ] Icons display correctly

---

### Test 5.3: Per-Connection Tab

**Objective**: Verify connection metrics display

**Steps**:
1. In Compilation tab, click "🗄️ Per-Connection" sub-tab
2. Observe connection selector dropdown
3. Select a database connection

**Expected Behavior**:
- [ ] Connection dropdown populated with available connections
- [ ] Selecting connection loads metrics
- [ ] Metrics table shows compiled queries for connection
- [ ] Loading spinner appears during fetch
- [ ] Error message if connection unavailable

**Metrics Table Columns**:
- [ ] Normalized Hash
- [ ] Template SQL
- [ ] Executions
- [ ] Avg Time
- [ ] Prepared
- [ ] Cached

---

### Test 5.4: Invalidation Log Tab

**Objective**: Verify audit trail display

**Steps**:
1. Click "📝 Invalidation Log" sub-tab
2. Observe log entries

**Expected Display**:
- [ ] Log entries shown in table format
- [ ] Each entry shows:
  - Table name affected
  - Reason for invalidation
  - Count of invalidated plans/statements
  - Timestamp
- [ ] Filter by connection works
- [ ] Timestamp ordering correct

---

### Test 5.5: Manual Refresh

**Objective**: Verify manual refresh functionality

**Steps**:
1. In Compilation tab, observe refresh button
2. Click "🔄 Refresh" button
3. Observe:
   - Button shows loading spinner
   - Statistics update
   - Last updated timestamp changes

**Validation Checklist**:
- [ ] Button shows loading state
- [ ] Data refreshes on click
- [ ] Spinner disappears when done
- [ ] Timestamp updates to current time

---

### Test 5.6: Auto-Refresh

**Objective**: Verify 5-second auto-refresh

**Steps**:
1. Open Compilation tab
2. Watch last updated timestamp
3. Wait 5-10 seconds
4. Observe timestamp change

**Validation Checklist**:
- [ ] Timestamp updates every 5 seconds
- [ ] Statistics refresh automatically
- [ ] No console errors during auto-refresh
- [ ] Can stop auto-refresh and manually refresh

---

## End-to-End Integration Testing

### Test 6.1: Complete Query Execution with Compilation

**Objective**: Verify full flow from query input to compiled execution

**Steps**:
1. Open http://localhost:3000 (Query Interface tab)
2. Execute a query: `SELECT * FROM products WHERE category = 'electronics' AND price > 100`
3. Observe QueryResults component

**Expected Behavior**:
- [ ] Query executes successfully
- [ ] Compilation badge appears (if compilation enabled)
- [ ] Badge shows "✓ Normalized", "✓ Plan Cached", or "✓ Prepared"
- [ ] Execution time displayed
- [ ] Results shown in table

**In QueryResults Component**:
```
Expected compilation badge:
"Query Compiled" (red theme)
✓ Normalized
✓ Plan Cached
✓ Prepared
Cost: 15.42
Index Scan
```

---

### Test 6.2: Repeated Query Compilation Benefit

**Objective**: Verify compilation benefits for repeated queries

**Steps**:
1. Execute query 1st time: `SELECT * FROM products WHERE id = 1`
   - Note execution time (first run, no cache)
2. Execute same query 2nd time: `SELECT * FROM products WHERE id = 1`
   - Note execution time (should be faster with compilation)
3. Check Compilation stats tab

**Expected Result**:
- [ ] 1st execution: ~80-100ms (no cache benefit)
- [ ] 2nd execution: ~10-20ms (compiled, 5-10x faster)
- [ ] Plan Cache hits: 1
- [ ] Prepared statement marked as used

**Performance Validation**:
```
First execution:  85ms  (normalization + planning + EXPLAIN + execution)
Second execution: 12ms  (normalization + cache lookup + prepared execution)
Speedup: 7x faster
```

---

### Test 6.3: Semantic Variations with Compilation

**Objective**: Verify same normalized query matches different literals

**Steps**:
1. Execute: `SELECT * FROM products WHERE id = 1 AND category = 'electronics'`
2. Execute: `SELECT * FROM products WHERE id = 5 AND category = 'books'`
3. Check compilation stats

**Expected Behavior**:
- [ ] Both queries have same normalized hash (only structure differs)
- [ ] Cache lookup succeeds for second query
- [ ] Plan reused (not re-fetched)
- [ ] Speedup applied to both

**Verification**:
- 2nd query should show plan cache hit in badge
- Performance similar to 2nd execution of same literal

---

## Performance Validation

### Test 7.1: Normalization Overhead Validation

**Objective**: Verify normalization takes <5ms per query

**Steps**:
```bash
# Run benchmark suite
cd /Users/sam/database-guru
python -m pytest tests/benchmarks/test_compilation_performance.py::TestNormalizationPerformance -v
```

**Expected Results**:
```
test_simple_query_normalization_overhead: ~3-4ms ✓
test_complex_query_normalization_overhead: ~5-7ms ✓
test_query_with_many_literals_normalization: ~6-8ms ✓
```

---

### Test 7.2: Cache Lookup Performance Validation

**Objective**: Verify plan cache lookup <10ms

**Steps**:
```bash
python -m pytest tests/benchmarks/test_compilation_performance.py::TestPlanCachePerformance -v
```

**Expected Results**:
```
test_plan_cache_lookup_hit_performance: <5ms ✓
test_plan_cache_lookup_miss_performance: <3ms ✓
test_plan_cache_write_performance: <20ms ✓
```

---

### Test 7.3: End-to-End Speedup Validation

**Objective**: Verify 50%+ speedup for compiled queries

**Steps**:
```bash
python -m pytest tests/benchmarks/test_compilation_performance.py::TestEndToEndCompilationPerformance -v
```

**Expected Results**:
```
test_repeated_query_speedup_first_vs_compiled:
  First execution: ~85ms
  Compiled execution: ~12ms
  Speedup: 86% (7x faster) ✓
```

---

### Test 7.4: Real-World Load Test

**Objective**: Validate compilation benefits under realistic workload

**Steps**:
1. Create test script:

```python
import asyncio
import time
from src.core.sql_normalizer import SQLNormalizer
from src.cache.plan_cache import PlanCache

async def load_test():
    normalizer = SQLNormalizer()
    cache = PlanCache()

    # Simulate 100 unique patterns, 10 executions each
    queries = [
        f"SELECT * FROM table_{i} WHERE id = {j * i}"
        for i in range(100)
        for j in range(10)
    ]

    start = time.time()

    for query in queries:
        normalized = normalizer.normalize(query)
        # Simulate cache lookup
        await cache.get_cached_plan(...)

    elapsed = time.time() - start

    print(f"1000 queries in {elapsed:.2f}s")
    print(f"Avg: {elapsed*1000/1000:.2f}ms per query")

asyncio.run(load_test())
```

2. Run test:
```bash
python test_load.py
```

**Expected Results**:
- [ ] 1000 queries complete in <15 seconds (~15ms each)
- [ ] No memory leaks
- [ ] No CPU spikes
- [ ] Cache hit rate ~90%

---

## Error Handling & Edge Cases

### Test 8.1: Invalid SQL Handling

**Objective**: Verify compilation gracefully handles invalid SQL

**Steps**:
1. In Query Interface, submit invalid SQL:
   ```sql
   SELECT * FROM nonexistent_table WHERE id = 1
   ```
2. Observe error handling

**Expected Behavior**:
- [ ] Error message displayed to user
- [ ] Compilation attempts logged
- [ ] No server crash
- [ ] Error recoverable (can submit new query)

---

### Test 8.2: Missing Schema Handling

**Objective**: Verify handling when schema fingerprint changes

**Steps**:
1. Execute query: `SELECT * FROM products WHERE id = 1`
2. Manually alter table (add column)
3. Execute same query again

**Expected Behavior**:
- [ ] Schema change detected
- [ ] Cache invalidated
- [ ] New EXPLAIN plan fetched
- [ ] Query executes correctly with updated schema

---

### Test 8.3: Cache Overflow Handling

**Objective**: Verify LRU eviction when statement limit reached

**Steps**:
1. Monitor prepared statements count in Compilation stats
2. Execute 150 unique queries (exceeds 100 statement limit)
3. Observe stats tab

**Expected Behavior**:
- [ ] Prepared statement count never exceeds 100
- [ ] Old statements evicted (LRU)
- [ ] Recent statements preserved
- [ ] No errors during eviction

---

### Test 8.4: Connection Failure Handling

**Objective**: Verify graceful degradation when connection unavailable

**Steps**:
1. Execute query successfully
2. Disconnect test database
3. Execute another query
4. Observe behavior

**Expected Behavior**:
- [ ] Query fails with clear error
- [ ] Compilation logs error (doesn't crash)
- [ ] Reconnect and retry works

---

### Test 8.5: Concurrent Query Handling

**Objective**: Verify thread safety under concurrent load

**Steps**:
```bash
# Run concurrent test
python -m pytest tests/test_compilation_endpoints.py -v -n 4
```

**Expected Results**:
- [ ] All tests pass
- [ ] No race conditions
- [ ] Cache access is thread-safe
- [ ] No data corruption

---

## Troubleshooting

### Issue: Compilation stats showing zeros

**Diagnosis**:
1. Check if queries are actually executing
2. Verify `enable_compilation` is True in settings

**Solution**:
```bash
# Check settings
curl http://localhost:8000/api/health | grep compilation

# Restart backend with compilation enabled
ENABLE_QUERY_COMPILATION=true python -m uvicorn src.main:app --reload
```

---

### Issue: Plan cache hits showing 0%

**Diagnosis**:
1. Each unique query pattern needs 2+ executions for cache benefit
2. Test workload may have all unique queries

**Solution**:
```bash
# Execute same query multiple times in quick succession
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"sql": "SELECT * FROM products WHERE id = 1"}'
done
```

---

### Issue: Memory usage growing over time

**Diagnosis**:
1. Prepared statement cleanup task may not be running
2. Cache not respecting TTL

**Solution**:
```bash
# Check cleanup task in logs
tail -100f backend.log | grep cleanup

# Manually trigger cleanup via admin endpoint
curl -X POST http://localhost:8000/api/compilation/cleanup
```

---

### Issue: Normalized queries not matching different literals

**Diagnosis**:
1. Normalization may be too aggressive or not aggressive enough
2. Check parameter type tracking

**Solution**:
```python
# Test normalization directly
from src.core.sql_normalizer import SQLNormalizer

normalizer = SQLNormalizer()

q1 = normalizer.normalize("SELECT * FROM products WHERE id = 1")
q2 = normalizer.normalize("SELECT * FROM products WHERE id = 5")

assert q1.normalization_hash == q2.normalization_hash
print(f"Hash match: {q1.normalization_hash == q2.normalization_hash}")
```

---

### Issue: Frontend dashboard not updating

**Diagnosis**:
1. Auto-refresh may be disabled
2. API endpoint may be failing

**Solution**:
1. Check browser console for errors
2. Verify API endpoint: `curl http://localhost:8000/api/compilation/stats`
3. Check Network tab in DevTools for failed requests

---

## Success Criteria Summary

**✓ All Tests Pass When**:
1. SQL normalization converts literals to parameters consistently
2. Schema fingerprinting detects changes correctly
3. Plan cache hits on repeated queries
4. Prepared statements improve performance
5. All 5 API endpoints return correct responses
6. Frontend dashboard displays live statistics
7. Compilation badge shows in query results
8. Performance targets met (<5ms norm, <10ms cache, >50% speedup)
9. No errors under concurrent load
10. Graceful error handling for edge cases

**Performance Targets**:
- Normalization overhead: <5ms
- Cache lookup: <10ms
- Prepared statement execution: 40-50ms faster than unprepared
- End-to-end speedup: 50-70% for repeated queries

---

## Testing Checklist

Print and use this checklist during manual testing:

```
Layer 1: SQL Normalization
[ ] Test 1.1: Simple query normalization
[ ] Test 1.2: Complex query normalization
[ ] Test 1.3: Parameter type tracking
[ ] Test 1.4: Normalization consistency
[ ] Test 1.5: IN clause handling

Layer 2: EXPLAIN Plan Caching
[ ] Test 2.1: Plan cache basic flow
[ ] Test 2.2: Schema fingerprinting
[ ] Test 2.3: Plan cache invalidation
[ ] Test 2.4: EXPLAIN parsing

Layer 3: Prepared Statements
[ ] Test 3.1: Lazy preparation
[ ] Test 3.2: LRU eviction
[ ] Test 3.3: Background cleanup
[ ] Test 3.4: Per-connection isolation

API Endpoints
[ ] Test 4.1: GET /api/compilation/stats
[ ] Test 4.2: GET /api/compilation/metrics/{id}
[ ] Test 4.3: DELETE /api/compilation/cache/connection/{id}
[ ] Test 4.4: GET /api/compilation/invalidation-log

Frontend Dashboard
[ ] Test 5.1: Compilation tab navigation
[ ] Test 5.2: Overview tab display
[ ] Test 5.3: Per-Connection tab
[ ] Test 5.4: Invalidation Log tab
[ ] Test 5.5: Manual refresh
[ ] Test 5.6: Auto-refresh

End-to-End Integration
[ ] Test 6.1: Complete query execution
[ ] Test 6.2: Repeated query speedup
[ ] Test 6.3: Semantic variations

Performance Validation
[ ] Test 7.1: Normalization overhead <5ms
[ ] Test 7.2: Cache lookup <10ms
[ ] Test 7.3: Speedup >50%
[ ] Test 7.4: Load test (1000 queries)

Error Handling
[ ] Test 8.1: Invalid SQL handling
[ ] Test 8.2: Schema changes
[ ] Test 8.3: Cache overflow
[ ] Test 8.4: Connection failures
[ ] Test 8.5: Concurrent queries

Status: [ ] PASS   [ ] FAIL
Tester: __________________
Date: __________________
```

---

## Appendix: Quick Test Commands

```bash
# Run all compilation tests
python -m pytest tests/test_compilation*.py -v

# Run benchmarks
python -m pytest tests/benchmarks/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Test specific endpoint
curl http://localhost:8000/api/compilation/stats

# Monitor logs
tail -f backend.log | grep -i compilation

# Check system health
curl http://localhost:8000/api/health

# Clear compilation cache
curl -X DELETE http://localhost:8000/api/compilation/cache/connection/1
```

---

**Document Version**: 1.0
**Last Updated**: December 7, 2024
**Status**: Complete - Ready for QA Testing
