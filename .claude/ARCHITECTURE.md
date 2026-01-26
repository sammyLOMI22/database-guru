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

### Features
- Default: 1000 row limit, 30 second timeout
- Handles both async and sync database sessions
- Automatic truncation with warnings

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

## Security System (November 2, 2025)

### Components
- `PromptSanitizer` (`src/security/prompt_sanitizer.py`) - Multi-layer prompt injection protection

### Features
- Input sanitization at API boundary (Pydantic validators)
- Injection detection (15+ attack patterns)
- Safe prompt construction with XML-like delimiters
- Token limits prevent resource exhaustion
- Security logging for monitoring
- 29 comprehensive security tests passing

## Database Schema

The system maintains its own metadata database (`database_guru.db`):

### Key Tables
| Table | Purpose |
|-------|---------|
| `database_connections` | User database connection configs |
| `query_history` | All executed queries with results |
| `chat_sessions` | Conversation sessions with context |
| `learned_corrections` | Patterns learned from successful fixes |
| `confidence_scores` | Historical confidence predictions |
| `user_feedback` | User-submitted corrections and reports |
| `system_settings` | Configuration for auto-learning, validation, per-task model settings |
| `column_mappings` | Learned column name corrections |
| `table_mappings` | Learned table name corrections |
| `result_validation_patterns` | Learned result validation patterns |
