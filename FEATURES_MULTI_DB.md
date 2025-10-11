# 🚀 New Feature: Multi-Database Query Support

## Overview

Database Guru now supports **querying multiple databases simultaneously** in a single conversation! This powerful feature allows you to compare data across different databases, validate migrations, analyze multi-tenant systems, and much more.

## What's New?

### 📊 Chat Sessions with Multiple Connections

Create chat sessions that can access multiple database connections at once:

```python
# Create a session with 3 different databases
POST /api/chat/sessions
{
  "name": "Production Analysis",
  "connection_ids": [1, 2, 3]  # Multiple databases!
}
```

### 🤖 Intelligent Multi-Database Queries

Ask questions that span multiple databases, and the AI will automatically:
- Determine which database(s) contain the relevant data
- Generate appropriate SQL for each database
- Execute queries in parallel
- Return combined results

```python
# Query across all connected databases
POST /api/multi-query/
{
  "question": "Compare total revenue across production and backup databases",
  "chat_session_id": "your-session-id"
}
```

### 💬 Persistent Chat History

All your queries and results are saved in the chat session with full context about which databases were queried.

## Example Use Cases

### 1. Data Migration Validation
```
Question: "Compare the number of customers in old_database vs new_database"

Result:
- old_database: 15,432 customers
- new_database: 15,432 customers
✅ Migration verified!
```

### 2. Multi-Tenant Analysis
```
Question: "Which tenant database has the highest number of active orders?"

Result:
- tenant_1_db: 1,250 orders
- tenant_2_db: 2,100 orders  ← Highest!
- tenant_3_db: 980 orders
```

### 3. Cross-Environment Comparison
```
Question: "Compare total users between development and production"

Result:
- development_db: 50 users
- production_db: 15,430 users
```

### 4. Regional Analytics
```
Question: "Show total sales by region across US, EU, and APAC databases"

Result:
- us_database: $1,250,000
- eu_database: $890,000
- apac_database: $750,000
```

## Quick Start

### Step 1: Set Up Database Connections

First, ensure you have multiple database connections configured:

```bash
POST /api/connections/
{
  "name": "Production DB",
  "database_type": "postgresql",
  "host": "prod.example.com",
  "port": 5432,
  "database_name": "production",
  "username": "dbuser",
  "password": "***"
}

POST /api/connections/
{
  "name": "Analytics DB",
  "database_type": "postgresql",
  "host": "analytics.example.com",
  "port": 5432,
  "database_name": "analytics",
  "username": "dbuser",
  "password": "***"
}
```

### Step 2: Create a Chat Session

```bash
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Analysis Session",
    "connection_ids": [1, 2]
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Analysis Session",
  "connections": [
    {
      "id": 1,
      "name": "Production DB",
      "database_type": "postgresql"
    },
    {
      "id": 2,
      "name": "Analytics DB",
      "database_type": "postgresql"
    }
  ]
}
```

### Step 3: Query Multiple Databases

```bash
curl -X POST http://localhost:8000/api/multi-query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Compare total orders in both databases",
    "chat_session_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

Response:
```json
{
  "query_id": 42,
  "question": "Compare total orders in both databases",
  "database_results": [
    {
      "connection_name": "Production DB",
      "sql": "SELECT COUNT(*) as total_orders FROM orders;",
      "success": true,
      "results": [{"total_orders": 15420}],
      "row_count": 1,
      "execution_time_ms": 45.2
    },
    {
      "connection_name": "Analytics DB",
      "sql": "SELECT COUNT(*) as total_orders FROM order_facts;",
      "success": true,
      "results": [{"total_orders": 15420}],
      "row_count": 1,
      "execution_time_ms": 32.1
    }
  ],
  "total_databases_queried": 2,
  "total_rows": 2,
  "total_execution_time_ms": 77.3
}
```

## API Endpoints

### Chat Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/sessions` | POST | Create new chat session |
| `/api/chat/sessions` | GET | List all chat sessions |
| `/api/chat/sessions/{id}` | GET | Get specific session |
| `/api/chat/sessions/{id}` | PATCH | Update session connections |
| `/api/chat/sessions/{id}` | DELETE | Delete session |
| `/api/chat/sessions/{id}/messages` | GET | Get chat history |

### Multi-Database Queries

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/multi-query/` | POST | Query across multiple databases |

## Testing

### Run the Test Script

```bash
# Start the server
python -m src.main

# In another terminal, run the test
python test_multi_db.py
```

The test script will demonstrate all the new features with real examples.

## Advanced Features

### Dynamic Connection Management

Add or remove databases from a chat session at any time:

```bash
PATCH /api/chat/sessions/{session_id}
{
  "connection_ids": [1, 3, 4]  # Updated list
}
```

### Query Without Chat Sessions

You can also query multiple databases directly without creating a session:

```bash
POST /api/multi-query/
{
  "question": "Show all products",
  "connection_ids": [1, 2, 3]  # Specify directly
}
```

### Cache Support

Results are cached per connection combination for faster subsequent queries:

```bash
POST /api/multi-query/
{
  "question": "Show total revenue",
  "chat_session_id": "...",
  "use_cache": true  # Enable caching
}
```

## Performance

- **Parallel Execution**: Queries run simultaneously on different databases
- **Connection Pooling**: Each database maintains its own connection pool
- **Intelligent Caching**: Results cached by connection combination
- **Schema Caching**: Database schemas cached to reduce overhead

## Backward Compatibility

All existing functionality remains unchanged:
- ✅ Single database queries still work
- ✅ Existing `/api/query/` endpoint unchanged
- ✅ Global active connection still supported
- ✅ No breaking changes to existing code

## Documentation

- **Complete Guide**: See `MULTI_DATABASE_GUIDE.md` for full documentation
- **Implementation Details**: See `MULTI_DB_IMPLEMENTATION_SUMMARY.md`
- **Test Examples**: See `test_multi_db.py` for working examples

## Questions You Can Now Ask

### Comparison Questions
- "Compare total revenue between database A and database B"
- "Which database has more active users?"
- "Show me the difference in product counts across all databases"

### Aggregation Questions
- "What's the total revenue across all my databases?"
- "Count all customers in production and backup combined"

### Validation Questions
- "Do the customer counts match between old_db and new_db?"
- "Verify all orders from production exist in analytics"

### Analysis Questions
- "Which tenant has the most transactions?"
- "Compare sales performance across regional databases"
- "Show top products by revenue in each database"

## Troubleshooting

### "No database connections specified"
Ensure you either:
- Provide a `chat_session_id` with active connections
- Provide `connection_ids` in the request
- Have a global active connection set

### "Connection not found"
Verify your connection IDs exist:
```bash
GET /api/connections/
```

### Queries timing out
- Increase timeout in request
- Optimize database queries
- Check database performance

## What's Next?

Upcoming enhancements:
- 🎨 Frontend chat UI
- 📊 Visual query builder for multi-database
- 🔗 Cross-database JOIN support
- 📅 Scheduled multi-database reports
- 👥 Connection group management

## Get Started Now!

1. **Update your server**: Pull latest changes
2. **Restart Database Guru**: `python -m src.main`
3. **Run the test**: `python test_multi_db.py`
4. **Try it yourself**: Create a chat session and start querying!

---

**Happy Multi-Database Querying!** 🎉
