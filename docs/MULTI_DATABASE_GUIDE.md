# Multi-Database Query Feature Guide

## Overview

Database Guru now supports **querying multiple databases simultaneously** within a single chat context. This allows you to:

- Compare data across different databases
- Ask questions that span multiple data sources
- Maintain context across different database connections
- Track which databases were used for each query

## Key Features

### 1. Chat Sessions with Multiple Connections

Each chat session can have multiple active database connections. All queries within that session will be aware of all connected databases.

### 2. Intelligent Query Routing

The LLM automatically determines which database(s) contain the relevant data and generates appropriate SQL for each database.

### 3. Cross-Database Comparisons

Ask questions like:
- "Compare the total number of customers in database A vs database B"
- "Which database has more products in the Electronics category?"
- "Show me the average order value across all databases"

### 4. Chat History with Context

All messages in a chat session maintain context about which databases were queried and what results were returned.

## Architecture

### Database Models

```python
ChatSession
  - id: UUID
  - name: str
  - active_connection_ids: List[int]  # Multiple DB connections
  - created_at, updated_at, last_active_at

ChatMessage
  - id: int
  - chat_session_id: UUID
  - role: 'user' | 'assistant' | 'system'
  - content: str
  - query_history_id: int (optional)
  - databases_used: JSON  # Track which DBs were queried
```

### Core Components

1. **MultiDatabaseHandler** (`src/core/multi_db_handler.py`)
   - Aggregates schemas from multiple databases
   - Executes queries on appropriate databases
   - Parses multi-database SQL output

2. **Enhanced SQL Generator** (`src/llm/sql_generator.py`)
   - New `generate_multi_database_sql()` method
   - Special prompts for multi-database scenarios
   - Parses DATABASE: prefixed queries

3. **Chat Session API** (`src/api/endpoints/chat.py`)
   - Create/read/update/delete chat sessions
   - Manage messages within sessions
   - Associate multiple connections with sessions

4. **Multi-Database Query API** (`src/api/endpoints/multi_db_query.py`)
   - Query endpoint supporting multiple databases
   - Chat session integration
   - Result aggregation

## API Usage

### 1. Create a Chat Session

```bash
POST /api/chat/sessions
{
  "name": "E-commerce Analysis",
  "connection_ids": [1, 2, 3],  # Multiple database connection IDs
  "user_id": "user123"  # Optional
}
```

Response:
```json
{
  "id": "abc-123-def-456",
  "name": "E-commerce Analysis",
  "active_connection_ids": [1, 2, 3],
  "connections": [
    {
      "id": 1,
      "name": "Production DB",
      "database_type": "postgresql",
      "database_name": "prod_ecommerce"
    },
    {
      "id": 2,
      "name": "Analytics DB",
      "database_type": "duckdb",
      "database_name": "/path/to/analytics.duckdb"
    }
  ],
  "created_at": "2025-10-11T15:30:00Z",
  "message_count": 0
}
```

### 2. Query with Chat Context

```bash
POST /api/multi-query/
{
  "question": "Compare total revenue between production and analytics databases",
  "chat_session_id": "abc-123-def-456",
  "allow_write": false,
  "use_cache": true
}
```

Response:
```json
{
  "query_id": 42,
  "question": "Compare total revenue...",
  "database_results": [
    {
      "connection_id": 1,
      "connection_name": "Production DB",
      "database_type": "postgresql",
      "sql": "SELECT SUM(total_amount) as total_revenue FROM orders;",
      "success": true,
      "results": [{"total_revenue": 125000.50}],
      "row_count": 1,
      "execution_time_ms": 45.2
    },
    {
      "connection_id": 2,
      "connection_name": "Analytics DB",
      "database_type": "postgresql",
      "sql": "SELECT SUM(revenue) as total_revenue FROM sales_summary;",
      "success": true,
      "results": [{"total_revenue": 124900.75}],
      "row_count": 1,
      "execution_time_ms": 32.1
    }
  ],
  "total_databases_queried": 2,
  "total_rows": 2,
  "total_execution_time_ms": 77.3,
  "warnings": [],
  "cached": false,
  "timestamp": "2025-10-11T15:30:15Z"
}
```

### 3. Query with Explicit Connection IDs (No Chat Session)

```bash
POST /api/multi-query/
{
  "question": "Show me all products",
  "connection_ids": [1],
  "allow_write": false
}
```

### 4. View Chat History

```bash
GET /api/chat/sessions/{session_id}/messages
```

Response:
```json
[
  {
    "id": 1,
    "chat_session_id": "abc-123-def-456",
    "role": "user",
    "content": "Compare total revenue between databases",
    "created_at": "2025-10-11T15:30:00Z"
  },
  {
    "id": 2,
    "chat_session_id": "abc-123-def-456",
    "role": "assistant",
    "content": "Queried 2 database(s), returned 2 rows",
    "query_history_id": 42,
    "databases_used": [
      {"conn_id": 1, "name": "Production DB", "rows": 1},
      {"conn_id": 2, "name": "Analytics DB", "rows": 1}
    ],
    "created_at": "2025-10-11T15:30:15Z"
  }
]
```

### 5. Update Chat Session Connections

```bash
PATCH /api/chat/sessions/{session_id}
{
  "connection_ids": [1, 3]  # Remove connection 2, keep 1, add 3
}
```

### 6. List All Chat Sessions

```bash
GET /api/chat/sessions?user_id=user123&limit=10
```

## LLM Prompt Format

When querying multiple databases, the LLM receives a combined schema:

```
# Multi-Database Schema (45 tables across 2 databases)

--- Database: Production DB (postgresql) ---
Database Name: prod_ecommerce
Connection ID: 1
Tables: 20

Table: Production DB.customers
  - id (INTEGER) PRIMARY KEY
  - name (VARCHAR)
  - email (VARCHAR)
  ...

Table: Production DB.orders
  - id (INTEGER) PRIMARY KEY
  - customer_id (INTEGER)
  - total_amount (DECIMAL)
  ...

--- Database: Analytics DB (postgresql) ---
Database Name: analytics
Connection ID: 2
Tables: 25

Table: Analytics DB.sales_summary
  - id (INTEGER) PRIMARY KEY
  - date (DATE)
  - revenue (DECIMAL)
  ...
```

The LLM responds with:

```
DATABASE: Production DB
SELECT SUM(total_amount) as total_revenue FROM orders;

DATABASE: Analytics DB
SELECT SUM(revenue) as total_revenue FROM sales_summary;
```

## Example Use Cases

### 1. Data Migration Validation

```bash
POST /api/multi-query/
{
  "question": "Compare the count of customers in old_db and new_db",
  "connection_ids": [1, 2]
}
```

### 2. Multi-Tenant Analysis

```bash
POST /api/multi-query/
{
  "question": "Which tenant database has the highest active users?",
  "connection_ids": [10, 11, 12, 13]
}
```

### 3. Development vs Production Comparison

```bash
POST /api/multi-query/
{
  "question": "Compare schema between dev and prod databases",
  "connection_ids": [1, 2]
}
```

### 4. Cross-Region Analytics

```bash
POST /api/multi-query/
{
  "question": "Show total sales by region across US and EU databases",
  "connection_ids": [5, 6]
}
```

### 5. DuckDB Analytics Integration

DuckDB is fully supported in multi-database queries! Perfect for combining production data with analytical processing:

```bash
POST /api/multi-query/
{
  "question": "Compare order volumes between PostgreSQL production and DuckDB analytics warehouse",
  "connection_ids": [1, 7]  # 1=PostgreSQL, 7=DuckDB
}
```

Example use case:
- **Production DB (PostgreSQL)**: Real-time transactional data
- **Analytics DB (DuckDB)**: Historical data for fast analytical queries

```bash
POST /api/chat/sessions
{
  "name": "Production + Analytics",
  "connection_ids": [1, 7]  # Mix PostgreSQL and DuckDB
}
```

DuckDB excels at:
- Fast aggregations on large datasets
- Complex analytical queries
- Reading Parquet/CSV files directly
- OLAP workloads

## Testing

### Running the Test Script

```bash
# Make sure the server is running
python -m src.main

# In another terminal
python test_multi_db.py
```

The test script will:
1. List existing database connections
2. Create a chat session with multiple connections
3. Run single-database queries
4. Run multi-database comparison queries
5. View chat history
6. Test direct queries without chat context

### Manual Testing with curl

```bash
# Create chat session
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Session", "connection_ids": [1]}'

# Query with chat context
curl -X POST http://localhost:8000/api/multi-query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all products",
    "chat_session_id": "your-session-id-here"
  }'
```

## Frontend Integration

### React Example

```typescript
// Create chat session
const createChatSession = async (connectionIds: number[]) => {
  const response = await fetch('/api/chat/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: 'New Session',
      connection_ids: connectionIds
    })
  });
  return response.json();
};

// Query with chat context
const queryMultiDatabase = async (sessionId: string, question: string) => {
  const response = await fetch('/api/multi-query/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      chat_session_id: sessionId,
      allow_write: false
    })
  });
  return response.json();
};

// Get chat messages
const getChatMessages = async (sessionId: string) => {
  const response = await fetch(`/api/chat/sessions/${sessionId}/messages`);
  return response.json();
};
```

## Migration from Single to Multi-Database

### Backward Compatibility

The system maintains full backward compatibility:

1. **Single Active Connection** - The old `/api/query/` endpoint still works with the global active connection
2. **Fallback Behavior** - If no chat session or connection IDs provided, multi-query endpoint falls back to active connection
3. **Existing Data** - All existing query history and connections remain functional

### Migration Steps

1. **Keep existing connections** - Your current database connections don't need to change
2. **Optionally create chat sessions** - For new multi-database workflows
3. **Use new endpoints** - Switch to `/api/multi-query/` for multi-database support
4. **Update frontend** - Add chat session UI if desired

## Performance Considerations

1. **Parallel Execution** - Queries to different databases run in parallel
2. **Connection Pooling** - Each database maintains its own connection pool
3. **Caching** - Results cached per connection combination
4. **Query Limits** - Configure `max_rows` and `timeout_seconds` per database

## Security

1. **Connection Validation** - Only valid connection IDs accepted
2. **Write Protection** - `allow_write` flag must be explicitly enabled
3. **SQL Validation** - Same validation rules apply to all queries
4. **User Isolation** - (Optional) Filter connections by user_id

## Supported Database Types

Multi-database queries work with all supported database types:

- ✅ **PostgreSQL** - Full async support
- ✅ **MySQL** - Full async support
- ✅ **SQLite** - File-based, async support
- ✅ **DuckDB** - File-based, optimized for analytics (sync operations, handled transparently)
- ✅ **MongoDB** - Document store (limited SQL support)

You can mix and match any combination! For example:
- PostgreSQL (production) + DuckDB (analytics)
- SQLite (local dev) + MySQL (staging) + PostgreSQL (production)
- Multiple DuckDB files for different datasets

## Limitations

1. **No Cross-Database JOINs** - Queries execute independently on each database
2. **Client-Side Aggregation** - Combining results happens in application layer
3. **Database Type Differences** - SQL syntax must be appropriate for each DB type
4. **Schema Introspection** - Large schemas may impact prompt size
5. **Sync vs Async** - DuckDB uses sync operations (handled transparently in thread pool)

## Troubleshooting

### Issue: "No database connections specified"

**Solution:** Ensure either:
- Chat session has active_connection_ids
- connection_ids provided in request
- Global active connection is set

### Issue: "Connection not found"

**Solution:** Verify connection IDs exist and are accessible

### Issue: Queries timing out

**Solution:**
- Increase timeout_seconds in request
- Optimize database queries
- Check database performance

### Issue: LLM not generating DATABASE: prefix

**Solution:**
- Ensure using multi-database endpoint
- Check that multiple connections provided
- Verify LLM model supports complex prompts

## Future Enhancements

Potential future features:
- Cross-database joins via temp tables
- Query result merging strategies
- Visual query plan across databases
- Database health monitoring
- Connection group presets
- Scheduled multi-database reports

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-repo/database-guru/issues
- Documentation: https://docs.database-guru.com
- Email: support@database-guru.com
