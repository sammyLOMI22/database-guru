# API Reference

Detailed documentation for all API endpoints in Database Guru.

## Endpoint Organization

All endpoints are in `src/api/endpoints/`.

## Core Endpoints

### Query Processing
**File**: `query.py`
- `POST /api/query/` - Main query processing endpoint
- Supports `session_id` for conversational context

### Multi-Database
**File**: `multi_db_query.py`
- Multi-database query handling with parallel execution
- Pre-validation integration (January 7, 2026)
- Narrative generation support (December 13, 2025)

### Connections
**File**: `connections.py`
- Database connection management (CRUD)

### Chat Sessions
**File**: `chat.py`
- Chat session management
- `GET /sessions/{id}/context` - Get conversation context
- `DELETE /sessions/{id}/context` - Clear conversation context

## Feedback & Learning

### User Feedback
**File**: `feedback.py`
- User feedback submission and stats

### Learned Corrections
**File**: `learned_corrections.py`
- View learned patterns

### Mappings (November 10, 2025)
**File**: `mappings.py`

**10 endpoints total**:
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/mappings/columns` | List column mappings |
| DELETE | `/mappings/columns/{id}` | Delete column mapping |
| GET | `/mappings/tables` | List table mappings |
| DELETE | `/mappings/tables/{id}` | Delete table mapping |
| GET | `/mappings/patterns` | List result patterns |
| DELETE | `/mappings/patterns/{id}` | Delete pattern |
| GET | `/mappings/stats` | Get statistics |
| POST | `/mappings/patterns/{id}/helpful` | Track helpfulness |

**Features**:
- Advanced filtering by connection_name, table_name, database_type, pattern_type, action
- Pagination support (limit/offset)
- Statistics aggregation and analytics

## Verification & Planning

### Result Verification
**File**: `result_verification.py`
- Manual result verification

### Query Planning
**File**: `query_planning.py`
- Query plan generation

### Confidence
**File**: `confidence.py`
- Confidence scoring API

## Configuration

### Settings
**File**: `settings.py`
- System settings and configuration
- Model configuration API endpoints

### Schema
**File**: `schema.py`
- Schema introspection

### Models
**File**: `models.py`
- Available Ollama models
- Filters embedding models from list

## Tools API (November 21, 2025)
**File**: `tools.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/tools` | List available tools (filterable by category) |
| GET | `/api/tools/stats` | Get execution statistics |
| GET | `/api/tools/stats/{tool_name}` | Get stats for specific tool |
| GET | `/api/tools/prompt` | Get tools formatted for LLM prompt |
| POST | `/api/tools/{tool_name}/invalidate-cache` | Invalidate tool cache |
| POST | `/api/tools/invalidate-all-cache` | Invalidate all tool caches |

## Cache API (November 22, 2025)
**File**: `cache.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/cache/stats` | Get combined cache statistics (semantic + LLM + embedding) |
| GET | `/api/cache/semantic/recent` | Get recent cached queries with filtering |
| DELETE | `/api/cache/semantic` | Clear semantic query cache |
| DELETE | `/api/cache/llm` | Clear LLM response cache |
| DELETE | `/api/cache/all` | Clear all caches |
| DELETE | `/api/cache/semantic/connection/{id}` | Clear cache for specific connection |

## Pools API (December 6, 2025)
**File**: `pools.py`

4 REST endpoints for connection pool monitoring and management.

## Lineage API (January 2026)
**File**: `lineage.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/lineage/parse` | Parse SQL and return lineage graph |
| GET | `/api/lineage/query/{query_id}` | Get lineage for historical query |
| POST | `/api/lineage/impact` | Analyze schema change impact |
| GET | `/api/lineage/table/{table_name}/queries` | Get queries referencing a table |
| GET | `/api/lineage/stats` | Get lineage statistics |
| GET | `/api/lineage/patterns/{connection_id}` | Get query pattern heatmap data |
