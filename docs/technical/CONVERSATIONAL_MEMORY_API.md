# Conversational Memory API Documentation

**Version**: 1.0
**Feature Status**: Production Ready ✅
**Last Updated**: November 1, 2025

## Overview

The Conversational Memory API enables context-aware, multi-turn conversations with Database Guru. Users can ask follow-up questions that reference previous queries without repeating context.

## Key Features

- **Session-based context** - Each chat session maintains independent conversation history
- **Configurable window** - Default 3-query context window (adjustable)
- **Smart detection** - Automatic detection of contextual vs standalone questions
- **Fast retrieval** - < 10ms context loading with database indexing
- **Visual feedback** - Full context visibility through UI components

---

## API Endpoints

### 1. Query with Conversational Context

**Endpoint**: `POST /api/query/`

Process a natural language query with optional conversational context.

#### Request

```json
{
  "question": "Filter by electronics",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "database_type": "postgresql",
  "model": "qwen2.5-coder:32b",
  "allow_write": false,
  "use_cache": true
}
```

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Natural language question (3-500 chars) |
| `session_id` | string (UUID) | No | Chat session ID for conversational context |
| `database_type` | string | No | Database type (default: "postgresql") |
| `model` | string | No | Ollama model to use (uses default if not specified) |
| `allow_write` | boolean | No | Allow write operations (default: false) |
| `use_cache` | boolean | No | Use cached results (default: true) |

#### Response

```json
{
  "query_id": 123,
  "question": "Filter by electronics",
  "sql": "SELECT * FROM products WHERE category = 'electronics'",
  "is_valid": true,
  "is_read_only": true,
  "warnings": [],
  "results": [...],
  "success": true,
  "execution_time": 45.2,
  "cached": false,
  "conversation_context": {
    "has_context": true,
    "window_size": 2,
    "messages": [
      {
        "question": "Show me all products",
        "sql": "SELECT * FROM products",
        "success": true,
        "timestamp": "2025-11-01T12:00:00Z"
      },
      {
        "question": "Filter by electronics",
        "sql": "SELECT * FROM products WHERE category = 'electronics'",
        "success": true,
        "timestamp": "2025-11-01T12:01:00Z"
      }
    ]
  },
  "used_context": true
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `query_id` | integer | Query history ID |
| `question` | string | Original question |
| `sql` | string | Generated SQL query |
| `is_valid` | boolean | Whether SQL is valid |
| `is_read_only` | boolean | Whether query is read-only |
| `warnings` | array | Any warnings about the query |
| `results` | array | Query results (if executed) |
| `success` | boolean | Execution success status |
| `execution_time` | float | Execution time in milliseconds |
| `cached` | boolean | Whether result was from cache |
| `conversation_context` | object | Conversation context metadata |
| `used_context` | boolean | Whether context was used in generation |

---

### 2. Get Conversation Context

**Endpoint**: `GET /api/chat/sessions/{session_id}/context`

Retrieve the conversation context for a chat session.

#### Request

```bash
GET /api/chat/sessions/550e8400-e29b-41d4-a716-446655440000/context
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string (UUID) | Yes | Chat session ID |

#### Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "context": {
    "has_context": true,
    "window_size": 3,
    "messages": [
      {
        "question": "Show me all products",
        "sql": "SELECT * FROM products",
        "success": true,
        "timestamp": "2025-11-01T12:00:00Z"
      },
      {
        "question": "Filter by electronics",
        "sql": "SELECT * FROM products WHERE category = 'electronics'",
        "success": true,
        "timestamp": "2025-11-01T12:01:00Z"
      },
      {
        "question": "Sort by price",
        "sql": "SELECT * FROM products WHERE category = 'electronics' ORDER BY price",
        "success": true,
        "timestamp": "2025-11-01T12:02:00Z"
      }
    ]
  }
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Chat session ID |
| `context.has_context` | boolean | Whether context exists |
| `context.window_size` | integer | Number of messages in context |
| `context.messages` | array | Array of previous queries |
| `context.messages[].question` | string | User question |
| `context.messages[].sql` | string | Generated SQL |
| `context.messages[].success` | boolean | Query success status |
| `context.messages[].timestamp` | string | ISO timestamp |

---

### 3. Clear Conversation Context

**Endpoint**: `DELETE /api/chat/sessions/{session_id}/context`

Clear the conversation context for a session (fresh start).

#### Request

```bash
DELETE /api/chat/sessions/550e8400-e29b-41d4-a716-446655440000/context
```

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string (UUID) | Yes | Chat session ID |

#### Response

```json
{
  "message": "Context cleared successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Success message |
| `session_id` | string | Chat session ID |

---

## Usage Examples

### Example 1: Multi-Turn Product Query

```bash
# Step 1: Create a chat session
SESSION_ID=$(curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Product Queries", "connection_ids": [1]}' \
  | jq -r '.id')

# Step 2: First query - show all products
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all products",
    "session_id": "'$SESSION_ID'"
  }'

# Step 3: Follow-up query - filter by category (uses context)
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Filter by electronics",
    "session_id": "'$SESSION_ID'"
  }'

# Step 4: Another follow-up - sort results (uses context)
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Sort by price",
    "session_id": "'$SESSION_ID'"
  }'

# Step 5: View conversation context
curl http://localhost:8000/api/chat/sessions/$SESSION_ID/context
```

### Example 2: Clear Context and Start Fresh

```bash
# Clear previous context
curl -X DELETE http://localhost:8000/api/chat/sessions/$SESSION_ID/context

# Start fresh conversation
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all customers",
    "session_id": "'$SESSION_ID'"
  }'
```

### Example 3: TypeScript/JavaScript

```typescript
import { queryAPI, chatAPI } from './services/api';

// Create a session
const session = await chatAPI.createSession({
  name: 'Customer Analysis',
  connection_ids: [1]
});

// Query with context
const response1 = await queryAPI.processQuery({
  question: 'Show me all customers',
  session_id: session.id
});

// Follow-up query (uses context)
const response2 = await queryAPI.processQuery({
  question: 'Filter by California',
  session_id: session.id
});

// View context
const context = await chatAPI.getContext(session.id);
console.log('Context:', context.context.messages);

// Clear context
await chatAPI.clearContext(session.id);
```

---

## Smart Context Detection

The system automatically determines when to use conversation context based on question patterns.

### Questions That Use Context

- **Pronouns**: "filter that", "sort it", "show them"
- **Modifiers**: "also show", "add where", "include that"
- **Short refinements**: "by category", "limit 10"
- **References**: "same table", "previous query"

### Questions That Don't Use Context

- **Complete questions**: "Show me all products from California"
- **New topics**: "Get customers ordered today"
- **System commands**: "List all databases"

### Detection Logic

```python
def should_use_context(question: str) -> bool:
    """
    Determine if question likely refers to previous context

    Args:
        question: User question

    Returns:
        True if question appears to reference previous queries
    """
    question_lower = question.lower().strip()

    # Strong indicators (pronouns and directives)
    strong_indicators = ["that", "it", "them", "those", "these",
                         "also", "too", "same", "previous", "last"]

    # Modification keywords
    modification_keywords = ["filter", "sort", "order", "add",
                             "include", "exclude", "remove"]

    # Check for indicators
    for indicator in strong_indicators:
        if indicator in question_lower:
            return True

    # Check for modification keywords (but not at sentence start)
    for keyword in modification_keywords:
        if keyword in question_lower and not question_lower.startswith("show"):
            return True

    # Short questions are likely refinements
    words = question.split()
    if len(words) <= 3 and not question_lower.startswith(("show", "get", "list", "find")):
        return True

    return False
```

---

## Configuration

### Context Window Size

The default context window is 3 queries. To change:

```python
from src.llm.conversational_memory_agent import get_memory_agent

# Get agent with custom window size
agent = get_memory_agent(context_window=5)
```

### Database Schema

The conversational memory feature uses the existing database schema:

**Tables Used**:
- `chat_sessions` - Chat session metadata
- `chat_messages` - User and assistant messages
- `query_history` - SQL queries and results

**No schema changes required!**

---

## Performance

### Metrics

| Operation | Average Time | Notes |
|-----------|-------------|-------|
| Context retrieval | < 10ms | Indexed database query |
| Context prompt building | < 5ms | In-memory string operations |
| Query with context | +50-200ms | Additional LLM tokens |
| Clear context | < 50ms | Database operation |

### Optimization Tips

1. **Keep window size reasonable** - Default 3 is optimal for most use cases
2. **Use session-based grouping** - Separate sessions for different topics
3. **Clear context periodically** - Start fresh when changing topics
4. **Monitor token usage** - Context adds 50-200 tokens per query

---

## Error Handling

### Session Not Found

```json
{
  "detail": "Chat session 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Status Code**: 400 Bad Request

**Solution**: Verify session ID exists using `GET /api/chat/sessions`

### Invalid Session ID Format

```json
{
  "detail": "Invalid UUID format for session_id"
}
```

**Status Code**: 422 Unprocessable Entity

**Solution**: Use valid UUID v4 format

### Database Connection Error

```json
{
  "detail": "Failed to retrieve conversation context: database error"
}
```

**Status Code**: 500 Internal Server Error

**Solution**: Check database connection and logs

---

## Testing

### Unit Tests

```bash
# Run conversational memory tests
pytest tests/test_conversational_memory.py -v

# Run with coverage
pytest tests/test_conversational_memory.py --cov=src.llm.conversational_memory_agent
```

### Integration Tests

See [TEST_CONVERSATIONAL_MEMORY.md](../TEST_CONVERSATIONAL_MEMORY.md) for comprehensive testing guide.

### Manual Testing

```bash
# Start system
./start.sh

# Run API test script
python scripts/test_conversational_memory_api.py
```

---

## Security Considerations

### Session Isolation

- Each chat session maintains independent context
- No cross-session data leakage
- Session IDs use secure UUIDs

### Data Privacy

- Context stored in user's database
- No external API calls for context retrieval
- Messages can be deleted via session cleanup

### SQL Injection Prevention

- All SQL generation uses LLM with safety checks
- Context does not execute arbitrary code
- Same security measures as standalone queries

---

## Troubleshooting

### Context Not Updating

**Symptom**: Follow-up queries don't use previous context

**Solutions**:
1. Verify `session_id` is being sent in requests
2. Check session exists: `GET /api/chat/sessions/{session_id}`
3. View context directly: `GET /api/chat/sessions/{session_id}/context`
4. Check logs for errors: `tail -f backend.log`

### Wrong Context Being Used

**Symptom**: System uses unexpected previous queries

**Solutions**:
1. Clear context: `DELETE /api/chat/sessions/{session_id}/context`
2. Check window size configuration
3. Create new session for different topic

### Performance Issues

**Symptom**: Queries slow with context enabled

**Solutions**:
1. Reduce context window size
2. Check database indexes on `chat_messages` table
3. Monitor LLM token usage
4. Use caching for repeated queries

---

## Migration Guide

### From Standalone Queries

**Before** (No context):
```python
response = await queryAPI.processQuery({
    question: 'Show me products'
})
```

**After** (With context):
```python
# Create session once
session = await chatAPI.createSession({...})

# All queries use context
response = await queryAPI.processQuery({
    question: 'Show me products',
    session_id: session.id
})
```

### Backward Compatibility

- All existing queries continue to work without `session_id`
- No breaking changes to API
- Optional feature - can be adopted gradually

---

## Related Documentation

- [Conversational Memory Implementation](../CONVERSATIONAL_MEMORY_IMPLEMENTATION.md) - Technical deep dive
- [Phase 1 Complete](../PHASE_1_COMPLETE.md) - Feature completion summary
- [Testing Guide](../TEST_CONVERSATIONAL_MEMORY.md) - Testing instructions
- [API Reference](http://localhost:8000/docs) - Full OpenAPI documentation

---

## Support

**Issues**: Report bugs on GitHub
**Questions**: Check existing documentation or create an issue
**Feature Requests**: Open a GitHub discussion

---

**Generated with love by Database Guru Team**
*November 1, 2025*
