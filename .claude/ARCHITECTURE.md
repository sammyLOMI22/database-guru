# Architecture Reference

Detailed documentation for architectural patterns and systems in Database Guru.

## Multi-Database Support with Parallel Execution
**Status**: PRODUCTION-READY

### Components
- `UserDatabaseConnector` (`src/core/user_db_connector.py`) - Creates connections to user databases
- `MultiDatabaseHandler` (`src/core/multi_db_handler.py`) - **Parallel queries across multiple databases (3x speedup)**

### Features
- **Intelligent throttling** - Semaphore-based concurrency control (max 10 databases)
- **Dual timeout protection** - 35-second timeout prevents hanging queries
- **Comprehensive metrics** - Speedup calculation, concurrency tracking, success rates
- **Parallel schema introspection** - All databases introspected simultaneously with `asyncio.gather()`
- **Parallel query execution** - Multiple queries execute concurrently across databases
- Supports both sync (DuckDB) and async (PostgreSQL, MySQL, SQLite) sessions
- Graceful degradation: one database failure doesn't stop others
- **Frontend observability** - ParallelDatabaseMetrics component with real-time visualization

## Connection Pooling
**Status**: PRODUCTION-READY (December 6, 2025)

### Components
- `ConnectionPoolManager` (`src/core/connection_pool_manager.py`) - **30x faster connection reuse**

### Features
- **Singleton pattern** - Global pool manager with per-connection isolation
- **Pool keying** - `(connection_id, database_type)` ensures isolation
- **Supported databases** - PostgreSQL, MySQL, SQLite, DuckDB (MongoDB deferred)
- **Three-tier eviction** - Idle timeout (30 min), max age (2 hours), connection deletion
- **Background cleanup** - Automatic cleanup task runs every 5 minutes
- **Comprehensive metrics** - Active/idle connections, utilization%, wait times, health status
- **Performance improvement** - Reduces connection overhead from 150ms to ~5ms per query
- **Configuration** - 10 environment variables for fine-tuning (pool size, overflow, timeouts, cleanup)
- **API endpoints** - 4 REST endpoints for pool monitoring and management
- **Frontend dashboard** - ConnectionPoolMetrics component with real-time visualization
- **Test infrastructure** - Docker Compose for test databases (PostgreSQL, MySQL, MongoDB)
- **Async and sync support** - Handles both async pools (PostgreSQL, MySQL, SQLite) and sync pools (DuckDB)
- **Graceful shutdown** - Closes all pools cleanly on application termination

## Schema Management

### Components
- `SchemaInspector` (`src/core/schema_inspector.py`) - Introspects database schemas
- `SchemaValidator` (`src/core/schema_validator.py`) - Validates table/column references with fuzzy matching
- `LocationMapper` (`src/core/location_mapper.py`) - Converts location names to database codes (e.g., "New York" → "NY")
- Schema sampling for value-aware validation

## Execution Safety

### Components
- `SQLExecutor` (`src/core/executor.py`) - Executes SQL with timeout protection and row limits
- `DMLExecutor` (`src/dml/dml_executor.py`) - Executes INSERT/UPDATE/DELETE within transactions (Phase 18)

### Features
- Default: 1000 row limit, 30 second timeout
- Handles both async and sync database sessions
- Automatic truncation with warnings

### DML Safety (Phase 18)
- **Per-connection write permissions**: INSERT/UPDATE/DELETE individually toggled, allowed_tables whitelist
- **Parameterized SQL**: All DML uses named parameters (`:param`) to prevent injection
- **Table name validation**: Regex check (`SAFE_IDENT_RE`) blocks injection via table names
- **Require WHERE clause**: Enforced on UPDATE/DELETE by default (configurable per-connection)
- **Row limits**: Max rows per operation configurable per connection (default 100)
- **Transaction wrapping**: All DML executes in a single transaction with full rollback on error
- **Auth integration**: Write permission checks respect `REQUIRE_AUTH` and resource ownership

## Caching & Performance

### Redis Caching
- `src/cache/redis_client.py` - Query result caching

### Semantic Caching (November 22, 2025)
Intelligent query similarity matching:
- `EmbeddingService` (`src/cache/embedding_service.py`) - Text embeddings using Ollama or TF-IDF fallback
- `SemanticCache` (`src/cache/semantic_cache.py`) - Matches similar queries (30-50% higher cache hit rate)
- `LLMCache` (`src/cache/llm_cache.py`) - Caches LLM SQL generation responses (40-60% fewer LLM calls)
- Schema fingerprinting ensures cache validity across schema changes
- Configurable similarity thresholds (default: 0.85 for semantic, 0.88 for LLM)

### Other Performance Features
- **Conditional Result Verification** - Skips verification for high-confidence results (1-100 rows, first attempt)
- Rate limiting middleware (100 requests/60 seconds)
- Async operations throughout for concurrency

## User Feedback System

- Users can correct SQL/schema errors via UI
- `FeedbackValidator` (`src/llm/feedback_validator.py`) - Validates feedback before auto-learning
- 3 validation modes: strict (production), moderate (balanced), lenient (testing)
- Blocks destructive operations (DELETE, UPDATE, DROP) from auto-learning
- Comprehensive testing validates corrections actually improve results

## Learned Mapping System (November 10, 2025)

### Components
- `ColumnMapper` (`src/llm/column_mapper.py`) - Learns and applies column name corrections
- `TableMapper` (`src/llm/table_mapper.py`) - Learns and applies table name corrections
- `ResultPatternLearner` (`src/llm/result_pattern_learner.py`) - Learns result validation patterns

### Features
- **Management API** (`src/api/endpoints/mappings.py`) - View, filter, and manage learned patterns
- **Filtering** - By connection_name, table_name, database_type, pattern_type, action
- **Statistics** - Usage counts, success rates, helpfulness ratings
- **Frontend Dashboard** - 5 components for browsing and managing mappings
- Auto-learns from non-SQL feedback types (column_name, table_name, result_issue)

## Security System (November 2, 2025 / Phase 21 - March 2026)

### Prompt Injection Protection
- `PromptSanitizer` (`src/security/prompt_sanitizer.py`) - Multi-layer prompt injection protection
- Input sanitization at API boundary (Pydantic validators)
- Injection detection (15+ attack patterns)
- Safe prompt construction with XML-like delimiters
- Token limits prevent resource exhaustion
- Security logging for monitoring
- 29 comprehensive security tests passing

### Authentication & Authorization (Phase 21)
**Status**: PRODUCTION-READY

#### Components
- `AuthService` (`src/auth/service.py`) - JWT token creation/validation, bcrypt password hashing, user CRUD
- `User` model (`src/auth/models.py`) - SQLAlchemy model (id, email, username, hashed_password, is_active, is_admin, must_change_password, password_version)
- Auth dependencies (`src/auth/dependencies.py`) - FastAPI dependencies for auth injection
- `AuditLog` model (`src/auth/audit.py`) - Audit trail for security-sensitive operations

#### Features
- **JWT Authentication** - HS256 tokens via python-jose, configurable expiration (default 24hr)
- **Password Hashing** - bcrypt with automatic salting
- **Feature Flag** - `REQUIRE_AUTH=False` allows backwards-compatible gradual rollout
- **Auth Dependencies** - `get_current_user` (401), `get_optional_user` (None if no auth), `require_admin` (403)
- **Resource Ownership** - `owner_id` FK on ChatSession, DatabaseConnection, FileSource, QueryHistory, MigrationProject
- **Per-User Rate Limiting** - JWT-based user ID extraction in middleware, IP fallback for unauthenticated
- **Audit Logging** - Never-raising `log_action()` for create/delete/login events
- **61 tests** across 4 test files (auth, ownership, rate limiting, audit)

### Auth Hardening (Phase 24.8 - April 2026)
**Status**: PRODUCTION-READY (Phases A / B / C / D1 / D3 shipped behind toggles; D2 deferred — needs Redis)

Every behavior below defaults OFF; operators flip flags in `.env` / `.env.docker` per deployment posture. The Admin → Health → "Auth hardening" panel renders the live state of each flag.

#### Phase A — Token Versioning
- New `users.password_version INTEGER` (alembic `4f9a1c8b2e3d`); incremented by `bump_password_version(user)` helper.
- `AuthService.create_access_token()` stamps a `pv` JWT claim **only** when `AUTH_TOKEN_VERSIONING_ENABLED=True`.
- `get_current_user` rejects tokens whose `pv` doesn't match the user's current value (legacy tokens with no `pv` are accepted so flipping the flag is non-destructive).
- Bumps fire on `change-password`, admin reset, optionally on logout (`AUTH_INVALIDATE_TOKENS_ON_LOGOUT`) and deactivate (`AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE`).
- `change-password` returns a fresh `TokenResponse` so the caller stays signed in while every other device they were on is evicted.

#### Phase B — Rate Limit + Login Lockout
- `_UserKeyedRateLimiter` (in-process, sliding window) — `change_password_rate_limiter` singleton, gate `enforce_change_password_limit()`. Configurable via `AUTH_RATE_LIMIT_CHANGE_PASSWORD` + `AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE`.
- `LoginAttemptTracker` keyed by lowercase username (case-insensitive so casing can't dodge it; unknown usernames count too to defeat enumeration via lockout-vs-401). Configurable via `AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED`, `AUTH_LOGIN_LOCKOUT_THRESHOLD`, `AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS`.
- `account_locked` and `account_unlocked` audit events. In-process trackers are per-uvicorn-worker; multi-worker deployments swap in a Redis backend.

#### Phase C — One-Shot Password Reset Tokens
- New `password_reset_tokens` table (alembic `5e2b7a9d4c8f`). Plaintext token never persisted — only the bcrypt hash.
- `AUTH_PASSWORD_RESET_MODE` 3-way switch: `temp_password` (default; current behavior), `reset_token` (returns redemption URL with TTL), `both` (transition mode).
- `POST /api/auth/redeem-reset` is unauthenticated by design (the token IS the credential), bcrypt-walks outstanding tokens, marks `used_at`, rotates the password, returns a fresh `TokenResponse`. Generic 401 on unknown / expired / used / inactive-user to defeat enumeration.
- Frontend `/reset?token=…` route short-circuits the rest of the gating (auth + forced-change) until the user redeems or cancels.

#### Phase D1 — Password History
- New `password_history` table (alembic `6a3c5f8e7b1d`). Stores bcrypt hashes only; trimmed on every insert to keep the table bounded.
- `check_password_history()` rejects reuse against current + last `AUTH_PASSWORD_HISTORY_DEPTH` hashes (0 = disabled). Wired into `change-password` and `redeem-reset`; redeem rolls back so the token isn't burned on a recoverable input error.

#### Phase D3 — Admin Quorum
- `count_active_admins()` + `_enforce_admin_quorum()` helper. When `AUTH_REQUIRE_ADMIN_QUORUM=True`, refuses any change that would drop the active-admin count to 0 (PATCH role/active toggle and DELETE soft-deactivate). Layered with the existing self-edit protection.

#### Phase D2 — JWT JTI Denylist (DEFERRED)
Phase A's `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` covers the coarse "log me out everywhere" case via `password_version` bump. D2 only matters when per-session revocation matters AND the version-bump approach is too coarse. Slot in once Redis is in the standard deploy story (Phase 23 `full` profile).

#### Settings + Validation
13 new `AUTH_*` flags in `Settings`. `Settings.check_auth_hardening()` runs at startup (called from `src/main.py` lifespan, alongside `check_jwt_secret()`) — typo'd `AUTH_PASSWORD_RESET_MODE` raises before serving traffic; missing `AUTH_PASSWORD_RESET_BASE_URL` warns when reset mode requires it.

**44 new tests** across `test_auth_change_password.py` (4), `test_auth_token_versioning.py` (7), `test_auth_rate_limit.py` (8), `test_auth_reset_tokens.py` (9), `test_auth_history_and_quorum.py` (9), `test_settings_auth_hardening.py` (7).

## File Data Source System (Phase 13 - January 2026)
**Status**: PRODUCTION-READY

### Components
- `FileSourceHandler` (`src/core/file_source_handler.py`) - File validation, saving, and schema inference
- `FileSourceDuckDBSession` (`src/core/file_source_session.py`) - Singleton in-memory DuckDB session manager
- `files.py` (`src/api/endpoints/files.py`) - REST API endpoints for file management

### Features
- **File Upload Support** - CSV, XLSX, XLS files up to 100MB
- **Automatic Schema Inference** - DuckDB auto-detects column types (INTEGER, DOUBLE, VARCHAR, DATE, etc.)
- **Content Deduplication** - SHA-256 hashing prevents duplicate file storage
- **Lazy Table Loading** - DuckDB tables only created when first queried
- **Thread Safety** - AsyncIO locks protect concurrent access to DuckDB session
- **Memory Management** - Configurable memory limit (1GB default) and thread count (4)
- **Session Scoping** - Files can be session-specific or global (shared)
- **Auto-Cleanup** - Automatic file deletion after configurable days (30 default)
- **Security** - Filename sanitization, path traversal protection, content validation via magic bytes

### File Storage Structure
```
uploads/
├── global/           # Shared files (is_global=true)
│   └── {hash}_{filename}
└── sessions/
    └── {session_id}/  # Session-scoped files
        └── {hash}_{filename}
```

### DuckDB Table Naming
- Format: `file_{id}_{sanitized_name}`
- Example: `file_1_sales_data`, `file_3_revenue_2024`
- Max length: 40 characters
- Special characters removed for SQL compatibility

### Integration with Multi-Database Queries
- File sources automatically added to combined schema for LLM context
- Query planning considers both database and file sources
- DuckDB session ensures all file tables are loaded before query execution

## LLM Provider Expansion (Phase 15 - April 2026)
**Status**: PRODUCTION-READY

### Architecture
- `BaseLLMProvider` ABC — common interface for all providers (`generate()`, `chat()`, `health_check()`, `list_models()`)
- `DataLocality` enum — `LOCAL`, `CLOUD_PRIVATE`, `CLOUD_PUBLIC` classification per provider
- `ProviderRegistry` — central lookup with data security enforcement (`DATA_SECURITY_LEVEL` setting)
- `TrackedLLMClient` — wraps any provider with LLM usage tracking (backward-compatible with OllamaClient signature)
- `get_llm_client()` — factory function, replaces `get_ollama_client()` across all callers

### Provider Hierarchy
```
BaseLLMProvider (ABC)
├── OllamaProvider (LOCAL)
├── OpenAICompatibleProvider (httpx)
│   ├── OpenAIProvider (CLOUD_PUBLIC)
│   ├── LMStudioProvider (LOCAL)
│   └── VLLMProvider (LOCAL)
├── AzureOpenAIProvider (CLOUD_PRIVATE)
├── AnthropicProvider (CLOUD_PUBLIC)
├── GoogleVertexProvider (CLOUD_PRIVATE)
└── AWSBedrockProvider (CLOUD_PRIVATE)
```

### Data Security Enforcement
- **`DATA_SECURITY_LEVEL`** setting: `local_only` (default), `cloud_private`, `unrestricted`
- Registry blocks provider access when locality exceeds security level
- Fallback chains never "fall up" to a less-secure tier
- Frontend shows confirmation dialog for Frontier mode, amber/red warnings per locality
- Test endpoint uses synthetic prompt — never sends real schema data

### Provider Configuration
- `LLMProviderConfig` DB table — stores encrypted API keys (Fernet), endpoints, models
- `LLMTaskRouting` DB table — per-task provider routing overrides
- Env vars take priority over DB config (resolution: env > database > default)
- `ProviderConfigService` handles CRUD with encryption/decryption

### Model Router Integration
- `ModelRouter.get_provider_for_task()` — looks up configured provider per task type
- `ModelRouter.execute_with_fallback()` — tries primary provider, then fallback chain
- `TaskConfig` dataclass extended with `provider` and `fallback_chain` fields

## LLM Usage Monitoring (Phase 16 - February 2026)
**Status**: PRODUCTION-READY

### Components
- `LLMUsageTracker` (`src/services/llm_usage_tracker.py`) - Centralized tracking service
- `LLMCostService` (`src/services/llm_cost_service.py`) - Model config and cost calculation
- `LLMUsageAggregator` (`src/services/llm_usage_aggregator.py`) - Pre-computed statistics

### Features
- **Context Manager API** - `async with tracker.track_call(...)` wraps any LLM call transparently
- **Token Estimation** - tiktoken (cl100k_base) encoder with character-count fallback
- **Native Token Counts** - Extracts actual counts from Ollama, OpenAI, Anthropic, Azure responses
- **Cost Calculation** - Per-model pricing with configurable rates per 1M tokens
- **Pre-computed Aggregates** - Hourly/daily rollups by agent, provider, and model
- **Per-Session Tracking** - Links usage to chat sessions and query history
- **Error Tracking** - Records failed calls with error messages
- **9 REST API Endpoints** - Stats, breakdowns by agent/model/provider, timeseries, session usage
- **Frontend Dashboard** - Full monitoring UI with charts, stat cards, and recent call log
- **Session Usage Badge** - Inline token/cost display in chat header
- **Session Usage Summary** - Expandable agent breakdown per chat session

### Tracked Agents
All LLM-calling agents are instrumented:
- SQL Generator (via `TrackedLLMClient`)
- Self-Correcting Agent
- Query Planning Agent
- Result Narrator
- Lineage Narrator, Impact Advisor, Schema Health Analyzer
- Pattern Intelligence, Lineage Conversation Agent

## Data Insights Enhancement (Phase 19 - February 2026)
**Status**: PRODUCTION-READY

### Components
- `narrative_tiers.py` (`src/llm/prompts/narrative_tiers.py`) - Tiered prompt templates by model size
- `AnalyticsCache` (`src/services/analytics_cache.py`) - Two-tier statistics/pattern cache
- `ResultNarrator` (`src/llm/result_narrator.py`) - Enhanced with quality metrics and parallel pipeline

### Features
- **Tiered Narratives** (19.1) - Compact/Standard/Enhanced prompts auto-selected by model size (SMALL/MEDIUM/LARGE). Token budgets and sample row limits scale with tier. 40% token savings for small models
- **Analytics Caching** (19.2) - Local TTLCache (1hr) + optional Redis (24hr). Caches computed statistics and pattern detection results keyed by result-set hash. Singleton via `get_analytics_cache()`
- **Multi-Source Quality** (19.3) - `DataQualityMetrics` per database (null rates, completeness, duplicates, freshness). `GapInsight` detects coverage gaps across databases. `MultiSourceQualityReport` formats summary for LLM prompt (enhanced tier only)
- **Chart Intelligence** (19.4) - Frontend `ScoringPreset` system (default/business/scientific) adjusts chart type weights. `scoreColumnInterest()` ranks Y-axis candidates by variance and semantic value. Context-aware insight ordering based on user question
- **Parallel Analysis** (19.5) - `asyncio.gather` runs stats/anomalies/correlations in parallel for >=10 rows. Early exit for <=3 rows (skip LLM, use `_fallback_narrative`). `return_exceptions=True` for graceful degradation

### Configuration
- `ANALYTICS_CACHE_MAXSIZE` - Local cache max entries (default: 100)
- `ANALYTICS_CACHE_TTL` - Local cache TTL in seconds (default: 3600)
- `ANALYTICS_CACHE_REDIS_TTL` - Redis cache TTL in seconds (default: 86400)

## Database Schema

The system maintains its own metadata database (`database_guru.db`):

### Key Tables
| Table | Purpose |
|-------|---------|
| `database_connections` | User database connection configs |
| `query_history` | All executed queries with results |
| `chat_sessions` | Conversation sessions with context |
| `file_sources` | Uploaded CSV/Excel file metadata (Phase 13) |
| `learned_corrections` | Patterns learned from successful fixes |
| `confidence_scores` | Historical confidence predictions |
| `user_feedback` | User-submitted corrections and reports |
| `system_settings` | Configuration for auto-learning, validation, per-task model settings |
| `column_mappings` | Learned column name corrections |
| `table_mappings` | Learned table name corrections |
| `result_validation_patterns` | Learned result validation patterns |
| `llm_usage` | Individual LLM API call records with tokens, cost, timing (Phase 16) |
| `llm_usage_aggregate` | Pre-computed hourly/daily usage statistics (Phase 16) |
| `llm_model_config` | Model metadata, capabilities, and cost rates (Phase 16) |
| `users` | User accounts for JWT authentication (Phase 21); adds `must_change_password` and `password_version` columns in Phase 24.8 |
| `audit_logs` | Security audit trail — actions, resources, IP addresses (Phase 21); Phase 24.8 adds `password_change`, `password_change_failed`, `password_reset_redeemed`, `password_reset_redeem_failed`, `account_locked`, `account_unlocked` actions |
| `password_reset_tokens` | One-shot, TTL-bounded password reset tokens (Phase 24.8 — Phase C). Stores bcrypt hashes only; `used_at` marks single-use redemption |
| `password_history` | Bcrypt hashes of a user's previous passwords (Phase 24.8 — Phase D1). Trimmed to `AUTH_PASSWORD_HISTORY_DEPTH` rows on insert; consulted by change-password / redeem-reset to block reuse |
| `connection_write_permissions` | Per-connection DML permissions (INSERT/UPDATE/DELETE toggles, allowed tables, row limits) (Phase 18) |
