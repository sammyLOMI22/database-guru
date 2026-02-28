# Phase 14: NoSQL Database Expansion — Testing Guide

This guide covers how to verify the Phase 14 NoSQL expansion both via automated tests and manual end-to-end walkthroughs. Phase 14 adds full support for MongoDB, Redis, Cassandra, DynamoDB, and Elasticsearch with native query generation, schema inference, self-correcting retry loops, and mixed SQL+NoSQL chat sessions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Running Automated Tests](#running-automated-tests)
3. [Test Coverage Summary](#test-coverage-summary)
4. [Manual Testing: Backend API](#manual-testing-backend-api)
5. [Manual Testing: Frontend UI](#manual-testing-frontend-ui)
6. [Manual Testing: Mixed SQL + NoSQL Chat](#manual-testing-mixed-sql--nosql-chat)
7. [Known Limitations & Edge Cases](#known-limitations--edge-cases)

---

## Prerequisites

```bash
# 1. Activate virtualenv
source venv/bin/activate

# 2. Ensure NoSQL driver dependencies are installed
pip install motor redis cassandra-driver aioboto3 "elasticsearch[async]"

# 3. Ensure Ollama is running (needed for LLM-powered query generation)
ollama serve &
ollama pull llama3.2:latest

# 4. Frontend dependencies
cd frontend && npm install && cd ..

# 5. Start both servers
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev &
```

For manual testing, you need **at least one NoSQL database** accessible:

| Database | Easiest Setup | Default Port |
|----------|--------------|--------------|
| **MongoDB** | `docker run -d -p 27017:27017 mongo:7` | 27017 |
| **Redis** | `docker run -d -p 6379:6379 redis:7` | 6379 |
| **Cassandra** | `docker run -d -p 9042:9042 cassandra:4` | 9042 |
| **DynamoDB** | `docker run -d -p 8000:8000 amazon/dynamodb-local` | 8000 |
| **Elasticsearch** | `docker run -d -p 9200:9200 -e discovery.type=single-node elasticsearch:8.11.0` | 9200 |

> **Automated tests don't require running databases.** All tests use mocks.

---

## Running Automated Tests

### Run all Phase 14 tests

```bash
./run_tests.sh tests/nosql/
```

### Run individual test modules

```bash
# Router (dispatch, result normalization, serialization)
./run_tests.sh tests/nosql/test_router.py

# MongoDB (MQL generation, parsing, executor, schema, error classifier, handler)
./run_tests.sh tests/nosql/test_mongodb.py

# Redis (command generation, parsing, executor, error classifier, handler)
./run_tests.sh tests/nosql/test_redis.py

# Cassandra (CQL extraction, error classifier, handler)
./run_tests.sh tests/nosql/test_cassandra.py

# DynamoDB (PartiQL extraction, error classifier, handler)
./run_tests.sh tests/nosql/test_dynamodb.py

# Elasticsearch (Query DSL parsing, executor, schema inspector, handler)
./run_tests.sh tests/nosql/test_elasticsearch.py

# Dialect registry (NoSQL enums correctly skip SQL rules)
./run_tests.sh tests/test_dialect_registry.py
```

### Run with verbose output

```bash
python -m pytest tests/nosql/ -v
```

### Run a specific test class or method

```bash
# Single class
python -m pytest tests/nosql/test_mongodb.py::TestMQLGeneratorParsing -v

# Single test
python -m pytest tests/nosql/test_mongodb.py::TestMQLGeneratorParsing::test_parse_direct_json -v
```

### Run with coverage

```bash
python -m pytest tests/nosql/ \
  --cov=src/nosql \
  --cov=src/core/multi_db_handler \
  --cov-report=html
```

### Frontend build verification

```bash
cd frontend && npm run build
```

This verifies the updated `DatabaseConnectionModal.tsx` compiles without errors.

---

## Test Coverage Summary

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_router.py` | 25 | `is_nosql()` for all types + case insensitive + SQL returns false; `normalize_nosql_result()` success/error shape, truncation, column union, scalar results, empty data; `_serialize_value()` for datetime, bytes (UTF-8 + binary), Decimal, nested dicts, lists, passthrough; `execute_nosql_query()` routing to MongoDB handler, unknown type raises ValueError |
| `test_mongodb.py` | 32 | `MQLQuery` dataclass (is_write for find/aggregate/insert/update/delete); MQL parsing (direct JSON, code block, text-surrounded, unknown operation defaults to find, invalid raises, aggregate pipeline); display strings (find, find+sort+limit, aggregate, count, distinct); generate calls Ollama; generate_with_error_context passes error hint; error classifier (7 error types); executor (write blocked, empty collection, find, count, aggregate adds $limit); handler (correct result shape, error result) |
| `test_redis.py` | 15 | Error classifier (unknown command, wrong args, WRONGTYPE, permission, timeout, unknown); command parsing (single command, code block, hash command uppercase); display string; generate calls Ollama; executor (GET, hash result, error handling); handler error result |
| `test_cassandra.py` | 15 | Error classifier (table not found, column not found, syntax error, ALLOW FILTERING hint, type mismatch, permission, timeout, unknown); CQL extraction (raw, code block, strips explanation, adds semicolon); display string; generate; handler error result |
| `test_dynamodb.py` | 13 | Error classifier (ResourceNotFound, validation key/general, PartiQL syntax, access denied, timeout, unknown); PartiQL extraction (raw, code block, strips explanation); display string; generate; handler error result |
| `test_elasticsearch.py` | 27 | Error classifier (9 patterns: index not found, field not found, no mapping, parsing, shard exception, illegal argument, security, timeout, unknown); Query DSL parsing (direct JSON, code block, text-surrounded, invalid raises); display string (includes/excludes index); generate and generate_with_error_context; executor (search hits, aggregation, timeout, default size, nested source flattening); schema inspector (get_schema skips system indices, nested properties, format_schema_for_llm); handler (error result, success shape with full contract validation) |

**Total: 127 tests**

### Key Scenarios Tested

**Router — Type Detection:**
- All 5 NoSQL types recognized (`mongodb`, `redis`, `cassandra`, `dynamodb`, `elasticsearch`)
- Case insensitive: `MongoDB` → true
- SQL types return false: `postgresql`, `mysql`, `sqlite`, `duckdb` → false
- Unknown types raise `ValueError`

**Router — Result Normalization:**
- Success result has correct shape: `success`, `data`, `columns`, `row_count`, `execution_time_ms`, `truncated`
- Error result: `success=False`, error message preserved
- Truncation at `max_rows` limit, `truncated=True`
- Column names inferred as union of all document keys
- Scalar results (single value) wrapped correctly

**Router — Serialization:**
- `datetime` → ISO format string
- `bytes` (valid UTF-8) → decoded string
- `bytes` (binary) → `<binary N bytes>`
- `Decimal` → float
- Nested dicts/lists → recursive serialization
- `None` → `None` passthrough

**MongoDB — MQL Generation:**
- Direct JSON response → `MQLQuery` with correct fields
- JSON in markdown code block → extracted and parsed
- JSON surrounded by explanatory text → first JSON object extracted
- Unknown operations (e.g., `mapReduce`) → default to FIND
- Invalid non-JSON response → raises `ValueError`
- Aggregation pipeline with `$match` + `$group` → correct pipeline list

**MongoDB — Write Safety:**
- INSERT/UPDATE/DELETE blocked when `allow_write=False`
- Error message says "not allowed"

**MongoDB — Executor:**
- FIND returns list of docs via cursor
- COUNT returns `[{"count": N}]`
- AGGREGATE auto-appends `$limit` stage if missing

**MongoDB — Handler Contract:**
- Result has all required keys: `success`, `sql`, `result`, `attempts`, `self_corrected`, `total_attempts`, `error`, `agent_trace`, `model_used`
- Error returns: `success=False`, error message in `error` field, non-null `agent_trace`

**Cassandra — CQL Specific:**
- ALLOW FILTERING error → hint includes "ALLOW FILTERING" suggestion
- CQL extracted from `\`\`\`cql` code blocks
- Explanatory text after query stripped
- Trailing semicolon auto-appended

**DynamoDB — PartiQL Specific:**
- ResourceNotFoundException → TABLE_NOT_FOUND
- ValidationException with "key" → COLUMN_NOT_FOUND
- ValidationException general → SYNTAX_ERROR
- PartiQL syntax error → SYNTAX_ERROR
- AccessDeniedException → PERMISSION_DENIED

**Elasticsearch — Query DSL Specific:**
- Search hits returned as flat documents
- Aggregation results returned as rows
- Default `size: 1000` applied when not specified
- Nested `_source` fields flattened (dot notation)
- Schema inspector skips system indices (`.` prefix)
- Schema handles nested properties with dot notation

**Dialect Registry:**
- All 5 NoSQL enum members (MONGODB, REDIS, CASSANDRA, DYNAMODB, ELASTICSEARCH) correctly skip SQL rules assertion

---

## Manual Testing: Backend API

Start the backend server:

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### Test 1: Register a MongoDB Connection

```bash
curl -X POST http://localhost:8000/api/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Local MongoDB",
    "database_type": "mongodb",
    "host": "localhost",
    "port": 27017,
    "database_name": "test_db",
    "username": "",
    "password": ""
  }'
```

**What to verify:**
- Returns 201 with connection object
- `database_type` is `"mongodb"`
- Connection appears in `GET /api/connections`

### Test 2: Register a Redis Connection

```bash
curl -X POST http://localhost:8000/api/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Local Redis",
    "database_type": "redis",
    "host": "localhost",
    "port": 6379,
    "database_name": "0",
    "username": "",
    "password": ""
  }'
```

**What to verify:**
- Returns 201 with connection object
- `database_name` is `"0"` (Redis DB number)

### Test 3: Register a DynamoDB Connection

```bash
curl -X POST http://localhost:8000/api/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AWS DynamoDB",
    "database_type": "dynamodb",
    "host": "us-east-1",
    "port": 0,
    "database_name": "",
    "username": "AKIAIOSFODNN7EXAMPLE",
    "password": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  }'
```

**What to verify:**
- Returns 201
- `host` stores the AWS region
- `username` stores the access key ID

### Test 4: Test a NoSQL Connection

```bash
curl -X POST http://localhost:8000/api/connections/test \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Redis",
    "database_type": "redis",
    "host": "localhost",
    "port": 6379,
    "database_name": "0",
    "username": "",
    "password": ""
  }'
```

**What to verify:**
- If Redis is running: returns `{"success": true, "message": "Connection successful!"}`
- If Redis is not running: returns `{"success": false, "message": "..."}`

### Test 5: Query a NoSQL Database via Chat

```bash
# 1. Create a chat session with the MongoDB connection
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MongoDB Test",
    "active_connection_ids": [<MONGODB_CONNECTION_ID>]
  }'

# 2. Ask a question
curl -X POST http://localhost:8000/api/chat/sessions/<SESSION_ID>/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "show all documents in users collection"
  }'
```

**What to verify:**
- `success` is `true` (if MongoDB has a `users` collection)
- `sql` contains a MongoDB shell-syntax display string (e.g., `db.users.find({})`)
- `result.data` is a list of documents
- `result.columns` lists all field names across documents
- `agent_trace` contains generation/execution steps
- If query fails, self-correction attempts are visible in `attempts` list

### Test 6: NoSQL Schema Introspection in Multi-DB

```bash
# Create a chat session with both SQL and NoSQL connections
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mixed Session",
    "active_connection_ids": [<SQLITE_ID>, <MONGODB_ID>]
  }'
```

**What to verify:**
- Session created successfully (no ValueError from schema introspection)
- Both connections are listed in the session
- Querying the session generates appropriate SQL for SQLite and MQL for MongoDB

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

### Test A: Connection Modal — All 11 Types Visible

1. Click **Connections** in the sidebar
2. Click **+ Add Connection**
3. Verify the type selector shows all 11 types:
   `postgresql`, `mysql`, `sqlite`, `mssql`, `oracle`, `mongodb`, `duckdb`, `redis`, `cassandra`, `dynamodb`, `elasticsearch`
4. Each type button should be clickable and highlight when selected

### Test B: Connection Modal — DynamoDB Form

1. In the connection modal, select **dynamodb**
2. Verify the form shows:
   - **AWS Region** field (pre-filled with `us-east-1`)
   - **Access Key ID** field
   - **Secret Access Key** field (password input)
   - Info banner about encrypted credentials
3. Verify these fields are **NOT** shown: Port, Database Name, Username/Password (standard)
4. Click **Inspect Protocol** and verify connection string: `dynamodb://us-east-1 (Access Key: AKIA...)`

### Test C: Connection Modal — Redis Form

1. Select **redis**
2. Verify the form shows:
   - **Host Address** (pre-filled with `localhost`)
   - **Port** (pre-filled with `6379`)
   - **Password (Optional)** field
   - **Database Number** field (pre-filled with `0`)
3. Verify **Username** is NOT shown (Redis doesn't use username by default)
4. Click **Inspect Protocol** and verify: `redis://localhost:6379/0` (or `redis://:****@localhost:6379/0` if password entered)

### Test D: Connection Modal — Elasticsearch Form

1. Select **elasticsearch**
2. Verify the form shows:
   - **Host Address** (pre-filled with `localhost`)
   - **Port** (pre-filled with `9200`)
   - **Username (Optional)** field
   - **Password (Optional)** field
   - **Index Pattern (Optional)** field with placeholder `e.g., logs-*`
3. Click **Inspect Protocol** and verify: `https://localhost:9200`

### Test E: Connection Modal — Cassandra Form

1. Select **cassandra**
2. Verify the standard form shows with:
   - **Contact Point** (label adapts from "Host Address" to "Contact Point")
   - **Port** (pre-filled with `9042`)
   - **Keyspace** (label adapts from "Database Schema Name" to "Keyspace")
   - **Username** and **Password**

### Test F: Connection Modal — Validation

1. Select **dynamodb**, leave Region empty, click **Verify Engine**
   - Should show: "AWS Region is required"
2. Fill Region, leave Access Key empty, click **Verify Engine**
   - Should show: "Access Key ID is required"
3. Select **redis**, leave Host empty, click **Verify Engine**
   - Should show: "Host is required"
4. Select **elasticsearch**, leave Host empty, click **Verify Engine**
   - Should show: "Host is required"
5. Select **elasticsearch**, fill Host + Port only (no username), click **Verify Engine**
   - Should proceed (username is optional for Elasticsearch)

### Test G: Connection Modal — Save and Verify

1. Fill out a complete Redis connection form
2. Click **Synchronize connection**
3. Verify the connection appears in the connections list with type badge
4. Click the connection to select it for querying

### Test H: Data Sources Panel

1. After adding NoSQL connections, switch to the **Query** tab
2. In the data sources panel (sidebar), verify:
   - NoSQL connections appear alongside SQL connections
   - Each shows correct database type
   - Connections can be selected/deselected for multi-source queries

---

## Manual Testing: Mixed SQL + NoSQL Chat

This is the key Phase 14 integration test — querying SQL and NoSQL databases in the same chat session.

### Test I: Create a Mixed Session

1. Have at least one SQL connection (e.g., SQLite) and one NoSQL connection (e.g., MongoDB)
2. Create a new chat session
3. Select both connections in the data sources panel
4. Ask a question like: "how many records are in each database?"

**What to verify:**
- Both databases are queried in parallel
- SQL database returns SQL results
- NoSQL database returns native query results
- Both results display correctly in the chat
- The SQL display shows the native query syntax (e.g., `db.collection.find(...)` for MongoDB)

### Test J: NoSQL-Only Session

1. Create a chat session with only a MongoDB connection
2. Ask: "show all users"
3. Verify:
   - Query generated is MQL (e.g., `db.users.find({})`)
   - Results displayed as a table
   - Column headers reflect MongoDB document field names
   - Agent trace shows generation/execution steps

### Test K: Self-Correction in Action

1. Ask a question that references a non-existent collection
2. Verify the system:
   - Shows `total_attempts > 1` if self-correction occurred
   - `self_corrected: true` if a retry succeeded
   - Error message is informative if all retries failed

---

## Known Limitations & Edge Cases

### Functional Limitations

| Limitation | Detail |
|-----------|--------|
| **Read-only by default** | NoSQL write operations (INSERT/UPDATE/DELETE) are blocked unless `allow_write=True` is passed explicitly. The frontend does not expose write mode. |
| **Schema inference is sampling-based** | MongoDB and Elasticsearch schema is inferred from sampling ~100 documents. Rare fields may be missed. |
| **No query pre-flight validation for NoSQL** | The `MultiDatabaseQueryValidator` (FULL/PARTIAL/CANNOT) only works for SQL databases. NoSQL databases always attempt execution. |
| **Redis schema is key-pattern based** | Redis doesn't have a fixed schema. The schema inspector infers structure from key patterns and types. |
| **DynamoDB: PartiQL only** | Direct DynamoDB API calls (GetItem, Query, Scan) are not supported. Only PartiQL queries are generated. |
| **Cassandra: No JOINs** | CQL doesn't support JOINs. Cross-table queries require denormalized data. |
| **Elasticsearch: No write operations** | Even with `allow_write`, ES handler only supports search/aggregation queries. |
| **LLM is required** | Unlike the SQL pipeline (which has template matching), NoSQL always requires LLM for query generation. |
| **No query compilation/caching** | NoSQL queries are not compiled or cached (no equivalent of `QueryCompiler`). |

### Edge Cases to Watch For

1. **MongoDB ObjectId serialization**: `_id` fields containing `ObjectId` are serialized to strings. Queries filtering by `_id` need string comparison.

2. **Redis binary data**: Redis values stored as binary (not UTF-8) are displayed as `<binary N bytes>`. This is correct behavior but may confuse users.

3. **Cassandra ALLOW FILTERING**: If the error classifier detects an ALLOW FILTERING error, the hint tells the LLM to add `ALLOW FILTERING`. This may produce slow queries on large tables.

4. **DynamoDB region as host**: The `host` field stores the AWS region (e.g., `us-east-1`), not a hostname. The DynamoDB client pool constructs the endpoint from the region.

5. **Elasticsearch system indices**: Indices starting with `.` (e.g., `.kibana`, `.security`) are automatically excluded from schema inspection.

6. **Mixed session schema size**: Chat sessions with many NoSQL collections + SQL tables may produce large schema prompts. The LLM context window may be a bottleneck.

7. **Connection pooling**: Each NoSQL client pool is a singleton. Changing connection credentials requires pool eviction (automatic on next request if credentials differ).

8. **Concurrent handler access**: NoSQL handlers are instantiated per-request and are stateless. Client pools are thread-safe singletons.

### Pre-existing Test Failures

These tests are unrelated to Phase 14 and may fail in the full test suite:
- `test_mappings_api`
- `test_mapping_cache`
- `test_query_endpoints`
- `test_pooling_performance`
- `test_parallel_multi_db`

---

## Verification Checklist

Use this checklist for a complete Phase 14 sign-off:

### Automated Tests
- [ ] `./run_tests.sh tests/nosql/` — all 127 tests pass
- [ ] `./run_tests.sh tests/test_dialect_registry.py` — NoSQL dialects skip SQL rules
- [ ] `cd frontend && npm run build` — no compilation errors

### Frontend Connection Modal
- [ ] All 11 database types visible in selector
- [ ] DynamoDB form: Region / Access Key / Secret fields (no port/database_name)
- [ ] Redis form: host / port / optional password / DB number (no username)
- [ ] Elasticsearch form: host / port / optional auth / optional index pattern
- [ ] Cassandra form: Contact Point / Port / Keyspace labels
- [ ] Connection string preview correct for each NoSQL type
- [ ] Validation blocks missing required fields per type

### Backend Integration
- [ ] NoSQL connections can be registered via API
- [ ] NoSQL connections can be tested via `/api/connections/test`
- [ ] Chat sessions can include NoSQL connections
- [ ] Schema introspection works for NoSQL databases
- [ ] Mixed SQL + NoSQL chat sessions don't crash
- [ ] NoSQL queries execute and return results
- [ ] Self-correction retries work (error → hint → regenerate)

### Result Contract
- [ ] NoSQL results have same shape as SQL results
- [ ] `sql` field contains human-readable native query display
- [ ] `agent_trace` records all generation/execution steps
- [ ] `attempts` list tracks each retry with query/error/success
- [ ] `self_corrected` flag is accurate
