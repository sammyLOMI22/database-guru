# 🧙‍♂️ Database Guru - End-to-End Guide

## What's New - Full SQL Execution! 🎉

Database Guru now **actually executes SQL queries** and returns real results! Here's what works:

✅ **Schema Introspection** - Automatically discovers your database structure
✅ **SQL Generation** - Converts natural language to SQL using your real schema
✅ **SQL Execution** - Safely executes queries with timeout protection
✅ **Result Pagination** - Handles large result sets (max 1000 rows)
✅ **Caching** - Caches both SQL and results for fast responses

---

## Quick Start

### 1. Start Services

```bash
docker-compose up -d postgres redis ollama
docker exec -it db-qa-ollama ollama pull llama3
```

### 2. Setup Python Environment

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python src/database/init_db.py
```

### 4. Load Sample Data

```bash
python scripts/load_sample_data.py
```

This creates sample tables (customers, products, orders) with test data.

### 5. Start the API

```bash
python src/main.py
```

### 6. Run End-to-End Test

In a new terminal:

```bash
python test_end_to_end.py
```

---

## New API Endpoints

### Schema Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/schema/` | Get full database schema |
| GET | `/api/schema/tables` | List all tables |
| GET | `/api/schema/tables/{name}` | Get table details |
| POST | `/api/schema/refresh` | Refresh schema cache |
| GET | `/api/schema/formatted` | Get LLM-formatted schema |

### Query Endpoints (Updated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query/` | **Now executes SQL and returns results!** |
| POST | `/api/query/explain` | Explain SQL |
| GET | `/api/query/history` | Get query history |
| GET | `/api/query/stats` | Get statistics |

---

## Example Workflow

### 1. Check Schema

```bash
curl http://localhost:8000/api/schema/
```

Response:
```json
{
  "table_count": 4,
  "column_count": 20,
  "relationship_count": 3,
  "schema": {
    "tables": {
      "customers": {...},
      "products": {...},
      "orders": {...},
      "order_items": {...}
    }
  }
}
```

### 2. Ask a Natural Language Question

```bash
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all customers from California"
  }'
```

Response:
```json
{
  "query_id": 123,
  "question": "Show me all customers from California",
  "sql": "SELECT * FROM customers WHERE state = 'CA'",
  "is_valid": true,
  "is_read_only": true,
  "warnings": [],
  "results": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "city": "Los Angeles",
      "state": "CA"
    },
    {
      "id": 2,
      "name": "Jane Smith",
      "email": "jane@example.com",
      "city": "San Francisco",
      "state": "CA"
    }
  ],
  "row_count": 5,
  "execution_time_ms": 12.34,
  "cached": false
}
```

### 3. Try More Complex Queries

**Top products by price:**
```json
{
  "question": "What are the top 5 most expensive products?"
}
```

**Aggregation:**
```json
{
  "question": "How many completed orders are there?"
}
```

**Joins:**
```json
{
  "question": "Show me all orders with customer names"
}
```

---

## Features

### 🔒 Security

- **Read-only by default** - Write operations blocked unless explicitly allowed
- **SQL injection prevention** - Validates queries for suspicious patterns
- **Timeout protection** - Queries killed after 30 seconds
- **Row limits** - Maximum 1000 rows per query

### ⚡ Performance

- **Schema caching** - Schema cached in Redis (1 hour TTL)
- **Result caching** - Query results cached automatically
- **Connection pooling** - Efficient database connections
- **Pagination support** - Handle large result sets

### 🎯 Smart SQL Generation

- **Auto schema discovery** - No manual schema configuration needed
- **Context-aware** - Uses actual table/column names
- **Relationship detection** - Understands foreign keys
- **Few-shot learning** - Includes example queries for better results

---

## Sample Queries to Try

Once you've loaded sample data, try these:

1. **Simple filtering:**
   - "Show me all customers from California"
   - "List products in the Electronics category"

2. **Sorting:**
   - "What are the top 5 most expensive products?"
   - "Show newest customers first"

3. **Aggregation:**
   - "How many completed orders are there?"
   - "What's the average product price?"

4. **Joins:**
   - "Show orders with customer names"
   - "List products that have been ordered"

5. **Complex:**
   - "Find customers who have placed more than 2 orders"
   - "What's the total revenue by product category?"

---

## Architecture

```
User Question
     ↓
[Schema Introspection] → [Cache: 1hr]
     ↓
[LLM: Generate SQL]
     ↓
[Validate Safety]
     ↓
[Execute Query] → [Timeout: 30s, Max: 1000 rows]
     ↓
[Return Results] → [Cache Results]
```

---

## Configuration

Edit `.env` or settings:

```env
# Execution limits
MAX_QUERY_ROWS=1000
QUERY_TIMEOUT_SECONDS=30

# Caching
CACHE_TTL=3600  # 1 hour

# Schema
SCHEMA_CACHE_TTL=3600  # 1 hour
```

---

## Troubleshooting

### No results returned
- Check if sample data is loaded: `python scripts/load_sample_data.py`
- Verify tables exist: `curl http://localhost:8000/api/schema/tables`

### SQL generation errors
- Refresh schema cache: `curl -X POST http://localhost:8000/api/schema/refresh`
- Check Ollama is running: `curl http://localhost:11434/api/tags`

### Execution timeouts
- Reduce row limit or add filters to your question
- Check database performance

---

## What's Next?

Now that you have end-to-end execution working, you could add:

1. **Web UI** - Build a chat interface
2. **Export results** - Download as CSV/JSON
3. **Visualization** - Charts and graphs
4. **Query optimization** - Suggest indexes
5. **Multi-database** - Connect to multiple DBs

---

**Database Guru is now fully functional!** 🎉

Visit http://localhost:8000/docs to explore the interactive API documentation.
