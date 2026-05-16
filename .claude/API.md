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

## LLM Usage API (Phase 16 + Phase 17 - February/April 2026)
**File**: `llm_usage.py`

Track and monitor LLM token usage, costs, and performance across all agents and providers.

### Usage Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm/usage/stats` | Overall usage statistics (calls, tokens, cost) |
| GET | `/api/llm/usage/by-agent` | Usage breakdown by agent type |
| GET | `/api/llm/usage/by-model` | Usage breakdown by model |
| GET | `/api/llm/usage/by-provider` | Usage breakdown by provider (includes total_cost_usd) |
| GET | `/api/llm/usage/timeseries` | Usage over time for charting (hour/day granularity) |
| GET | `/api/llm/usage/session/{session_id}` | Per-session usage with agent breakdown |
| GET | `/api/llm/usage/recent` | Recent LLM call records with filtering |
| POST | `/api/llm/usage/aggregate` | Manually trigger usage aggregation |
| POST | `/api/llm/usage/configs/seed` | No-op (pricing is user-managed via model-configs) |

### Model Pricing Admin Endpoints (Phase 17)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm/usage/model-configs` | List all model pricing configurations |
| GET | `/api/llm/usage/unpriced-models` | List models seen in usage but missing pricing |
| POST | `/api/llm/usage/model-configs` | Create or update a model pricing configuration |
| DELETE | `/api/llm/usage/model-configs/{model_name}` | Delete a model pricing configuration |

### Cost Summary & Provider Comparison Endpoints (Phase 17)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm/usage/cost-summary` | Cost summary with daily breakdown and per-provider totals |
| GET | `/api/llm/usage/provider-comparison` | Compare performance and cost across providers by agent type |

### Query Parameters
```
GET /api/llm/usage/stats?days=7          # 1-90 day window
GET /api/llm/usage/by-agent?days=30      # Agent breakdown
GET /api/llm/usage/timeseries?days=7&granularity=hour  # hour or day
GET /api/llm/usage/recent?limit=50&agent_type=sql_generator&model_name=qwen2.5-coder
GET /api/llm/usage/cost-summary?days=30  # 1-365 day window
GET /api/llm/usage/provider-comparison?days=7  # 1-90 day window
```

### Response Models
- **LLMUsageStatsResponse**: total_calls, total_tokens, avg_response_time_ms, total_cost_usd
- **LLMUsageByAgentResponse**: Per-agent token and call counts
- **LLMUsageTimeSeriesResponse**: Period-based totals for charting
- **SessionUsageSummaryResponse**: Per-session breakdown with by_agent map
- **LLMUsageResponse**: Individual call records with full details
- **ModelConfigResponse**: Model pricing configuration (id, model_name, provider, costs, is_active)
- **UnpricedModelResponse**: Model seen in usage without pricing (model_name, provider, call_count, total_tokens)
- **CostSummaryResponse**: period_days, total_cost_usd, total_tokens, total_calls, avg_cost_per_call, daily_costs, by_provider
- **ProviderComparisonResponse**: period_days, by_agent_type → provider → stats (calls, latency, cost, tokens, success_rate)

## LLM Provider API (Phase 15 - April 2026)
**File**: `llm_providers.py`

Manage LLM providers, test connectivity, configure per-task routing, and store encrypted API keys.

### Provider Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm-providers/` | List all provider configs with registry status |
| GET | `/api/llm-providers/registry` | Runtime registry state with security_level |
| GET | `/api/llm-providers/{name}/config` | Get provider config |
| PUT | `/api/llm-providers/{name}/config` | Update provider config (encrypts API key) |
| DELETE | `/api/llm-providers/{name}/config` | Remove provider config |
| POST | `/api/llm-providers/{name}/test` | Test provider connectivity (synthetic prompt) |
| GET | `/api/llm-providers/{name}/models` | List available models for provider |
| GET | `/api/llm-providers/health/all` | Health check all registered providers |

### Task Routing
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm-providers/routing/tasks` | Get all task→provider routing rules |
| PUT | `/api/llm-providers/routing/tasks` | Create/update task routing rule |
| DELETE | `/api/llm-providers/routing/tasks/{task_type}` | Delete task routing rule |

### Key Concepts
- **Data Security Levels**: `local_only` (default), `cloud_private`, `unrestricted` — controls which providers can be used
- **Data Locality**: Each provider classified as `local`, `cloud_private`, or `cloud_public`
- **API Key Encryption**: Fernet symmetric encryption at rest via `LLM_ENCRYPTION_KEY`
- **Test Endpoint**: Uses synthetic prompt ("Hello, respond with OK") — never sends real data

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

## DML / Edit Mode API (Phase 18 - March 2026)
**File**: `dml.py`

Inline data editing with preview, execution, and per-connection write permissions.

### DML Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/dml/preview` | Generate and preview DML statements from changes |
| POST | `/api/dml/execute` | Execute DML changes within a transaction |
| GET | `/api/dml/permissions/{connection_id}` | Get write permissions for a connection |
| PUT | `/api/dml/permissions/{connection_id}` | Update write permissions |
| GET | `/api/dml/table-info/{connection_id}/{table_name}` | Get table columns and primary keys |

### Request/Response Models
- **DMLPreviewRequest**: connection_id, changes (list of RowChangeSchema), wrap_in_transaction
- **DMLPreviewResponse**: display SQL, statement list, change count, summary by type
- **DMLExecuteRequest**: connection_id, changes
- **ExecutionResult**: success, rows_affected, error_message, executed_sql
- **WritePermissionRequest**: allow_insert, allow_update, allow_delete, require_where_clause, max_rows_per_operation, allowed_tables
- **WritePermissionResponse**: Full permission state for a connection
- **TableInfoResponse**: table_name, primary_key_columns, columns (with type, nullable, default, is_primary_key, is_autoincrement)

### Features
- **Parameterized SQL**: All generated DML uses named parameters to prevent injection
- **Transaction Wrapping**: All executions wrapped in a single transaction with rollback on error
- **Write Permissions**: Per-connection INSERT/UPDATE/DELETE toggles, allowed_tables whitelist, max rows per operation
- **Validation**: Require WHERE clause enforcement, row limit checks, table name regex validation
- **Auth Integration**: Uses `get_optional_user` for ownership checks when `REQUIRE_AUTH` is enabled

---

## Authentication API (Phase 21 + Phase 24.8 hardening)
**File**: `auth.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/register` | Register new user (email, username, password) |
| POST | `/api/auth/login` | Login and receive JWT token (optional per-username lockout when `AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=True`) |
| POST | `/api/auth/logout` | Audit-log the logout; optionally bumps `password_version` to evict every device when `AUTH_INVALIDATE_TOKENS_ON_LOGOUT=True` |
| GET | `/api/auth/me` | Get current authenticated user info |
| POST | `/api/auth/change-password` | Self-service password change. Verifies current password, enforces complexity + history (Phase D1), bumps `password_version` (Phase A), returns a fresh `TokenResponse` so the caller stays signed in while other sessions are evicted. Per-user rate-limited when `AUTH_RATE_LIMIT_CHANGE_PASSWORD=True`. |
| POST | `/api/auth/redeem-reset` | Phase C: redeem an admin-issued one-shot reset token (`{ token, new_password }`). Walks outstanding tokens via bcrypt, marks `used_at`, rotates the password, returns a fresh `TokenResponse`. **404 when `AUTH_PASSWORD_RESET_MODE` is `temp_password`.** |

### Features
- **JWT Tokens**: HS256 algorithm with configurable expiration (default 24hr). When `AUTH_TOKEN_VERSIONING_ENABLED=True`, tokens carry a `pv` (password_version) claim and `get_current_user` rejects stale ones with 401 "Session invalidated, please sign in again." Legacy tokens with no `pv` are accepted so flipping the flag is non-destructive.
- **Password Hashing**: bcrypt via `python-jose[cryptography]`. `must_change_password` flag set on every operator reset; the frontend force-routes the user through `/change-password` before any other action.
- **Feature Flag**: `REQUIRE_AUTH=False` for backwards-compatible gradual rollout.
- **Dependencies**: `get_current_user` (401 if no token), `get_optional_user` (returns None if unauthenticated), `require_admin` (403 if not admin).
- **Audit Logging**: `register`, `login`, `login_failed`, `logout`, `password_change`, `password_change_failed`, `password_reset_redeemed`, `password_reset_redeem_failed`, `account_locked`, `account_unlocked`.

## Audit Log API (Phase 21 + Phase 24.7)
**File**: `audit.py`
**Mounted only when**: `ADMIN_UI_ENABLED=true`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/audit/logs` | List audit logs (admin only, filters + pagination) |
| GET | `/api/audit/logs/me` | List current user's audit logs |
| GET | `/api/audit/facets` | Distinct `actions` / `resource_types` for filter dropdowns (admin only) |

### Query Parameters
```
GET /api/audit/logs?action=login&resource_type=user&user_id=42&start_date=2026-04-01T00:00:00&end_date=2026-04-30T23:59:59&limit=50&offset=0
GET /api/audit/logs/me?action=create&limit=20
```

### Response Shape
```json
{
  "items": [{
    "id": 1, "user_id": 42, "username": "alice",
    "action": "login", "resource_type": "user", "resource_id": "42",
    "details": {"...": "..."}, "ip_address": "10.0.0.1",
    "timestamp": "2026-04-25T18:00:00Z"
  }],
  "total": 12345, "limit": 50, "offset": 0
}
```

## Admin Users API (Phase 24.7)
**File**: `admin_users.py`
**Mounted only when**: `ADMIN_UI_ENABLED=true`
**All endpoints require**: `require_admin` dependency; every mutation calls `log_action()`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/users` | List users with `search` (username/email), `is_active`, `is_admin`, `limit`, `offset` |
| POST | `/api/admin/users` | Create user (email, username, password ≥12 chars, optional `is_admin`) |
| PATCH | `/api/admin/users/{user_id}` | Toggle `is_active` / `is_admin`; self-lockout protected (cannot demote/deactivate self) |
| POST | `/api/admin/users/{user_id}/reset-password` | Behavior depends on `AUTH_PASSWORD_RESET_MODE` (Phase C). `temp_password` (default): returns a 16-char alnum password once. `reset_token`: returns a single-use redemption URL with TTL. `both`: returns both for transition periods. Sets `must_change_password=True` and bumps `password_version` to evict prior sessions. |
| DELETE | `/api/admin/users/{user_id}` | Idempotent soft-deactivate (`is_active=False`); returns 204. Refused with 400 when `AUTH_REQUIRE_ADMIN_QUORUM=True` and the target is the last active admin (Phase D3). Bumps `password_version` when `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE=True`. |

### Settings → Observability + Auth Hardening Surfacing (Phase 24.7 + 24.8)
`GET /api/settings/` returns the read-only flags below so the Admin → Health panel can render gates and deep-links conditionally:
- **Observability**: `metrics_enabled`, `metrics_endpoint_exposed`, `metrics_public_url`, `otel_enabled`, `otel_service_name`, `otel_traces_sampler_ratio`, `jaeger_ui_url`, `grafana_url`, `admin_ui_enabled` (frontend hides Admin tab + Observability section when false)
- **Auth hardening (Phase 24.8)**: `auth_token_versioning_enabled`, `auth_invalidate_tokens_on_deactivate`, `auth_invalidate_tokens_on_logout`, `auth_rate_limit_change_password`, `auth_change_password_per_user_per_minute`, `auth_rate_limit_login_lockout_enabled`, `auth_login_lockout_threshold`, `auth_login_lockout_window_seconds`, `auth_password_reset_mode`, `auth_password_reset_token_ttl_minutes`, `auth_password_reset_base_url`, `auth_password_history_depth`, `auth_require_admin_quorum`

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
