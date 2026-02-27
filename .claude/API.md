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

### Core Lineage (Phase 11)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/lineage/parse` | Parse SQL and return lineage graph |
| GET | `/api/lineage/query/{query_id}` | Get lineage for historical query |
| POST | `/api/lineage/impact` | Analyze schema change impact |
| GET | `/api/lineage/table/{table_name}/queries` | Get queries referencing a table |
| GET | `/api/lineage/stats` | Get lineage statistics |
| GET | `/api/lineage/patterns/{connection_id}` | Get query pattern heatmap data |

### Lineage Intelligence (Phase 12)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/lineage/parse?explain=true` | Parse SQL with LLM narrative (12.1) |
| POST | `/api/lineage/impact/advise` | Get impact advice with migration plan & SQL patches (12.2) |
| GET | `/api/lineage/schema/health/{connection_id}` | Get schema health report with grade (12.3) |
| GET | `/api/lineage/patterns/{connection_id}/analyze` | Get pattern intelligence analysis (12.4) |
| GET | `/api/lineage/patterns/{connection_id}/bottlenecks/{table}` | Get bottleneck analysis for table (12.4) |
| POST | `/api/lineage/ask` | Ask natural language question about schema/lineage (12.5) |

**Phase 12 Features**:
- **12.1 Lineage Narrator**: Add `explain=true` to `/parse` for LLM-generated narrative
- **12.2 Impact Advisor**: Migration plans, SQL patches, risk explanations
- **12.3 Schema Health**: Health grades (A-F), index suggestions, anti-patterns
- **12.4 Pattern Intelligence**: Bottleneck analysis, query anti-patterns, trends
- **12.5 Conversational Lineage**: Natural language Q&A with multi-turn support

## File Data Source API (Phase 13 - January 2026)
**File**: `files.py`

Upload and query CSV/Excel files as DuckDB data sources.

### File Management Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/files/upload` | Upload CSV/XLSX/XLS file (multipart form) |
| GET | `/api/files/` | List file sources with optional filtering |
| GET | `/api/files/{file_id}` | Get file source details |
| DELETE | `/api/files/{file_id}` | Delete file source and physical file |
| GET | `/api/files/{file_id}/schema` | Get inferred schema with column types |
| GET | `/api/files/{file_id}/preview` | Get data preview (default 20, max 100 rows) |
| POST | `/api/files/{file_id}/refresh` | Re-infer schema for updated files |
| POST | `/api/files/excel-sheets` | Inspect Excel sheets before upload |

### Session File Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/sessions/{session_id}/files/{file_id}` | Add file to chat session |
| DELETE | `/sessions/{session_id}/files/{file_id}` | Remove file from session |
| GET | `/sessions/{session_id}/files` | List files in session |

### Upload Parameters
```
POST /api/files/upload
Content-Type: multipart/form-data

Parameters:
- file (required): The file to upload (.csv, .xlsx, .xls)
- name (optional): Display name for the file
- sheet_name (optional): Excel sheet to import (default: first sheet)
- session_id (optional): Chat session ID for session-scoped files
- is_global (optional): true for global scope, false for session-scoped
```

### Query Parameters for Listing
```
GET /api/files/?session_id=xxx&include_global=true&status=ready
- session_id: Filter by chat session
- is_global: Filter by global flag
- include_global: Include global files with session files
- status: Filter by processing status (pending/processing/ready/error)
```

### Response Models
- **FileSourceResponse**: Complete file source with schema_cache
- **FileSchemaResponse**: Column types, nullable, sample_values, row_count
- **FilePreviewResponse**: Columns, data array, truncation indicator
- **ExcelSheetsResponse**: Available sheets in Excel file

### Features
- **Auto Schema Inference**: DuckDB detects column types automatically
- **Type Normalization**: Maps to standard types (INTEGER, VARCHAR, etc.)
- **Content Deduplication**: SHA-256 hashing prevents duplicate storage
- **Lazy Table Loading**: Tables loaded to DuckDB only when queried
- **Session Isolation**: Files scoped to chat sessions or global

## LLM Usage API (Phase 16 - February 2026)
**File**: `llm_usage.py`

Track and monitor LLM token usage, costs, and performance across all agents.

### Usage Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm/usage/stats` | Overall usage statistics (calls, tokens, cost) |
| GET | `/api/llm/usage/by-agent` | Usage breakdown by agent type |
| GET | `/api/llm/usage/by-model` | Usage breakdown by model |
| GET | `/api/llm/usage/by-provider` | Usage breakdown by provider |
| GET | `/api/llm/usage/timeseries` | Usage over time for charting (hour/day granularity) |
| GET | `/api/llm/usage/session/{session_id}` | Per-session usage with agent breakdown |
| GET | `/api/llm/usage/recent` | Recent LLM call records with filtering |
| POST | `/api/llm/usage/aggregate` | Manually trigger usage aggregation |
| POST | `/api/llm/usage/configs/seed` | Seed default model cost configurations |

### Query Parameters
```
GET /api/llm/usage/stats?days=7          # 1-90 day window
GET /api/llm/usage/by-agent?days=30      # Agent breakdown
GET /api/llm/usage/timeseries?days=7&granularity=hour  # hour or day
GET /api/llm/usage/recent?limit=50&agent_type=sql_generator&model_name=qwen2.5-coder
```

### Response Models
- **LLMUsageStatsResponse**: total_calls, total_tokens, avg_response_time_ms, total_cost_usd
- **LLMUsageByAgentResponse**: Per-agent token and call counts
- **LLMUsageTimeSeriesResponse**: Period-based totals for charting
- **SessionUsageSummaryResponse**: Per-session breakdown with by_agent map
- **LLMUsageResponse**: Individual call records with full details

## Migration Toolkit API (Phase 20 - February 2026)
**File**: `migration.py`

Schema diff, migration planning, script generation, and data migration assistance.

### Schema Diff & Projects
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/migration/diff` | Compare two database schemas, optionally save as project |
| GET | `/api/migration/projects` | List all migration projects |
| GET | `/api/migration/projects/{id}` | Get project with full details |
| DELETE | `/api/migration/projects/{id}` | Delete a migration project |

### Migration Planning
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/migration/projects/{id}/plan` | Generate LLM-enriched migration plan |
| GET | `/api/migration/projects/{id}/plan` | Get cached migration plan |

### Script Generation
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/migration/projects/{id}/scripts` | Generate up.sql, down.sql, verify.sql |
| GET | `/api/migration/projects/{id}/scripts` | Get cached generated scripts |
| GET | `/api/migration/projects/{id}/scripts/{filename}` | Download specific script file |

### Data Migration
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/migration/projects/{id}/data-migration` | Generate batched INSERT SELECT queries |
| GET | `/api/migration/projects/{id}/data-migration` | Get cached data migration plan |

### Features
- **Schema Comparison**: Detects added/removed/modified tables, columns, indexes, constraints
- **Migration Planning**: Topological sort with FK awareness, data-loss detection, LLM intent enrichment
- **Script Generation**: Multi-dialect (PostgreSQL, MySQL, SQLite), SQLite recreate for column changes
- **Data Migration**: Staging table pattern (`table__new`), batched inserts, validation queries
- **Project Lifecycle**: draft → planned → scripted status progression
- **N+1 Prevention**: Uses `selectinload` for connection names

---

## Performance Guru API (Phase 22)

**Router**: `src/api/endpoints/performance.py`
**Prefix**: `/api/performance`

### Analysis
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/performance/analyze` | Run EXPLAIN + LLM-powered performance insights (rate-limited) |
| POST | `/api/performance/explain-only` | Run EXPLAIN without LLM interpretation (fast, no rate limit) |

### Features
- **SQL Validation**: Blocks DDL/DML (DROP, INSERT, UPDATE, DELETE, ALTER, CREATE, TRUNCATE) and multi-statement queries
- **EXPLAIN ANALYZE**: Opt-in via `run_analyze=true` (actually executes the query)
- **Schema Context**: Optional schema context passed to LLM for better index suggestions
- **Multi-Dialect**: PostgreSQL (EXPLAIN FORMAT TEXT), MySQL (EXPLAIN), SQLite (EXPLAIN QUERY PLAN), DuckDB (EXPLAIN/EXPLAIN ANALYZE)
- **Deterministic Fallback**: Returns rule-based insights when LLM is unavailable or times out
- **SQLite Short-Circuit**: Deterministic-only analysis (no LLM call) for SQLite plans
