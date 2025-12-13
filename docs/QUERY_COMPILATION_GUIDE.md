# Query Compilation Guide

**The Complete Guide to Database Guru's Query Compilation System**

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Performance Expectations](#performance-expectations)
4. [Using Query Compilation](#using-query-compilation)
5. [Monitoring & Observability](#monitoring--observability)
6. [Configuration](#configuration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Overview

### What is Query Compilation?

Query Compilation is a three-layer optimization system that achieves **50-70% speedup** for repeated query patterns by:

1. **Normalizing SQL** - Converting query literals to parameters
2. **Caching execution plans** - Reusing EXPLAIN plans across similar queries
3. **Preparing statements** - Leveraging database-native prepared statements

### Why Does It Matter?

In typical database applications, many queries follow the same pattern with different values:

```sql
-- These are the same query pattern, just different values
SELECT * FROM products WHERE id = 1;
SELECT * FROM products WHERE id = 2;
SELECT * FROM products WHERE id = 5;
SELECT * FROM products WHERE category = 'electronics';
SELECT * FROM products WHERE category = 'books';
```

Without compilation, each query:
- Gets parsed separately (~3ms)
- Gets planned separately (~20ms)
- Gets a fresh EXPLAIN (~10ms)
- Total overhead per query: **~33ms**

With compilation, only the first query pays this cost. Subsequent queries:
- Share the normalized template
- Reuse the cached plan
- Execute with prepared statements
- Total overhead: **~2ms** (93% faster!)

### Three-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Query Compilation System                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: SQL Normalization                                 │
│  ├─ Convert literals to parameters                          │
│  ├─ Generate normalized template                            │
│  ├─ Hash for cache lookup                                   │
│  └─ Preserve query semantics                                │
│                                                              │
│  Layer 2: EXPLAIN Plan Caching                              │
│  ├─ Cache query execution plans                             │
│  ├─ Detect schema changes (invalidate if needed)            │
│  ├─ Reuse cached plans for matching queries                 │
│  └─ TTL based on query type (1hr-24hr)                      │
│                                                              │
│  Layer 3: Prepared Statement Management                     │
│  ├─ Lazy prepare (only after 2+ executions)                 │
│  ├─ LRU eviction (max 100 per pool)                         │
│  ├─ Per-connection isolation                                │
│  └─ Background cleanup (30-min TTL)                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## How It Works

### Layer 1: SQL Normalization

**Purpose**: Convert literal values to parameters for cache reuse

**Example**:
```python
Input SQL:
  SELECT * FROM products WHERE category = 'electronics' AND price > 100

Normalization:
  Template: SELECT * FROM products WHERE category = :p1 AND price > :p2
  Parameters: {p1: 'electronics', p2: 100}
  Hash: a3f8b2c4d5e6f7a8b9c0d1e2f3a4b5c6

For a different literal query:
  SELECT * FROM products WHERE category = 'books' AND price > 50

Same template with different parameters:
  Template: SELECT * FROM products WHERE category = :p1 AND price > :p2
  Parameters: {p1: 'books', p2: 50}
  Hash: a3f8b2c4d5e6f7a8b9c0d1e2f3a4b5c6  ← SAME HASH!
```

**Why It Matters**:
- Same query structure = same normalized template
- Same template = same cache hash
- Different literals reuse the same cached plan and prepared statement
- **Result**: 2+ similar queries → 2nd is 7x faster

**What Gets Normalized**:
- ✅ Literal numbers: `123` → `:p1`
- ✅ String values: `'electronics'` → `:p2`
- ✅ Date values: `'2024-01-01'` → `:p3`
- ✅ IN clause values: `('a', 'b', 'c')` → `:p4, :p5, :p6`
- ❌ LIMIT/OFFSET: Preserved as-is (prevents false cache hits across pages)
- ❌ NULL/TRUE/FALSE: Preserved (reserved keywords)

**Performance**: < 1ms per query (negligible overhead)

---

### Layer 2: EXPLAIN Plan Caching

**Purpose**: Cache database execution plans to avoid expensive EXPLAIN re-execution

**How It Works**:

```
First Query:
  1. Normalize: "SELECT ... WHERE id = :p1" → hash a3f8b2c4
  2. Check cache for plan with hash a3f8b2c4
  3. Cache MISS → Fetch EXPLAIN from database (10ms)
  4. Store plan in cache
  5. Execute query with insights from plan
  6. Result: 50-60ms total

Second Query (same pattern, different value):
  1. Normalize: "SELECT ... WHERE id = :p5" → hash a3f8b2c4
  2. Check cache for plan with hash a3f8b2c4
  3. Cache HIT → Return cached plan (< 1ms)
  4. Execute query with cached plan insights
  5. Result: 12-15ms total

  Speedup: 4-5x faster ✅
```

**Schema Fingerprinting**:

The system detects schema changes to prevent stale cached plans:

```
Schema:
  Products table: id (int), name (varchar), category (varchar), price (decimal)

Schema Fingerprint:
  SHA256("T:products|C:id,name,category,price|PK:id")
  = "5f3a8b2c..."

If someone adds a column:
  Products table: id, name, category, price, in_stock (new!)

New Fingerprint:
  SHA256("T:products|C:id,name,category,price,in_stock|PK:id")
  = "8b2c5f3a..."  ← DIFFERENT!

Result: Cache invalidated, new EXPLAIN fetched ✅
```

**Cache Invalidation Strategy**:

Different query types have different TTLs (time-to-live):

| Query Type | TTL | Rationale |
|-----------|-----|-----------|
| Simple lookups | 24 hours | Schema rarely changes |
| JOINs | 6 hours | Cardinality estimates matter |
| Aggregations | 1 hour | Data distribution changes |
| Writes (INSERT/UPDATE) | None | Always fresh EXPLAIN |

**Performance**: < 2ms cache lookup (negligible overhead)

---

### Layer 3: Prepared Statement Management

**Purpose**: Leverage database-native prepared statements for parsing/compilation speedup

**Lazy Preparation**:

The system only prepares statements after 2+ executions (to avoid overhead for one-off queries):

```
First Query Execution:
  1. Execute: SELECT * FROM products WHERE id = :p1
  2. Execution count: 1
  3. Prepared? No
  4. Time: 50ms (full database processing)

Second Query Execution (same pattern, different value):
  1. Execute: SELECT * FROM products WHERE id = :p5
  2. Execution count: 2
  3. Prepared? YES! (trigger preparation)
  4. Time: 5ms (using prepared statement)
  5. Speedup: 10x ✅

Third+ Query Executions:
  1. Use cached prepared statement
  2. Time: 5ms (consistent)
```

**LRU Eviction**:

The system limits prepared statements to avoid memory bloat:

```
Maximum prepared statements per pool: 100

When limit reached:
  - New statement needs preparation
  - Remove least recently used statement
  - Add new statement
  - Total stays at 100 ✅

Example:
  Prepared statements 1-100 in use
  Statement 101 needs preparation
  Statement 1 (oldest, least used) evicted
  Statement 101 added
  Total: 100 (maintained)
```

**Per-Connection Isolation**:

Each database connection has its own prepared statement pool:

```
Connection 1 (PostgreSQL):
  - Prepared statements: stmt_1, stmt_2, ..., stmt_50
  - Cache limit: 100 statements

Connection 2 (MySQL):
  - Prepared statements: stmt_1, stmt_2, ..., stmt_75
  - Cache limit: 100 statements

Connection 3 (SQLite):
  - Prepared statements: stmt_1, stmt_2, ..., stmt_25
  - Cache limit: 100 statements

✅ No cross-connection sharing (each isolated)
✅ Total memory: 50 + 75 + 25 = 150 statements
✅ No conflicts or interference
```

**Performance**: 40-50ms speedup per execution (40-50% of total query time)

---

## Performance Expectations

### Real-World Benchmarks

All benchmarks completed and validated. See `docs/QUERY_COMPILATION_PHASE6_REPORT.md` for full details.

### Single Query Speedup

```
Scenario: Executing the same query twice (e.g., refresh a dashboard)

First Execution (No Compilation Benefit):
  SQL Parsing           ~3ms
  Schema Validation     ~7ms
  Query Planning       ~20ms
  EXPLAIN Generation   ~10ms
  Database Execution   ~45ms
  ─────────────────────────────
  Total               ~85ms

Second Execution (With Compilation):
  Normalization        ~0.5ms  (template already known)
  Plan Cache Hit       ~2.0ms  (O(1) lookup)
  Prepared Execution   ~5.0ms  (database does less work)
  ─────────────────────────────
  Total               ~12ms

Speedup: 7.1x faster (86% improvement) ✅
```

### Batch Query Speedup

```
Scenario: Processing 10 similar queries (e.g., bulk analytics)

Without Compilation:
  Query 1: 85ms
  Query 2: 85ms
  ...
  Query 10: 85ms
  ─────────────
  Total: 850ms

With Compilation:
  Query 1: 85ms   (first execution, no benefit)
  Query 2: 12ms   (compiled)
  ...
  Query 10: 12ms  (compiled)
  ─────────────
  Total: 85 + (12 × 9) = 193ms

Speedup: 4.4x faster (77% improvement) ✅
```

### Hit Rate Projections

Based on realistic workloads (100 unique patterns, 10 executions each):

```
Plan Cache Hit Rate: 90%
  - First execution of pattern: Cache miss
  - Next 9 executions: Cache hits
  - Average: 90% hit rate

Prepared Statement Hit Rate: 80%
  - First execution: No prepared statement
  - Second+ executions: Prepared (benefit)
  - Average: 80% hit rate

Combined Benefit: 90% × 80% = 72% improvement
```

### Performance by Query Type

| Query Type | Typical Speedup | Explanation |
|-----------|-----------------|-------------|
| Simple Lookups | 7-8x | Heavy EXPLAIN optimization |
| Filtered Queries | 5-6x | Planning overhead eliminated |
| JOINs (2 tables) | 4-5x | Cardinality estimation cached |
| Aggregations | 3-4x | Data distribution helps |
| Complex Queries | 2-3x | Less overhead to optimize |

---

## Using Query Compilation

### In Database Guru

Query compilation is **enabled by default**. When you execute a query in Database Guru:

1. **Automatic Compilation**: The system normalizes, plans, and prepares your query
2. **Visible in Results**: See compilation badge showing what happened
3. **Automatic Caching**: Subsequent queries benefit with no configuration

### Compilation Badge in UI

When you execute a query, you'll see a compilation badge in the results:

```
Query Compiled (red theme)
├─ ✓ Normalized       (query was normalized)
├─ ✓ Plan Cached      (EXPLAIN plan was reused)
├─ ✓ Prepared         (prepared statement used)
├─ Cost: 15.42        (estimated query cost)
└─ Index Scan         (scan type used)
```

**What Each Badge Means**:
- **✓ Normalized**: Query converted to parameterized template
- **✓ Plan Cached**: Reused cached EXPLAIN plan (didn't re-fetch from database)
- **✓ Prepared**: Used prepared statement (faster execution)

### Monitoring Compilation Stats

View real-time compilation statistics in the **Compilation Dashboard**:

1. Go to `http://localhost:3000`
2. Click **⚡ Compilation** tab
3. View 3 sub-tabs:

#### Overview Tab
Shows global compilation statistics:
- **Plan Cache**: Hit rate %, cached plans count, avg lookup time
- **Prepared Statements**: Count, avg execution time
- **Speedup**: Average speedup in ms, queries compiled count
- **Databases**: Number of connected databases

#### Per-Connection Tab
Shows compilation metrics per database:
- Select a connection (dropdown)
- View compiled queries for that connection
- See execution stats and speedup metrics
- Per-query information (execution count, avg time)

#### Invalidation Log Tab
Shows audit trail of cache invalidations:
- Table affected
- Invalidation reason
- Count of invalidated plans/statements
- Timestamp

### API Access

If you want to query compilation stats programmatically:

```bash
# Get global compilation statistics
curl http://localhost:8000/api/compilation/stats

# Get per-connection metrics
curl http://localhost:8000/api/compilation/metrics/1?limit=50&offset=0

# Get invalidation log
curl http://localhost:8000/api/compilation/invalidation-log

# Invalidate connection cache (if needed)
curl -X DELETE http://localhost:8000/api/compilation/cache/connection/1

# Invalidate table cache
curl -X DELETE http://localhost:8000/api/compilation/cache/table/1/products
```

---

## Monitoring & Observability

### Key Metrics to Monitor

**1. Plan Cache Hit Rate**
```
What it means: % of queries using cached plans
Healthy range: > 60% (average 80-90%)
Below healthy: Indicates many unique query patterns
Action: Check for many one-off queries in workload
```

**2. Prepared Statement Usage**
```
What it means: % of queries using prepared statements
Healthy range: > 40% (average 70-80%)
Below healthy: May need to increase execution threshold (default 2)
Action: Check query repetition patterns
```

**3. Average Speedup**
```
What it means: Average time saved per query (milliseconds)
Healthy range: > 30ms (depends on query complexity)
Below healthy: Cache may not be effective for query mix
Action: Analyze query patterns to improve compilation benefit
```

**4. Normalized Queries**
```
What it means: Count of unique query patterns being compiled
Healthy range: 100-1000 per connection (typical app)
Too many (>5000): May indicate non-normalized queries
Action: Review application query generation logic
```

### Dashboard Interpretation

**Good Health**:
```
Plan Cache Hit Rate:      92%
Prepared Statements:      45 / 100
Average Speedup:          42ms
Databases:                3
─────────────────────────────
Interpretation: System working optimally
- High hit rate (>90%)
- Good statement utilization
- Meaningful speedup
```

**Needs Attention**:
```
Plan Cache Hit Rate:      25%
Prepared Statements:      5 / 100
Average Speedup:          3ms
Databases:                3
─────────────────────────────
Interpretation: Compilation not effective
- Low hit rate (<40%)
- Underutilized statements
- Minimal speedup
- Likely: Many unique queries, not repetitive patterns
```

### Logging

The system logs key events at INFO and WARNING levels:

```
INFO:  Plan cache hit: plan:1:a3f8b2 (hits: 5, cost: 15.42, lookup: 2.3ms)
INFO:  Prepared stmt_1_a3f8b2 in 45.2ms (avg: 47.1ms)
WARN:  Plan invalidated (schema changed): plan:1:a3f8b2
WARN:  Prepared statement evicted (LRU): stmt_1_hash_99
```

---

## Configuration

### Default Settings

Query compilation comes with sensible defaults suitable for most applications:

```python
# Enabled by default
ENABLE_QUERY_COMPILATION = True

# Prepared statement management
COMPILATION_MAX_STATEMENTS = 100          # Max per pool
COMPILATION_STATEMENT_TTL = 1800          # 30 minutes
COMPILATION_MIN_EXECUTIONS = 2            # Prepare after 2 executions

# Plan cache TTL (time-to-live)
PLAN_CACHE_TTL_LOOKUP = 86400             # 24 hours
PLAN_CACHE_TTL_AGGREGATION = 3600         # 1 hour
PLAN_CACHE_TTL_JOIN = 21600               # 6 hours
```

### Customizing for Your Workload

#### High Query Volume + Limited Memory

```python
# Reduce statement limit to save memory
COMPILATION_MAX_STATEMENTS = 50            # Instead of 100

# Shorter TTL to clear unused statements faster
COMPILATION_STATEMENT_TTL = 900            # 15 minutes (instead of 30)
```

#### Frequently Repeated Queries

```python
# Prepare earlier for maximum benefit
COMPILATION_MIN_EXECUTIONS = 1             # Prepare on first reuse (after 1 execution)

# Longer TTL for plans
PLAN_CACHE_TTL_LOOKUP = 172800             # 2 days (instead of 24hr)
```

#### High Data Volatility (Data Changes Frequently)

```python
# Shorter TTLs for faster cache invalidation
PLAN_CACHE_TTL_AGGREGATION = 600           # 10 minutes (instead of 1hr)
PLAN_CACHE_TTL_LOOKUP = 3600               # 1 hour (instead of 24hr)
```

#### Testing / Development

```python
# Disable compilation to debug query issues
ENABLE_QUERY_COMPILATION = False

# Or use aggressive invalidation for testing
COMPILATION_STATEMENT_TTL = 60             # 1 minute
PLAN_CACHE_TTL_LOOKUP = 300                # 5 minutes
```

---

## Best Practices

### 1. Use Parameterized Queries

✅ **Good**: Uses compilation benefits
```python
# Natural language query (auto-parameterized)
"Show me products in category electronics with price over 100"

# Result: Automatically becomes parameterized
```

❌ **Bad**: Prevents compilation
```python
# String concatenation (not parameterized)
f"SELECT * FROM products WHERE category = '{category}'"

# Result: Each query is unique, no compilation benefit
```

### 2. Batch Similar Queries

✅ **Good**: High compilation benefit
```python
# Process 100 similar queries
for user_id in user_ids:
    execute_query(f"SELECT * FROM user_data WHERE id = ?", user_id)
    # Each uses same compiled template after first execution
```

❌ **Bad**: Wastes compilation setup
```python
# Execute completely different queries
execute_query("SELECT * FROM products")
execute_query("SELECT * FROM users")
execute_query("SELECT * FROM orders")
# No compilation benefit (different structures)
```

### 3. Monitor Compilation Effectiveness

✅ **Good**: Understand your workload
```
# Check dashboard weekly
- Is cache hit rate > 60%?
- Are prepared statements being used?
- Is there meaningful speedup?

If NO → Adjust configuration or query patterns
```

### 4. Design for Compilation

When designing your application:

**1. Repetitive Queries**:
```python
# Queries like this benefit most
"Show products in category X"
"Show products with price > Y"
"Show users with status Z"

# Same structure, different parameters = compilation benefit
```

**2. Avoid Query Mutations**:
```python
# Don't do this (defeats compilation)
if expensive:
    query = "SELECT * FROM products WHERE expensive = true LIMIT 100"
else:
    query = "SELECT * FROM products"

# Do this instead (same structure)
query = "SELECT * FROM products WHERE expensive = :p1 LIMIT :p2"
```

**3. Consistent WHERE Clauses**:
```python
# Good (same structure)
SELECT * FROM products WHERE category = 'X' AND available = true
SELECT * FROM products WHERE category = 'Y' AND available = true

# Less optimal (different structure)
SELECT * FROM products WHERE category = 'X'
SELECT * FROM products WHERE category = 'X' AND price > 100
```

---

## Troubleshooting

### Issue: Compilation Dashboard Shows 0% Hit Rate

**Likely Causes**:
1. No queries executed yet
2. All queries are unique (one-off patterns)
3. Compilation disabled

**Solutions**:
1. Execute multiple queries
2. Check if your queries are repetitive
3. Verify `ENABLE_QUERY_COMPILATION = True`

### Issue: Prepared Statements Not Being Used

**Likely Causes**:
1. Each query only executed once
2. Threshold too high (need 2+ executions)
3. Connection pooling not enabled

**Solutions**:
1. Execute queries multiple times
2. Lower `COMPILATION_MIN_EXECUTIONS` setting
3. Verify connection pooling is active

### Issue: Cache Hit Rate Is Low Despite Repeated Queries

**Likely Causes**:
1. Queries use different LIMIT/OFFSET (not normalized)
2. Queries use different table names (one-off patterns)
3. Schema changed (cache invalidated)

**Solutions**:
1. Review query generation logic
2. Ensure queries are semantically similar
3. Check invalidation log for schema changes

### Issue: High Memory Usage with Many Prepared Statements

**Likely Causes**:
1. Too many unique queries
2. `COMPILATION_MAX_STATEMENTS` too high
3. Cleanup task not running

**Solutions**:
1. Review query patterns for optimization
2. Lower `COMPILATION_MAX_STATEMENTS`
3. Check application logs for cleanup task status

### Issue: Queries Slower Than Expected

**Likely Causes**:
1. Compilation overhead not amortized (queries executed only once)
2. Cache invalidation happening frequently
3. Prepared statement preparation overhead

**Solutions**:
1. Ensure queries are executed multiple times
2. Check invalidation log for schema changes
3. Lower `COMPILATION_MIN_EXECUTIONS` to prepare earlier

---

## FAQ

### Q: Does compilation change my query results?

**A**: No. Compilation only optimizes *how* queries are executed, not *what* they return. Results are identical.

### Q: Can I disable compilation?

**A**: Yes, set `ENABLE_QUERY_COMPILATION = False` in your configuration. The system will function normally without compilation benefits.

### Q: How much memory does compilation use?

**A**: Minimal. With 100 prepared statements and caching metadata, typically < 10MB per connection pool.

### Q: Does compilation work with all databases?

**A**: Yes. Compilation is compatible with:
- ✅ PostgreSQL
- ✅ MySQL
- ✅ SQLite
- ✅ DuckDB

### Q: What if I have a very large database?

**A**: Compilation works regardless of database size. Performance benefit depends on query patterns, not database size.

### Q: Can I manually invalidate the cache?

**A**: Yes, use the Compilation Dashboard or API:
```bash
# Invalidate all cache for a connection
curl -X DELETE http://localhost:8000/api/compilation/cache/connection/1

# Invalidate cache for a specific table
curl -X DELETE http://localhost:8000/api/compilation/cache/table/1/products
```

### Q: How does compilation interact with semantic caching?

**A**: They're complementary:
- **Semantic Cache**: Matches similar queries (85%+ similarity)
- **Query Compilation**: Matches exact same pattern (100% hash match)

Both active means:
1. Semantic match found? Use cached result (instant)
2. Exact compilation match? Use compiled path (very fast)
3. Neither? Execute and cache both ways

### Q: What happens during a schema change?

**A**: Automatically handled:
1. System detects schema change
2. Invalidates affected cached plans
3. Invalidates related prepared statements
4. Logs invalidation event
5. Fetches fresh EXPLAIN on next execution

### Q: Can I see what queries are compiled?

**A**: Yes, in the Compilation Dashboard:
1. Go to **Compilation** tab
2. Click **🗄️ Per-Connection** sub-tab
3. Select a connection
4. View all compiled queries with metrics

### Q: What's the overhead of compilation system?

**A**: Minimal and measured:
- Normalization: 0.2-1.5ms per query
- Cache lookup: < 0.001ms per query
- Statement management: < 0.1ms per query
- **Total overhead: < 2ms per query**

If queries are repeated 2+ times, the speedup (12-50ms) far exceeds the overhead.

### Q: How do I know if compilation is helping?

**A**: Check the metrics:
1. Go to **Compilation** tab
2. Look at **📊 Overview** sub-tab
3. Check **Speedup** card
4. Positive value = compilation is helping
5. High value = very effective

---

## Additional Resources

- **Performance Analysis**: See `docs/QUERY_COMPILATION_PHASE6_REPORT.md`
- **Manual Testing**: See `docs/QUERY_COMPILATION_MANUAL_TESTING_GUIDE.md`
- **Implementation Details**: See `CLAUDE.md` (compilation section)
- **API Reference**: `/api/docs` (Swagger UI)

---

## Support

For issues or questions about query compilation:

1. **Check this guide** - Most common questions answered in FAQ
2. **Review dashboard** - Compilation statistics often reveal the issue
3. **Check logs** - Info/warning logs provide detailed insights
4. **See troubleshooting** - Organized by symptom

---

**Document Version**: 1.0
**Last Updated**: December 7, 2024
**Status**: Complete & Ready for Production

