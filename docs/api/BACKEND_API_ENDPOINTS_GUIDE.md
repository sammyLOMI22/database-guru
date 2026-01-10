# Database Guru API Reference

**Base URL**: `http://localhost:8000/api`
**Interactive Docs**: `http://localhost:8000/api/docs` (Swagger UI)

---

## Table of Contents

- [Query Endpoints](#query-endpoints)
- [Multi-Database Query Endpoints](#multi-database-query-endpoints)
- [Connection Endpoints](#connection-endpoints)
- [Chat Session Endpoints](#chat-session-endpoints)
- [Feedback Endpoints](#feedback-endpoints)
- [Schema Endpoints](#schema-endpoints)
- [Cache Endpoints](#cache-endpoints)
- [Tools Endpoints](#tools-endpoints)
- [Mappings Endpoints](#mappings-endpoints)
- [Learned Corrections Endpoints](#learned-corrections-endpoints)
- [Query Planning Endpoints](#query-planning-endpoints)
- [Result Verification Endpoints](#result-verification-endpoints)
- [Connection Pool Endpoints](#connection-pool-endpoints)
- [Models Endpoints](#models-endpoints)
- [Settings Endpoints](#settings-endpoints)
- [Health Endpoints](#health-endpoints)

---

## Query Endpoints

**Prefix**: `/api/query`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Execute a natural language query and get SQL results |
| `POST` | `/stream` | Stream query execution with real-time updates |
| `POST` | `/explain` | Get query explanation without executing |
| `GET` | `/history` | Get query execution history |
| `GET` | `/history/{query_id}` | Get specific query from history |
| `DELETE` | `/history/{query_id}` | Delete a query from history |
| `GET` | `/stats` | Get query execution statistics |

### Key Request Body (POST `/`)

```json
{
  "question": "How many customers are in California?",
  "connection_id": 1,
  "session_id": "optional-uuid",
  "row_limit": 100,
  "enable_narratives": true
}
```

---

## Multi-Database Query Endpoints

**Prefix**: `/api/multi-db-query`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Execute query across multiple databases |
| `POST` | `/stream` | Stream multi-database query with real-time updates |
| `POST` | `/validate` | Pre-validate query feasibility across databases |

### Key Request Body (POST `/`)

```json
{
  "question": "Show all orders",
  "connection_ids": [1, 2, 3],
  "enable_narratives": true
}
```

---

## Connection Endpoints

**Prefix**: `/api/connections`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all database connections |
| `POST` | `/` | Create a new database connection |
| `POST` | `/test` | Test a connection without saving |
| `POST` | `/{connection_id}/activate` | Set a connection as active |
| `DELETE` | `/{connection_id}` | Delete a connection |

### Key Request Body (POST `/`)

```json
{
  "name": "My PostgreSQL",
  "database_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "username": "user",
  "password": "pass"
}
```

**Supported database types**: `postgresql`, `mysql`, `sqlite`, `duckdb`, `mongodb`

---

## Chat Session Endpoints

**Prefix**: `/api/chat`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions` | Create a new chat session |
| `GET` | `/sessions` | List all chat sessions |
| `GET` | `/sessions/{session_id}` | Get a specific session |
| `PATCH` | `/sessions/{session_id}` | Update session (e.g., rename) |
| `DELETE` | `/sessions/{session_id}` | Delete a session |
| `GET` | `/sessions/{session_id}/messages` | Get messages in a session |
| `POST` | `/sessions/{session_id}/messages` | Add a message to a session |
| `GET` | `/sessions/{session_id}/context` | Get conversational context |
| `DELETE` | `/sessions/{session_id}/context` | Clear session context |

---

## Feedback Endpoints

**Prefix**: `/api/feedback`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Submit feedback on a query result |
| `POST` | `/apply` | Apply a user correction |
| `GET` | `/query/{query_id}` | Get feedback for a specific query |
| `GET` | `/recent` | Get recent feedback submissions |
| `GET` | `/stats` | Get feedback statistics |
| `DELETE` | `/{feedback_id}` | Delete feedback |

### Feedback Types

- `correct` - Mark result as correct
- `incorrect_sql` - SQL was wrong, provide correction
- `column_name` - Column name suggestion
- `table_name` - Table name suggestion
- `result_issue` - Result validation issue

---

## Schema Endpoints

**Prefix**: `/api/schema`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Get full schema for active connection |
| `GET` | `/tables` | List all tables |
| `GET` | `/tables/{table_name}` | Get details for specific table |
| `POST` | `/refresh` | Refresh schema cache |
| `GET` | `/formatted` | Get schema formatted for LLM prompts |
| `GET` | `/explore/{connection_id}` | Explore schema for a connection |
| `POST` | `/compare` | Compare schemas across connections |

---

## Cache Endpoints

**Prefix**: `/api/cache`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stats` | Get combined cache statistics |
| `GET` | `/semantic/recent` | Get recently cached queries |
| `DELETE` | `/semantic` | Clear semantic query cache |
| `DELETE` | `/llm` | Clear LLM response cache |
| `DELETE` | `/all` | Clear all caches |
| `DELETE` | `/semantic/connection/{connection_id}` | Clear cache for specific connection |

---

## Tools Endpoints

**Prefix**: `/api/tools`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List available tools |
| `GET` | `/stats` | Get tool execution statistics |
| `GET` | `/stats/{tool_name}` | Get stats for specific tool |
| `GET` | `/prompt` | Get tools formatted for LLM prompt |
| `POST` | `/{tool_name}/invalidate-cache` | Invalidate cache for a tool |
| `POST` | `/invalidate-all-cache` | Invalidate all tool caches |

### Tool Categories

- **Schema Tools**: `search_schema`, `get_table_info`, `find_columns`, `get_relationships`
- **Data Tools**: `get_sample_data`, `get_column_values`, `count_rows`
- **Query Tools**: `test_query`, `validate_sql`, `explain_query`

---

## Mappings Endpoints

**Prefix**: `/api/mappings`

Manage learned column/table name mappings and result validation patterns.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/columns` | List column name mappings |
| `DELETE` | `/columns/{mapping_id}` | Delete a column mapping |
| `GET` | `/columns/stats` | Get column mapping statistics |
| `GET` | `/tables` | List table name mappings |
| `DELETE` | `/tables/{mapping_id}` | Delete a table mapping |
| `GET` | `/tables/stats` | Get table mapping statistics |
| `GET` | `/patterns` | List result validation patterns |
| `DELETE` | `/patterns/{pattern_id}` | Delete a pattern |
| `POST` | `/patterns/{pattern_id}/helpful` | Mark pattern as helpful/not helpful |
| `GET` | `/patterns/stats` | Get pattern statistics |

---

## Learned Corrections Endpoints

**Prefix**: `/api/learned-corrections`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List learned SQL corrections |
| `GET` | `/{correction_id}` | Get specific correction |
| `GET` | `/stats/summary` | Get learning statistics |
| `DELETE` | `/{correction_id}` | Delete a correction |
| `POST` | `/reset` | Reset all learned corrections |
| `GET` | `/search/similar` | Search for similar corrections |

---

## Query Planning Endpoints

**Prefix**: `/api/query-planning`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/plan` | Create execution plan for a query |
| `POST` | `/plan-and-generate` | Create plan and generate SQL |

---

## Result Verification Endpoints

**Prefix**: `/api/result-verification`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/result` | Verify query result correctness |
| `POST` | `/execute-and-verify` | Execute query and verify results |
| `GET` | `/health` | Check verification agent health |

---

## Connection Pool Endpoints

**Prefix**: `/api/connections`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/pools/stats` | Get all pool statistics |
| `GET` | `/pools/stats/{connection_id}` | Get pool stats for connection |
| `DELETE` | `/pools/{connection_id}` | Evict a connection from pool |
| `GET` | `/pools/health` | Get pool health status |

---

## Models Endpoints

**Prefix**: `/api/models`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List available Ollama models |
| `GET` | `/details` | Get detailed model information |
| `POST` | `/pull/{model_name}` | Pull a model from Ollama |
| `GET` | `/recommended` | Get recommended models for tasks |
| `GET` | `/test/{model_name}` | Test if a model responds correctly |

---

## Settings Endpoints

**Prefix**: `/api/settings`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Get current system settings |
| `PUT` | `/` | Update system settings |
| `POST` | `/reset` | Reset settings to defaults |

### Key Settings

```json
{
  "default_model": "qwen2.5-coder:32b",
  "model_sql_generation": "duckdb-nsql",
  "model_narratives": "llama3.2:latest",
  "timeout_sql_generation": 30,
  "enable_query_templates": true,
  "enable_location_preprocessing": true,
  "auto_learn_from_feedback": true
}
```

---

## Health Endpoints

**Prefix**: `/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Basic API health check |
| `GET` | `/health` | Detailed health check with component status |

### Health Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "ollama_connected": true,
  "database_connected": true,
  "active_connections": 3
}
```

---

## Common Response Patterns

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Paginated Response

```json
{
  "items": [ ... ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

---

## Authentication

Currently, the API does not require authentication for local development. For production deployment, see the [Security Policy](../technical/SECURITY_POLICY.md).

---

## Rate Limiting

- Default: 100 requests per 60 seconds per IP
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW` environment variables

---

## See Also

- [Swagger UI](http://localhost:8000/api/docs) - Interactive API documentation
- [ReDoc](http://localhost:8000/api/redoc) - Alternative API documentation
- [OpenAPI JSON](http://localhost:8000/api/openapi.json) - OpenAPI specification
