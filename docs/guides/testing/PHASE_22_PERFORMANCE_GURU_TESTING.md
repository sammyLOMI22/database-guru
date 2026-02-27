# Phase 22: Performance Guru — Testing Guide

This guide covers how to verify the Phase 22 branch (`performance_guru`) both via automated tests and manual end-to-end walkthroughs.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Running Automated Tests](#running-automated-tests)
3. [Test Coverage Summary](#test-coverage-summary)
4. [Manual Testing: Backend API](#manual-testing-backend-api)
5. [Manual Testing: Frontend UI](#manual-testing-frontend-ui)
6. [Known Limitations & Edge Cases](#known-limitations--edge-cases)

---

## Prerequisites

```bash
# 1. Activate virtualenv
source venv/bin/activate

# 2. Ensure Ollama is running (needed for LLM-powered insights)
ollama serve &
ollama pull llama3.2:latest

# 3. Frontend dependencies
cd frontend && npm install && cd ..

# 4. Start both servers
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev &
```

You need **at least one database connection** registered in Database Guru. Any supported type works:
- SQLite (easiest — just register a local `.db` file)
- PostgreSQL
- MySQL
- DuckDB

> **LLM is optional.** If Ollama is not running, the analyzer still returns deterministic insights (rule-based warnings, seq scan detection, etc.) with `llm_used: false`.

---

## Running Automated Tests

### Run all Phase 22 tests

```bash
./run_tests.sh tests/test_explain_analyzer.py tests/test_explain_interpreter.py tests/test_performance_api.py
```

### Run individual test modules

```bash
# Explain Analyzer (Phase 22.1) — pure parsing, no mocks needed
./run_tests.sh tests/test_explain_analyzer.py

# Explain Interpreter (Phase 22.2) — async tests, mock LLM
./run_tests.sh tests/test_explain_interpreter.py

# Performance API (Phase 22.3) — schema validation, endpoint logic
./run_tests.sh tests/test_performance_api.py
```

### Run with verbose output

```bash
python -m pytest tests/test_explain_analyzer.py -v
```

### Run a specific test class or method

```bash
# Single class
python -m pytest tests/test_explain_analyzer.py::TestParsePostgreSQL -v

# Single test
python -m pytest tests/test_explain_analyzer.py::TestParsePostgreSQL::test_hash_join_tree -v
```

### Run with coverage

```bash
python -m pytest tests/test_explain_analyzer.py \
  tests/test_explain_interpreter.py \
  tests/test_performance_api.py \
  --cov=src/guru \
  --cov=src/api/endpoints/performance \
  --cov-report=html
```

---

## Test Coverage Summary

| Test File | Module Under Test | Test Count | What It Covers |
|-----------|-------------------|------------|----------------|
| `test_explain_analyzer.py` | `explain_analyzer.py` | ~36 | EXPLAIN SQL building (4 dialects), PostgreSQL plan parsing (seq scan, index scan, analyze output, join trees, disk spill, filters), MySQL parsing (full table scan, index lookup, filesort, temporary), SQLite parsing (SCAN, SEARCH, covering index, primary key, temp b-tree), DuckDB parsing, deterministic warnings, serialization |
| `test_explain_interpreter.py` | `explain_interpreter.py` | ~20 | LLM response parsing, timeout fallback, error fallback, malformed JSON handling, partial JSON, empty summary, SQLite deterministic analysis (skips LLM), fallback insights (seq scans, disk spill, no issues), prompt building (plan inclusion, warnings, schema context), tiered prompt selection (small/medium/large), serialization |
| `test_performance_api.py` | `performance.py` (endpoints) + `schemas.py` | ~21 | Schema validation (DDL blocking for DROP/UPDATE/DELETE/INSERT/ALTER/TRUNCATE/CREATE, semicolon rejection, empty SQL, CTE passthrough), connection lookup (404), full analyze endpoint (mocked), explain-only endpoint (mocked), run_analyze flag pass-through, EXPLAIN error handling (500) |

### Key scenarios tested

**Explain Analyzer — EXPLAIN SQL Building:**
- PostgreSQL: `EXPLAIN` / `EXPLAIN (ANALYZE, FORMAT TEXT)`
- MySQL: `EXPLAIN` (ANALYZE not supported)
- SQLite: `EXPLAIN QUERY PLAN` (ANALYZE silently ignored, flag overridden)
- DuckDB: `EXPLAIN` / `EXPLAIN ANALYZE`
- Unknown dialect: falls back to `EXPLAIN`

**Explain Analyzer — PostgreSQL Parsing:**
- Seq Scan → detected, table added to `seq_scan_tables`
- Index Scan using → `index_name` extracted, no seq scan flag
- EXPLAIN ANALYZE → `actual_time_ms`, `rows_actual`, `loops` parsed
- Hash Join tree → multi-node tree with `join_type`, child nodes
- Disk spill via `Sort Method: external merge` → `disk_spill=True`
- Disk spill via `Batches: 4` → hash join `disk_spill=True`
- Seq Scan with Filter + Rows Removed → warning includes row count
- Empty plan → `node_count=0`, `root_node=None`

**Explain Analyzer — MySQL Parsing:**
- `type=ALL` → Full Table Scan, added to `seq_scan_tables`
- `type=REF` with key → Index Lookup, `index_name` populated
- `Extra: Using filesort` → `disk_spill=True`, warning generated
- `Extra: Using temporary; Using filesort` → both warnings

**Explain Analyzer — SQLite Parsing:**
- `SCAN TABLE orders` → SCAN node, seq scan detected
- `SEARCH TABLE orders USING INDEX idx_status` → SEARCH node, index name extracted
- `SEARCH TABLE orders USING COVERING INDEX` → covering index parsed
- `SEARCH TABLE orders USING INTEGER PRIMARY KEY` → primary key detected
- `USE TEMP B-TREE FOR ORDER BY` → TEMP B-TREE node, warning generated

**Explain Interpreter — LLM Integration:**
- Valid JSON response → full `PerformanceInsights` with bottlenecks, index suggestions
- Timeout → fallback with `llm_used=False`, `confidence=0.4`
- Connection error → fallback
- Malformed text (not JSON) → fallback
- Partial JSON (missing fields) → graceful parse with defaults
- Empty summary → triggers fallback

**Explain Interpreter — SQLite Short-Circuit:**
- SQLite plans skip LLM entirely (`generate` never called)
- Full scan → `Full Table Scan` bottleneck detected
- TEMP B-TREE → `Temp B-Tree Sort` bottleneck
- Index-only plan → `overall_severity=good`, no bottlenecks

**Schema Validation:**
- DDL keywords (DROP, TRUNCATE, DELETE, UPDATE, INSERT, ALTER, CREATE) → rejected
- Semicolons (`SELECT 1; DROP TABLE x`) → rejected (multi-statement protection)
- SELECT queries → accepted
- CTE queries (`WITH ... SELECT`) → accepted
- Empty string → rejected (min_length=1)

---

## Manual Testing: Backend API

Start the backend server:

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

All performance endpoints are under the **performance** tag.

### Test 1: Basic EXPLAIN Analysis (POST `/api/performance/analyze`)

```bash
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM query_history WHERE id > 100",
    "connection_id": 1,
    "run_analyze": false,
    "include_schema_context": true
  }'
```

**What to verify:**
- `plan.dialect` matches the connection's database type
- `plan.raw_plan` is a non-empty array of strings (the raw EXPLAIN output)
- `plan.all_nodes` is a non-empty array of parsed plan nodes
- Each node has `node_type` (e.g., "Seq Scan", "Index Scan", "SCAN", "SEARCH")
- `plan.has_seq_scans` is `true` if any sequential scan was detected
- `plan.seq_scan_tables` lists the affected tables
- `plan.warnings` contains rule-based warnings (if any issues detected)
- `insights.summary` is a human-readable description
- `insights.overall_severity` is one of: `good`, `warning`, `critical`
- `insights.bottlenecks` lists performance issues with severity levels
- `insights.index_suggestions` has CREATE INDEX SQL (if applicable)
- `insights.confidence` is between 0.0 and 1.0
- `insights.llm_used` is `true` if Ollama responded, `false` for deterministic fallback
- `analyzed` is `false` (we didn't use EXPLAIN ANALYZE)

### Test 2: EXPLAIN ANALYZE (POST `/api/performance/analyze`)

> **Warning**: This actually executes the query on the target database.

```bash
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT COUNT(*) FROM query_history",
    "connection_id": 1,
    "run_analyze": true
  }'
```

**What to verify:**
- `analyzed` is `true`
- For PostgreSQL: nodes include `actual_time_ms`, `rows_actual`, `loops`
- For SQLite: `analyzed` is `false` (overridden) with a warning about unsupported EXPLAIN ANALYZE
- `plan.total_actual_time_ms` is populated (PostgreSQL/DuckDB only)

### Test 3: EXPLAIN Only — No LLM (POST `/api/performance/explain-only`)

```bash
curl -X POST http://localhost:8000/api/performance/explain-only \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM database_connections",
    "connection_id": 1,
    "run_analyze": false
  }'
```

**What to verify:**
- Response is fast (no LLM call, no rate limit)
- `plan` contains the full parsed execution plan
- `warnings` contains deterministic warnings only
- No `insights` field in the response (this endpoint skips LLM interpretation)

### Test 4: SQL Injection Protection

```bash
# Semicolon injection — should return 422
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT 1; DROP TABLE query_history",
    "connection_id": 1
  }'

# DDL — should return 422
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "DROP TABLE query_history",
    "connection_id": 1
  }'

# DML — should return 422
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "DELETE FROM query_history WHERE id > 0",
    "connection_id": 1
  }'
```

**What to verify:**
- All three return HTTP 422 Validation Error
- Error detail mentions "Performance analysis only supports SELECT queries" or "Multi-statement queries are not allowed"

### Test 5: Invalid Connection

```bash
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT 1",
    "connection_id": 99999
  }'
```

**What to verify:**
- Returns HTTP 404 with detail "Connection 99999 not found"

### Test 6: CTE Query

```bash
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "WITH recent AS (SELECT * FROM query_history WHERE id > 50) SELECT COUNT(*) FROM recent",
    "connection_id": 1
  }'
```

**What to verify:**
- CTE query is accepted (not blocked by validator)
- EXPLAIN plan is returned with node structure

### Test 7: Join Query (Best with PostgreSQL)

```bash
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT q.*, d.name FROM query_history q JOIN database_connections d ON q.connection_id = d.id WHERE d.database_type = '\''postgresql'\''",
    "connection_id": 1
  }'
```

**What to verify:**
- Plan shows join node (Hash Join, Nested Loop, or Merge Join)
- Multiple nodes in the tree with parent-child relationships
- `plan.node_count` > 1
- Insights may suggest indexes on join columns

### Test 8: LLM Fallback (Stop Ollama)

```bash
# Stop Ollama
pkill ollama

# Run analysis — should still work
curl -X POST http://localhost:8000/api/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM query_history",
    "connection_id": 1
  }'

# Restart Ollama
ollama serve &
```

**What to verify:**
- Request succeeds (does not return 500)
- `insights.llm_used` is `false`
- `insights.confidence` is 0.4 (deterministic fallback)
- `insights.summary` describes the plan structure
- `insights.bottlenecks` still populated from rule-based analysis
- `insights.general_recommendations` contains the deterministic warnings

---

## Manual Testing: Frontend UI

Start both backend and frontend:

```bash
# Terminal 1
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Test A: Performance Tab Navigation

1. Click the **Perf** tab in the header navigation bar
2. Verify the Performance Guru panel loads with:
   - Connection dropdown populated with your registered connections
   - SQL textarea placeholder text
   - EXPLAIN ANALYZE checkbox (unchecked by default)
   - Analyze button (disabled until connection and SQL are provided)
   - Empty state message ("Enter a SQL query...")

### Test B: Basic Analysis

1. Select a connection from the dropdown
2. Enter a query: `SELECT * FROM query_history WHERE id > 100`
3. Click **Analyze**
4. Verify:
   - Loading spinner appears during analysis
   - Meta info bar shows dialect, mode (EXPLAIN), node count
   - **Execution Plan** section shows a tree view with:
     - Collapsible nodes (click to expand/collapse)
     - Color coding: green for index scans, amber for seq scans, red for disk spill
     - Cost and row estimates on each node
     - "Show Raw" toggle switches to raw EXPLAIN text
   - **AI Insights** section shows:
     - Summary banner with severity color (green/amber/red)
     - Confidence percentage
     - "Deterministic Only" badge if LLM was not used
     - Bottlenecks section (if any) with severity badges
     - Index Suggestions (if any) with CREATE INDEX SQL and copy button
     - Query Rewrites (if any) with rewritten SQL and copy button
     - General Recommendations list

### Test C: EXPLAIN ANALYZE Toggle

1. Check the **EXPLAIN ANALYZE** checkbox
2. Verify the amber warning "Executes query" appears next to the checkbox
3. Click Analyze with a safe query (e.g., `SELECT COUNT(*) FROM query_history`)
4. Verify:
   - Meta info shows "EXPLAIN ANALYZE" mode
   - Plan nodes show actual time (ms) badges (blue)
   - Plan nodes show actual row counts alongside estimated

### Test D: Copy Index Suggestion

1. Run a query that produces a seq scan (e.g., `SELECT * FROM query_history WHERE original_question LIKE '%test%'`)
2. If index suggestions appear, click the copy button next to the CREATE INDEX SQL
3. Verify the SQL is copied to clipboard (paste it somewhere to confirm)

### Test E: Cross-Component Navigation (Chat → Perf)

1. Switch to the **Query** tab
2. Ask a natural language question that generates SQL (e.g., "show me all queries from the last week")
3. In the results, look for the ⚡ (Zap) icon next to the SQL code block
4. Click the Zap icon
5. Verify:
   - App switches to the **Perf** tab automatically
   - SQL textarea is pre-filled with the query from chat
   - Connection dropdown is pre-selected (if the chat result included a connection ID)
   - You can click Analyze to run the performance analysis

### Test F: Error Handling

1. Select a connection, enter invalid SQL: `SELECT FROM`
2. Click Analyze
3. Verify:
   - Red error banner appears with the database error message
   - No crash, app remains usable
4. Clear the error by entering valid SQL and re-analyzing

### Test G: Raw Plan Toggle

1. Run any analysis
2. In the Execution Plan section, click "Show Raw"
3. Verify:
   - Raw EXPLAIN text appears in a monospace code block
   - Click "Show Tree" to return to the tree view

### Test H: Empty State Handling

1. Navigate to the Perf tab with no connections registered
2. Verify the connection dropdown shows "Select a connection..." placeholder
3. The Analyze button should be disabled
4. Enter SQL but don't select a connection — button stays disabled
5. Select a connection but leave SQL empty — button stays disabled

---

## Known Limitations & Edge Cases

### Functional limitations

| Limitation | Detail |
|-----------|--------|
| **SELECT queries only** | The validator blocks DDL/DML and multi-statement queries. Only SELECT (including WITH/CTE) is accepted. |
| **SQLite: No EXPLAIN ANALYZE** | SQLite doesn't support EXPLAIN ANALYZE. The `analyzed` flag is forced to `false` with a warning. |
| **MySQL: No EXPLAIN ANALYZE** | MySQL's EXPLAIN doesn't include actual execution times. The `analyze` flag is silently ignored. |
| **LLM is optional** | If Ollama is unavailable, insights fall back to deterministic rule-based analysis with `confidence=0.4`. |
| **No query execution history** | Performance analysis results are not persisted. Each analysis is stateless. |
| **Rate limiting** | The `/analyze` endpoint is rate-limited (shared LLM rate limiter). The `/explain-only` endpoint is not rate-limited. |
| **Large plans** | Pathologically large EXPLAIN outputs (hundreds of nodes) may produce large API responses. |
| **DuckDB tree parsing** | DuckDB's EXPLAIN format uses box-drawing characters. The parser strips these but may miss some node types with unusual formatting. |

### Edge cases to watch for

1. **Aliased tables in PostgreSQL**: The parser uses `\S+` to capture relation names, which may truncate aliases with spaces (e.g., `orders o` is parsed as `orders`). The alias is effectively ignored but the table name is preserved.

2. **MySQL positional columns**: If a MySQL driver returns EXPLAIN rows as positional tuples instead of named columns, the parser falls back to a column-index mapping. Verify your MySQL driver returns `_mapping` attributes.

3. **DuckDB info lines**: Lines starting with `[` or `EC:` in DuckDB plans are skipped. If DuckDB changes its EXPLAIN format, the parser may miss nodes.

4. **Concurrent analysis**: Multiple simultaneous `/analyze` calls share the same module-level `ExplainAnalyzer` instance. This is safe since the analyzer is stateless.

5. **Schema context for LLM**: When `include_schema_context=true`, the schema is fetched from `SchemaCache`. If the connection is unreachable, schema context is silently omitted (debug log only).

6. **Model routing**: If a custom model is configured for `EXPLAIN_ANALYSIS` in system settings, it will be used instead of the default. The timeout is also configurable (default: 25 seconds).

### Pre-existing test failures

These tests are unrelated to Phase 22 and may fail in the full test suite:
- `test_mappings_api`
- `test_mapping_cache`
- `test_query_endpoints`
- `test_pooling_performance`
- `test_parallel_multi_db`
