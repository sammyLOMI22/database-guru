# NoSQL Query Generation Pipeline

## Overview

This document describes how Database Guru converts natural language questions into native NoSQL queries for MongoDB, Redis, Cassandra, DynamoDB, and Elasticsearch. Each database uses its own query language — MQL, Redis commands, CQL, PartiQL, and Query DSL respectively — but all share a common handler architecture with self-correcting retry loops.

For the SQL pipeline, see [SQL_GENERATION_PIPELINE.md](SQL_GENERATION_PIPELINE.md).

---

## Architecture

### High-Level Flow

```
User Question (NoSQL Connection)
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     NOSQL ROUTER                                │
├─────────────────────────────────────────────────────────────────┤
│  1. is_nosql(database_type) check                               │
│  2. Instantiate database-specific handler                       │
│  3. Call handler.handle() with standardized parameters           │
│  4. Return unified result contract                               │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SCHEMA INSPECTION                            │
├─────────────────────────────────────────────────────────────────┤
│  1. Check schema cache (30-minute TTL)                           │
│  2. If stale: connect via client pool, sample data               │
│  3. Infer field names, types, cardinality from samples           │
│  4. Format schema for LLM prompt                                 │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     NATIVE QUERY GENERATION                      │
├─────────────────────────────────────────────────────────────────┤
│  1. LLM generates native query via Ollama (temp=0.1)             │
│  2. Response parsed: JSON extraction with markdown fallback      │
│  3. Query object created (MQLQuery / RedisCommand / CQL / etc.)  │
│  4. Write safety check (block INSERT/UPDATE/DELETE by default)   │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Execute via native driver (motor, redis-py, cassandra,       │
│     boto3, elasticsearch-py)                                     │
│  2. 30-second timeout protection                                 │
│  3. Result normalization to unified contract                     │
│  4. Non-JSON serialization (datetime, ObjectId, bytes, Decimal)  │
│  5. Row limit enforcement (default 1000)                         │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SELF-CORRECTION (If Error)                   │
├─────────────────────────────────────────────────────────────────┤
│  Up to 3 attempts per query:                                     │
│  1. Classify error → ErrorType + human-readable hint             │
│  2. Pass error context + hint to LLM (temp=0.2)                  │
│  3. LLM regenerates with error awareness                         │
│  4. Re-execute and verify                                        │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RESPONSE                                     │
├─────────────────────────────────────────────────────────────────┤
│  1. Unified result dict matching SQL pipeline contract            │
│  2. Display string of native query (shell syntax)                │
│  3. Agent trace with per-attempt tracking                        │
│  4. self_corrected=True if success on attempt > 1                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Supported Databases

| Database | Query Language | Generator Output | Driver |
|----------|---------------|-----------------|--------|
| **MongoDB** | MQL (MongoDB Query Language) | `MQLQuery` dataclass (JSON) | motor (async) |
| **Redis** | Redis Commands | `RedisCommand` dataclass | redis-py (async) |
| **Cassandra** | CQL (Cassandra Query Language) | CQL string | cassandra-driver |
| **DynamoDB** | PartiQL | PartiQL string | aioboto3 |
| **Elasticsearch** | Query DSL | JSON dict | elasticsearch[async] |

---

## Shared Architecture

Every NoSQL database follows the same component pattern:

```
src/nosql/{database}/
├── handler.py            # Orchestrator: schema → generate → execute → retry
├── {query}_generator.py  # NL → native query via LLM
├── query_executor.py     # Execute native query via driver
├── schema_inspector.py   # Infer schema from live data
├── error_classifier.py   # Map errors to ErrorType + hints
└── client_pool.py        # Manage driver connections (singleton)
```

### Base Classes (`src/nosql/base.py`)

```python
class NoSQLSchemaInspector(ABC):
    async def get_schema(connection) -> Dict[str, Any]
    def format_schema_for_llm(schema) -> str

class NoSQLQueryGenerator(ABC):
    async def generate(question, schema, model=None) -> Any
    async def generate_with_error_context(question, schema, previous_query, error_message) -> Any
    def query_to_display_string(query) -> str

class NoSQLHandler(ABC):
    async def handle(question, connection, model, allow_write, row_limit, db, ...) -> Dict
```

### Result Formatter (`src/nosql/result_formatter.py`)

Normalizes all NoSQL results to match `SQLExecutor.execute_query()` contract:

```python
def normalize_nosql_result(data, execution_time_ms, error=None, max_rows=1000) -> Dict:
    return {
        "success": bool,
        "data": List[Dict],       # rows as dicts
        "columns": List[str],     # union of all keys across documents
        "row_count": int,
        "execution_time_ms": float,
        "truncated": bool,        # True if results exceeded max_rows
        "error": Optional[str],
        "compiled": None,
    }
```

**Serialization handles:**
| Input Type | Output | Notes |
|------------|--------|-------|
| `datetime` | ISO format string | `2026-02-27T10:30:00Z` |
| `ObjectId` | string | MongoDB document IDs |
| `Decimal` | float | DynamoDB numbers |
| `bytes` | UTF-8 string or `<binary N bytes>` | Redis binary data |
| Nested dicts/lists | Recursive serialization | Preserves structure |

---

## Unified Result Contract

Every NoSQL handler returns this exact structure, matching the SQL pipeline's `SelfCorrectingSQLAgent.generate_and_execute_with_retry()`:

```python
{
    "success": bool,
    "sql": str,                # display string of native query (e.g. "db.users.find({...})")
    "result": {
        "success": bool,
        "data": List[Dict],
        "columns": List[str],
        "row_count": int,
        "execution_time_ms": float,
        "truncated": bool,
        "error": Optional[str],
    },
    "attempts": [
        {"attempt": 1, "query": str, "success": bool, "error": Optional[str], "error_type": Optional[str]},
        ...
    ],
    "self_corrected": bool,    # True if success on attempt > 1
    "total_attempts": int,
    "error": Optional[str],
    "agent_trace": Dict,       # AgentTrace steps
    "model_used": str,
}
```

This means the frontend, result narrator, data insights, and chart intelligence all work identically for SQL and NoSQL results — no special handling needed.

---

## Per-Database Details

### MongoDB (MQL)

#### Query Generator (`src/nosql/mongodb/mql_generator.py`)

**Operation Types:**
```python
class MQLOperationType(Enum):
    FIND = "find"
    FIND_ONE = "findOne"
    AGGREGATE = "aggregate"
    COUNT = "count"
    DISTINCT = "distinct"
    INSERT = "insert"      # blocked by default
    UPDATE = "update"      # blocked by default
    DELETE = "delete"      # blocked by default
```

**MQLQuery Dataclass:**
```python
@dataclass
class MQLQuery:
    operation: MQLOperationType
    collection: str
    query: Dict[str, Any] = field(default_factory=dict)
    projection: Optional[Dict] = None
    pipeline: Optional[List[Dict]] = None    # for aggregate
    sort: Optional[Dict] = None
    limit: Optional[int] = None
    skip: Optional[int] = None
    update: Optional[Dict] = None            # for update operations
    is_write: bool  # property: True for INSERT/UPDATE/DELETE
```

**System Prompt (excerpt):**
```
You are a MongoDB query generator. Convert natural language queries into MongoDB
Query Language (MQL).

Rules:
1. Use proper MongoDB operators ($eq, $gt, $gte, $lt, $lte, $in, $nin, $regex, $exists, etc.)
2. For complex queries involving grouping, sorting with aggregation, or joins,
   use aggregation pipelines
3. Return a JSON object with: operation, collection, query, projection, pipeline, sort, limit
```

**LLM Response Parsing:**
1. Try direct JSON parse
2. Try extracting from markdown code blocks (` ```json ... ``` `)
3. Try regex search for first `{...}` in response text
4. Map unknown operations to FIND as fallback

**Display String Examples:**
| Operation | Display |
|-----------|---------|
| FIND | `db.users.find({"active": true}).sort({"name": 1}).limit(10)` |
| AGGREGATE | `db.orders.aggregate([{"$group": {"_id": "$status"}}])` |
| COUNT | `db.items.countDocuments({"type": "book"})` |
| DISTINCT | `db.events.distinct("category")` |

#### Query Executor (`src/nosql/mongodb/query_executor.py`)

**Execution dispatch:**
| Operation | Method | Notes |
|-----------|--------|-------|
| FIND | `collection.find(query, projection).sort().skip().limit()` | Cursor-based, `to_list()` is async |
| FIND_ONE | `collection.find_one(query, projection)` | Returns 0–1 documents |
| AGGREGATE | `collection.aggregate(pipeline)` | Auto-appends `$limit` stage if missing |
| COUNT | `collection.count_documents(query)` | Returns `[{"count": N}]` |
| DISTINCT | `collection.distinct(field, query)` | Returns `[{"field": name, "distinct_values": [...], "count": N}]` |

#### Schema Inspector (`src/nosql/mongodb/schema_inspector.py`)

**Schema Inference Flow:**
1. List collections (exclude `system.*`)
2. Per collection: `$sample` 100 documents
3. Analyze each document recursively (2 levels deep, dot notation)
4. Infer types: `string`, `int`, `double`, `bool`, `array`, `object`, `objectId`, `date`, `mixed(...)`
5. Track nullable/missing counts

**LLM Schema Format:**
```
DATABASE: MongoDB (MQL)

Collection: users (~15,000 documents)
  Fields:
    - _id: objectId
    - name: string
    - email: string (nullable)
    - address.city: string
    - address.state: string
    - orders: array
    - created_at: date
```

---

### Redis (Commands)

#### Command Generator (`src/nosql/redis/command_generator.py`)

**RedisCommand Dataclass:**
```python
@dataclass
class RedisCommand:
    command: str           # e.g. "GET", "HGETALL", "LRANGE"
    args: List[str]        # e.g. ["user:123"]
    data_type: RedisDataType  # STRING, HASH, LIST, SET, ZSET, STREAM, JSON
    is_write: bool
```

**System Prompt (excerpt):**
```
You are a Redis command generator. Convert natural language queries into Redis commands.

Rules:
1. Identify the data type (string, hash, list, set, sorted set, stream)
2. Use appropriate commands for the data type
3. Handle key patterns (user:*, order:*, etc.)
```

**Display String:** `HGETALL user:123` (command + args joined)

---

### Cassandra (CQL)

#### CQL Generator (`src/nosql/cassandra/cql_generator.py`)

**System Prompt (excerpt):**
```
You are a Cassandra CQL query generator. Convert natural language queries into valid CQL.

Rules:
1. CQL is SQL-like but with important constraints:
   - Always include the partition key in WHERE clause when possible
   - No JOIN operations - Cassandra denormalizes data
   - Use ALLOW FILTERING sparingly
```

**Key Constraints:**
- Partition key required in WHERE when possible
- No JOINs, no subqueries, no complex GROUP BY
- Limited aggregations: COUNT(*), SUM, AVG, MIN, MAX
- ALLOW FILTERING only when explicitly needed

**Output:** CQL string with trailing semicolon. Extracted from code blocks/raw text, explanatory text stripped.

**Display String:** The CQL statement itself (already human-readable).

---

### DynamoDB (PartiQL)

#### PartiQL Generator (`src/nosql/dynamodb/partiql_generator.py`)

**System Prompt (excerpt):**
```
You are a DynamoDB PartiQL query generator. Convert natural language queries into valid PartiQL.

Rules:
1. PartiQL is SQL-like but for DynamoDB
2. Table names MUST be double-quoted: SELECT * FROM "MyTable"
3. Always include the partition key in WHERE clause when possible
```

**Key Constraints:**
- Table names in double quotes: `SELECT * FROM "Orders"`
- String values in single quotes: `WHERE status = 'active'`
- No JOINs, no subqueries
- Case-sensitive attribute names
- Use `EXISTS()` for attribute existence checks

**Output:** PartiQL string. Extracted from code blocks/raw text.

**Display String:** The PartiQL statement itself.

---

### Elasticsearch (Query DSL)

#### Query DSL Generator (`src/nosql/elasticsearch/query_dsl_generator.py`)

**System Prompt (excerpt):**
```
You are an Elasticsearch Query DSL generator. Convert natural language into Elasticsearch queries.

Rules:
1. Return a valid JSON object with these keys:
   - "index": the index name to search
   - "query": the query clause (match, term, range, bool, etc.)
   - "aggs": optional aggregations
```

**Query Object Structure:**
```json
{
    "index": "logs-2026",
    "query": {"bool": {"must": [{"match": {"message": "error"}}]}},
    "aggs": {"status_counts": {"terms": {"field": "status.keyword"}}},
    "sort": [{"timestamp": "desc"}],
    "size": 100
}
```

**Query Types:**
| Type | Use Case | Example |
|------|----------|---------|
| `match` | Full-text search | `{"match": {"message": "error"}}` |
| `term` | Exact keyword match | `{"term": {"status.keyword": "active"}}` |
| `range` | Numeric/date ranges | `{"range": {"price": {"gte": 100}}}` |
| `bool` | Complex combinations | `{"bool": {"must": [...], "should": [...]}}` |

**Display String:**
```
GET /logs-2026/_search
{
  "query": {"match": {"message": "error"}},
  "size": 100
}
```

#### Schema Inspector (`src/nosql/elasticsearch/schema_inspector.py`)

**Flow:**
1. `cat.indices()` — list all indices (exclude `.` prefix system indices)
2. Per index: `indices.get_mapping()` to get field mappings
3. Flatten nested `properties` with dot notation (max 2 levels)
4. Extract doc count from indices info

**LLM Schema Format:**
```
DATABASE: Elasticsearch (Query DSL)

Index: logs-2026 (~1,500,000 documents)
  Fields:
    - timestamp: date
    - message: text
    - status: keyword
    - response_time: float
    - user.name: text
    - user.id: keyword

Query DSL Notes:
- Use 'query' for filtering (match, term, range, bool)
- Use 'aggs' for aggregations (terms, avg, sum, min, max, date_histogram)
```

---

## Error Classification & Self-Correction

Each database has an `error_classifier.py` that maps native error messages to a shared `ErrorType` enum (from `src/llm/self_correcting_agent.py`):

| ErrorType | MongoDB Example | Redis Example | Cassandra Example | DynamoDB Example | ES Example |
|-----------|----------------|---------------|-------------------|-----------------|------------|
| `TABLE_NOT_FOUND` | collection 'X' not found | — | unconfigured table X | ResourceNotFoundException | index_not_found |
| `COLUMN_NOT_FOUND` | path 'X' doesn't exist | — | Undefined column name X | ValidationException (attribute) | — |
| `SYNTAX_ERROR` | unknown operator: $badop | wrong number of arguments | mismatched input 'SELCT' | Syntax error in PartiQL | parsing_exception |
| `TYPE_MISMATCH` | can't convert from string to int | WRONGTYPE | Type error: cannot assign | — | number_format_exception |
| `PERMISSION_DENIED` | not authorized on admin | NOAUTH | Unauthorized: user has no permission | AccessDeniedException | security_exception |
| `TIMEOUT` | operation timed out | timeout | OperationTimedOut | — | timeout |
| `UNKNOWN` | (fallback) | (fallback) | (fallback) | (fallback) | (fallback) |

**Self-Correction Flow:**
```
Attempt 1 (temp=0.1): Generate → Execute → Error
     │
     ▼
classify_error("collection 'user' not found")
  → (TABLE_NOT_FOUND, "Collection 'user' not found. Check available collections.")
     │
     ▼
Attempt 2 (temp=0.2): generate_with_error_context(
    question, schema,
    previous_query="db.user.find({})",
    error_message="Collection 'user' not found. Check available collections."
)
  → LLM corrects to "db.users.find({})"
     │
     ▼
Execute → Success → Return (self_corrected=True, total_attempts=2)
```

---

## Client Pool Architecture

Each database maintains a singleton connection pool:

| Database | Pool Class | Driver | Pool Settings |
|----------|-----------|--------|---------------|
| MongoDB | `MongoClientPool` | motor | maxPoolSize=10, minPoolSize=1, 5s connect timeout |
| Redis | `RedisClientPool` | redis-py | Single async client per connection |
| Cassandra | `CassandraClientPool` | cassandra-driver | Cluster + session per connection |
| DynamoDB | `DynamoDBClientPool` | aioboto3 | Session per region+credentials |
| Elasticsearch | `ElasticsearchClientPool` | elasticsearch[async] | AsyncElasticsearch per connection |

All pools:
- Are singletons accessed via `ClassName.get_instance()`
- Key clients by `connection_id`
- Track last access time
- Support `evict(connection_id)` and `close_all()`

---

## Multi-Database Integration

### Mixed SQL + NoSQL Chat Sessions

When a chat session includes both SQL and NoSQL connections, the `MultiDatabaseHandler` handles the integration:

#### Schema Introspection (`_introspect_nosql_database`)

```python
async def _introspect_single_database(self, conn):
    from src.nosql.router import is_nosql
    if is_nosql(conn.database_type):
        return await self._introspect_nosql_database(conn)
    # ... existing SQL introspection
```

NoSQL introspection dispatches to the appropriate schema inspector:
```python
if db_type == "mongodb":
    pool = await MongoClientPool.get_instance()
    _, mongo_db = await pool.get_client(conn)
    inspector = MongoSchemaInspector(mongo_db)
    schema_dict = await inspector.get_schema()
elif db_type == "redis":
    # ... RedisClientPool + RedisSchemaInspector
elif db_type == "cassandra":
    # ... CassandraClientPool + CassandraSchemaInspector
# ... etc
```

Returns the same shape as SQL introspection for consistent handling.

#### LLM Schema Guidance (`format_schema_for_llm`)

When NoSQL databases are present alongside SQL, the schema prompt includes:

```
## NoSQL DATA SOURCES
These databases use native query languages (NOT SQL).
Generate SEPARATE native queries for each NoSQL source.

- analytics_mongo (mongodb): Use native mongodb query syntax
- cache_redis (redis): Use native redis query syntax
```

#### Execution Dispatch (`_execute_single_query_task`)

The existing multi-DB execution path already routes via `is_nosql()`:
```python
if is_nosql(connection.database_type):
    result = await execute_nosql_query(question, connection, ...)
else:
    result = await self._execute_sql_query(question, connection, ...)
```

Both paths run in parallel via `asyncio.gather()` with the same timeout and error handling.

---

## Constants Summary

| Constant | Value | Scope |
|----------|-------|-------|
| `MAX_RETRIES` | 3 | All handlers — max generation+execution attempts |
| `SCHEMA_TTL_SECONDS` | 1800 | All handlers — 30-minute schema cache |
| `timeout_seconds` | 30 | All executors — query execution timeout |
| `max_documents` / `max_results` | 1000 | All executors — default row limit |
| `sample_size` | 100 | MongoDB/ES inspectors — docs sampled for schema inference |
| Temperature (first attempt) | 0.1 | All generators — stable first generation |
| Temperature (retry) | 0.2 | All generators — slightly more creative on retries |

---

## Frontend Integration

### Connection Modal (`DatabaseConnectionModal.tsx`)

The connection modal supports all 11 database types with conditional form layouts:

| Layout Mode | Database Types | Fields |
|-------------|---------------|--------|
| **File-path** | SQLite, DuckDB | Database path only |
| **DynamoDB** | DynamoDB | Region (→host), Access Key ID (→username), Secret Access Key (→password) |
| **Redis** | Redis | Host, port, password (optional), DB number (→database_name) |
| **Elasticsearch** | Elasticsearch | Host, port, optional username/password, optional index pattern |
| **Standard** | All others | Host, port, database name, username, password |

### Connection String Previews

| Type | Preview |
|------|---------|
| MongoDB | `mongodb://user:****@localhost:27017/mydb` |
| Redis | `redis://:****@localhost:6379/0` |
| Cassandra | `cassandra://user:****@localhost:9042/keyspace` |
| DynamoDB | `dynamodb://us-east-1 (Access Key: AKIA...)` |
| Elasticsearch | `https://user:****@localhost:9200` |

---

## Adding a New NoSQL Database

To extend the pipeline with a new database:

1. **Create module:** `src/nosql/{db}/` with `__init__.py`
2. **Implement handler:** Extend `NoSQLHandler` — schema → generate → execute → retry loop
3. **Implement generator:** Extend `NoSQLQueryGenerator` — write system prompt, parse LLM response
4. **Implement executor:** Execute native queries, return `normalize_nosql_result()`
5. **Implement schema inspector:** Extend `NoSQLSchemaInspector` — sample data, infer types
6. **Implement error classifier:** `classify_error()` → `(ErrorType, hint_string)`
7. **Implement client pool:** Singleton with `get_instance()`, `get_client()`, `evict()`, `close_all()`
8. **Register in router:** Add `db_type` check + handler import in `execute_nosql_query()`
9. **Register in multi_db_handler:** Add branch in `_introspect_nosql_database()`
10. **Add frontend support:** Add type to modal selector, default port, conditional form fields

---

## File Reference

| Component | File | Key Methods |
|-----------|------|-------------|
| **NoSQL Router** | `src/nosql/router.py` | `is_nosql()`, `execute_nosql_query()` |
| **Base Classes** | `src/nosql/base.py` | `NoSQLHandler`, `NoSQLQueryGenerator`, `NoSQLSchemaInspector` |
| **Result Formatter** | `src/nosql/result_formatter.py` | `normalize_nosql_result()`, `_serialize_value()` |
| **MongoDB Handler** | `src/nosql/mongodb/handler.py` | `handle()`, `_generate_and_execute_with_retry()` |
| **MQL Generator** | `src/nosql/mongodb/mql_generator.py` | `generate()`, `_parse_response()`, `query_to_display_string()` |
| **MongoDB Executor** | `src/nosql/mongodb/query_executor.py` | `execute()`, `_execute_find()`, `_execute_aggregate()` |
| **MongoDB Schema** | `src/nosql/mongodb/schema_inspector.py` | `get_schema()`, `_analyze_document()` |
| **MongoDB Errors** | `src/nosql/mongodb/error_classifier.py` | `classify_error()` |
| **MongoDB Pool** | `src/nosql/mongodb/client_pool.py` | `get_instance()`, `get_client()`, `evict()` |
| **Redis Handler** | `src/nosql/redis/handler.py` | `handle()` |
| **Redis Generator** | `src/nosql/redis/command_generator.py` | `generate()`, `_parse_response()` |
| **Redis Executor** | `src/nosql/redis/query_executor.py` | `execute()` |
| **Cassandra Handler** | `src/nosql/cassandra/handler.py` | `handle()` |
| **CQL Generator** | `src/nosql/cassandra/cql_generator.py` | `generate()`, `_extract_cql()` |
| **Cassandra Executor** | `src/nosql/cassandra/query_executor.py` | `execute()` |
| **DynamoDB Handler** | `src/nosql/dynamodb/handler.py` | `handle()` |
| **PartiQL Generator** | `src/nosql/dynamodb/partiql_generator.py` | `generate()`, `_extract_partiql()` |
| **DynamoDB Executor** | `src/nosql/dynamodb/query_executor.py` | `execute()` |
| **ES Handler** | `src/nosql/elasticsearch/handler.py` | `handle()` |
| **Query DSL Generator** | `src/nosql/elasticsearch/query_dsl_generator.py` | `generate()`, `_parse_response()` |
| **ES Executor** | `src/nosql/elasticsearch/query_executor.py` | `execute()` |
| **ES Schema** | `src/nosql/elasticsearch/schema_inspector.py` | `get_schema()`, `format_schema_for_llm()` |
| **Multi-DB Handler** | `src/core/multi_db_handler.py` | `_introspect_nosql_database()`, `format_schema_for_llm()` |
| **Connection Modal** | `frontend/src/components/DatabaseConnectionModal.tsx` | `renderDynamicFields()`, `handleDatabaseTypeChange()` |

---

## Test Coverage

127 tests across 6 files in `tests/nosql/`:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_router.py` | Router dispatch, `is_nosql()`, result normalization, serialization | ~20 tests |
| `test_mongodb.py` | MQLQuery, MQL parsing, display strings, generate, error classifier, executor, handler | ~40 tests |
| `test_redis.py` | Error classifier, command parsing, display strings, executor, handler | ~15 tests |
| `test_cassandra.py` | Error classifier, CQL extraction, display strings, generate, handler | ~15 tests |
| `test_dynamodb.py` | Error classifier, PartiQL extraction, display strings, generate, handler | ~15 tests |
| `test_elasticsearch.py` | Error classifier, Query DSL parsing, display strings, executor, schema inspector, handler | ~22 tests |
