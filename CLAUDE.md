# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Database Guru is an AI-powered natural language to SQL query assistant. Users ask questions in plain English, and the system generates, executes, and self-corrects SQL queries using local LLMs via Ollama.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy 2.0 (async) + Python 3.11+
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- LLM: Ollama (local, primarily qwen2.5-coder:32b)
- Databases: SQLite for metadata, supports PostgreSQL/MySQL/SQLite/MongoDB/DuckDB for user databases

## Development Commands
After Completing a task that involves tool use, provide a quick summary of the work you've done.
### Backend Development

```bash
# Activate virtual environment
source venv/bin/activate

# Start backend server (with hot reload)
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
./run_tests.sh

# Run specific test file
./run_tests.sh tests/test_confidence_scorer.py

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Run specific test by name
python -m pytest tests/test_confidence_scorer.py::test_error_type_scoring -v

# Create sample database
python scripts/create_sample_db.py
```

### Frontend Development

```bash
# Start frontend dev server (with hot reload)
cd frontend
npm run dev

# Run tests
npm test

# Run tests in UI mode
npm run test:ui

# Build for production
npm run build

# Lint
npm run lint
```

### System Startup

```bash
# One-command startup (recommended)
chmod +x start.sh
./start.sh

# Stop all services
./stop.sh

# Ensure Ollama is running
ollama serve
# Or: brew services start ollama
```

## Architecture Overview

### Core Agent System

The system uses a multi-agent architecture with specialized agents that work together:

1. **Self-Correcting Agent** (`src/llm/self_correcting_agent.py`) **PRODUCTION-READY - November 8, 2025**
   - Main orchestrator for query processing
   - Handles retry logic with automatic error recovery
   - **Parallel correction attempts (PRODUCTION-READY)**: 1.6x speedup with timeout protection
     - Tries quick fix, learned, and LLM strategies simultaneously
     - 10-second configurable timeout prevents hanging
     - Comprehensive metrics tracking (winning strategy, success rates)
     - Smart fallback on timeout
   - Integrates all other agents and components
   - Uses `AgentTrace` for execution transparency
   - Key methods: `process_query()`, `_try_parallel_fixes()` - parallel error correction with metrics

2. **Conversational Memory Agent** (`src/llm/conversational_memory_agent.py`)
   - Manages conversation context for multi-turn dialogs
   - Retrieves recent queries from chat session history
   - Builds context-aware prompts with conversation history
   - Smart detection of contextual vs standalone questions (SECURITY FIXED: only triggers on question start)
   - **Production-grade security**: Uses `create_safe_context_prompt()` with prompt injection protection
   - Default 3-query window (configurable)
   - Key methods: `get_context()`, `build_context_prompt()`, `should_use_context()`

3. **Query Planning Agent** (`src/llm/query_planning_agent.py`)
   - Chain-of-thought reasoning for complex queries
   - Creates structured execution plans before SQL generation
   - Validates schema references and suggests corrections
   - 4x better accuracy on multi-table queries
   - Key method: `create_plan()` - generates `QueryPlan` dataclass

4. **Confidence Scorer** (`src/llm/confidence_scorer.py`)
   - Predicts success probability of SQL corrections (0.0-1.0)
   - 5 weighted factors: error type (30%), schema match (25%), historical success (20%), complexity (15%), similarity (10%)
   - Auto-skips corrections below 20% confidence
   - Key method: `score_correction()` - returns `ConfidenceScore` dataclass

5. **Result Verification Agent** (`src/llm/result_verification_agent.py`)
   - Validates query results for logical correctness
   - Detects empty results, NULL values, extreme values, suspicious counts
   - Triggers re-generation on high-confidence issues
   - Key method: `verify_result()` - returns `VerificationResult`

6. **Correction Learner** (`src/llm/correction_learner.py`)
   - Learns from successful corrections for instant future fixes
   - 50% faster recovery on repeated errors
   - Pattern-based matching with fuzzy similarity
   - Key methods: `learn_correction()`, `try_apply_learned_fix()`

7. **Schema-Aware Fixer** (`src/llm/schema_aware_fixer.py`)
   - Fast typo correction without LLM calls (200x faster)
   - Uses fuzzy matching against actual schema
   - Handles table names, column names, and common SQL errors
   - Key method: `try_quick_fix()` - returns corrected SQL or None

8. **Prompt Sanitizer** (`src/security/prompt_sanitizer.py`)
   - Multi-layer prompt injection protection
   - Input sanitization (removes control chars, normalizes whitespace)
   - Injection detection (15+ attack patterns blocked)
   - Safe prompt construction with XML-like delimiters
   - Token limits (500 chars for questions, 8000 for prompts)
   - Defense in depth: API → Agent → Prompt layers
   - Key methods: `sanitize_input()`, `detect_injection_attempts()`, `create_safe_context_prompt()`

9. **Multi-Database Handler** (`src/core/multi_db_handler.py`) **PRODUCTION-READY - November 8, 2025**
   - **Parallel multi-database execution (PRODUCTION-READY)**: 3x speedup with intelligent throttling
     - Queries execute simultaneously across multiple databases
     - Intelligent throttling (max 10 concurrent databases, configurable)
     - Dual timeout protection (35-second timeout prevents hanging)
     - Comprehensive metrics (speedup calculation, concurrency tracking, success rates)
   - Handles both async (PostgreSQL, MySQL, SQLite) and sync (DuckDB) sessions
   - Parallel schema introspection with `asyncio.gather()`
   - Graceful degradation: one database failure doesn't stop others
   - Key methods: `build_combined_schema()`, `execute_multi_database_query()`, `execute_with_semaphore()`

10. **Tool-Using Agent** (`src/llm/tool_using_agent.py`) **NEW - November 21, 2025**
    - Enhances SQL generation by gathering schema context before query generation
    - Analyzes user questions and automatically plans tool calls
    - Executes tools to explore schema and sample data
    - Builds enriched context for better first-attempt accuracy
    - Calculates confidence scores based on tool results
    - Key methods: `analyze_question()`, `execute_tools()`, `build_context()`

11. **Tool Registry** (`src/tools/tool_registry.py`)
    - Central registry for all available tools with caching support
    - Follows ColumnMapper pattern, uses MappingCache for performance
    - Manages tool definitions, categories, and execution metrics
    - Tracks execution statistics (times_executed, success_rate, cache_hit_rate)
    - Key methods: `register_tool()`, `get_tool()`, `get_tools_by_category()`, `invalidate_cache()`

12. **Result Narrator Agent** (`src/llm/result_narrator.py`) **NEW - December 13, 2025** (Updated Dec 24, 2025)
    - Generates human-readable narratives from query results with advanced analysis
    - Transforms raw data into contextual insights highlighting patterns and anomalies
    - **Core Features**: Summary (1-2 sentences), Key Insights (3-5 bullets), Direct Answer, Confidence Score (0.0-1.0), Statistics extraction
    - **Advanced Features** (all optional, never block):
      - Anomaly Detection: Z-score outlier detection (|z| ≥ 1.95 threshold)
      - Comparative Analysis: Compares results to historical similar queries
      - Trend Detection: Linear regression on temporal columns (R² ≥ 0.3)
      - Correlation Analysis: Pearson correlation between numeric columns (|r| > 0.7, minimum 10 rows)
    - **Performance**: <3 seconds for all features (99th percentile), <500ms for small datasets
    - **Graceful Degradation**: All advanced features wrapped in try-except, fallback to basic statistics if LLM fails
    - **Robust JSON Parsing** (Dec 24, 2025): Balanced brace extraction, JSON fragment filtering, handles malformed LLM output
    - **Configurable**: Enable/disable via UI toggle, `NARRATIVE_TIMEOUT_SECONDS` (default: 15s)
    - **Model Compatibility**: Works best with `gemma3:27b`; `llama3.2:latest` may produce malformed JSON (handled gracefully)
    - **Test Coverage**: 52 unit tests + 11 performance tests + 12 E2E tests (75 total)
    - Key methods: `generate_narrative()`, `_extract_json_object()`, `_detect_anomalies()`, `_detect_trends()`, `_calculate_correlations()`

13. **Model Router** (`src/llm/model_router.py`) **NEW - January 2, 2026**
    - Routes LLM tasks to appropriate models based on task type and user configuration
    - Enables using specialized models (e.g., `duckdb-nsql` for SQL) while using general-purpose models for other tasks
    - **Per-Task Model Configuration**: Assign different models for:
      - SQL Generation: Use specialized SQL models (duckdb-nsql, sqlcoder)
      - Narratives: Use general-purpose models (llama3.2, gemma)
      - Query Planning: Use reasoning-capable models
      - Error Correction: Use code-focused models
    - **Per-Task Timeouts**: Configurable timeout per task type (SQL: 30s, Narratives: 15s, Planning: 20s, Correction: 15s)
    - Falls back to default model when per-task model is not configured
    - Key methods: `get_model_for_task()`, `get_timeout_for_task()`, `get_config_for_task()`

14. **Query Template Engine** (`src/llm/query_templates.py`) **NEW - January 2, 2026** (Updated January 10, 2026)
    - Template-based SQL generation that bypasses LLM for simple query patterns
    - Improves response time and reduces errors for straightforward requests
    - **Supported Patterns**:
      - `list_all`: "show all products" → `SELECT * FROM products LIMIT 100`
      - `count`: "how many customers" → `SELECT COUNT(*) FROM customers`
      - `top_n`: "top 5 by price" → `SELECT * FROM X ORDER BY Y DESC LIMIT 5`
      - `filter_location`: "orders from California" → `SELECT * FROM orders WHERE state = 'CA'`
      - `filter_value`: "customers where status is active" → `SELECT * FROM customers WHERE status = 'active'`
      - `filter_date`: "orders from last 7 days" → Dialect-specific date math (NEW)
      - `search`: "find products containing 'widget'" → Dialect-specific case-insensitive search (NEW)
      - `sum_total`, `average`, `group_by`: Aggregation patterns
    - Table alias handling (singular/plural, abbreviations)
    - Column variation matching (price → unit_price, name → product_name)
    - **Dialect-aware SQL generation (NEW - Jan 10, 2026)**: Uses `DialectRegistry` for database-specific syntax
    - Returns `TemplateMatch` with SQL, confidence score, explanation, and `dialect_used`
    - Key method: `try_match()` - returns `TemplateMatch` or None

15. **Dialect Registry** (`src/llm/dialect_registry.py`) **NEW - January 10, 2026**
    - Defines database-specific SQL syntax rules for cross-database compatibility
    - **Supported Dialects**: PostgreSQL, MySQL, SQLite, DuckDB (MongoDB placeholder for MQL)
    - **DialectRules dataclass** covers:
      - Date/Time functions: `CURRENT_TIMESTAMP`, `NOW()`, `datetime('now')`
      - Date math: `INTERVAL '7 days'`, `DATE_SUB()`, `datetime('now', '-7 days')`
      - String functions: `ILIKE` vs `LOWER() LIKE`, `CONCAT` vs `||`
      - Boolean handling: `TRUE/FALSE` vs `1/0`
      - NULL handling: `IS NOT DISTINCT FROM`, `<=>`, `IS`
      - JSON/Array support: Database-specific operators
    - `build_dialect_context()` - Generates dialect-specific instructions for LLM prompts
    - `get_dialect_for_database_type()` - Maps connection string to `DatabaseDialect` enum
    - Key classes: `DatabaseDialect`, `DialectRules`, `DIALECT_RULES`

16. **Query Preprocessor** (`src/llm/query_preprocessor.py`) **NEW - January 2, 2026**
    - Pre-processes natural language queries before LLM generation
    - **Bidirectional Location Normalization**: Detects DB format and converts accordingly
      - If DB uses codes (CA, NY): "California" → "CA"
      - If DB uses full names: "CA" → "California"
      - Works for US states, cities, countries
    - **Entity Detection**: Extracts tables, columns, and values from questions
    - **Schema Validation**: Early detection of impossible queries
    - **Enhanced Context**: Builds LLM hints with matched entities and format guidance
    - Key method: `preprocess()` - returns `PreprocessedQuery` with normalized question and metadata

17. **Multi-Database Query Validator** (`src/llm/multi_db_query_validator.py`) **NEW - January 7, 2026**
    - Pre-flight validation for multi-database queries before execution
    - Assesses each database's capability to answer a query: FULL / PARTIAL / CANNOT
    - **SQL Parsing**: Uses `sqlparse` library for production-grade parsing
      - Handles schema-qualified names (`public.orders` → `orders`)
      - Extracts tables from JOINs, comma-separated FROM, aliases
      - Layered fallback: sqlparse → regex for robustness
    - **Location Detection**: Detects location-based queries, validates location columns across ALL tables
    - **Fuzzy Matching**: Finds alternative columns for missing ones (`state` → `region`, `province`)
    - **Suggested SQL**: Generates modified SQL for PARTIAL capability databases
    - **UI Integration**: Works with `SchemaGlance`, `MultiDatabaseAssessment`, `QueryFeasibilityBadge` components
    - Key classes: `QueryCapability`, `DatabaseQueryAssessment`, `MultiDatabaseValidationResult`
    - Key methods: `validate_query()`, `assess_database()`, `_extract_requirements()`
    - Test coverage: 27 tests in `tests/test_multi_db_query_validator.py`

18. **Prompt Optimizer** (`src/llm/prompt_optimizer.py`) **NEW - January 11, 2026**
    - Optimizes prompts for smaller LLM models by compressing schema and selecting relevant examples
    - **Model Size Detection**: Auto-detects model size from name patterns (e.g., "7b" → MEDIUM)
      - SMALL: <7B params, 2K context budget
      - MEDIUM: 7-13B params, 4K context budget
      - LARGE: 13B+ params, 8K+ context budget
    - **Model Family Support**: 7 families with specific prompt templates
      - Llama, Qwen, Gemma, Mistral, Phi, DuckDB-NSQL, SQLCoder
    - **Schema Compression**: Includes only relevant tables based on question keywords and FK relationships
    - **Smart Example Selection**: Chooses relevant few-shot examples based on query similarity
    - **Token Budgeting**: Allocates tokens across system prompt, schema, examples, and user input
    - **Safety Margin**: 20% buffer on token counting for SQL/code tokenization differences
    - **User Toggle**: OFF by default, enabled via Settings UI
    - Key methods: `optimize_prompt()`, `compress_schema()`, `select_examples()`
    - Key classes: `PromptBudget`, `ModelPromptTemplate`, `OptimizedPrompt`, `ModelSize`, `ModelFamily`
    - Test coverage: 52 tests in `tests/test_prompt_optimizer.py`

### Tool System (`src/tools/`)

The tool system provides 10 specialized tools across 4 categories for schema exploration and query validation:

**Schema Tools** (`src/tools/schema_tools.py`):
- `search_schema` - Search tables/columns by keyword with fuzzy matching
- `get_table_info` - Get detailed table information including columns, PKs, relationships
- `find_columns` - Find columns across all tables
- `get_relationships` - Get foreign key relationships and join suggestions

**Data Tools** (`src/tools/data_tools.py`):
- `get_sample_data` - Sample rows from tables (max 20 rows)
- `get_column_values` - Get distinct column values (essential for 'CA' vs 'California')
- `count_rows` - Count rows with optional WHERE filter (has SQL injection protection)

**Query Tools** (`src/tools/query_tools.py`):
- `test_query` - Test SQL syntax validity using EXPLAIN
- `validate_sql` - Validate SQL references against schema with fuzzy suggestions
- `explain_query` - Get query execution plan

### Data Flow

```
Natural Language Query (with optional session_id)
  ↓
Input Sanitization (Prompt Sanitizer) → Removes control chars, checks token limits
  ↓
Injection Detection → Blocks 15+ attack patterns
  ↓
Conversational Memory Agent → Retrieves conversation history (if session_id provided)
  ↓                          → Builds secure context-aware prompt with safe delimiters
  ↓
Tool-Using Agent → Analyzes question, executes schema/data tools **NEW - Nov 21, 2025**
  ↓              → Builds enriched context (table info, sample data, column values)
  ↓
Query Planning Agent → Creates structured plan with schema validation
  ↓
SQL Generator → Generates SQL from validated plan (with enriched context)
  ↓
Confidence Scorer → Predicts success probability
  ↓
SQL Executor → Executes with timeout/safety limits
  ↓
Result Verification Agent → Validates logical correctness
  ↓
[If Error] → **Parallel Correction Attempts** (quick fix + learned + LLM + tool_using, 4 strategies)
  ↓
[If Success] → Learn correction pattern for future
  ↓                          → Save to chat history (if session_id provided)
  ↓
Return Results
```

### Key Architectural Patterns

**Multi-Database Support with Parallel Execution (PRODUCTION-READY):**
- `UserDatabaseConnector` (`src/core/user_db_connector.py`) - Creates connections to user databases
- `MultiDatabaseHandler` (`src/core/multi_db_handler.py`) - **Parallel queries across multiple databases (3x speedup)**
  - **Intelligent throttling** - Semaphore-based concurrency control (max 10 databases)
  - **Dual timeout protection** - 35-second timeout prevents hanging queries
  - **Comprehensive metrics** - Speedup calculation, concurrency tracking, success rates
- **Parallel schema introspection** - All databases introspected simultaneously with `asyncio.gather()`
- **Parallel query execution** - Multiple queries execute concurrently across databases
- Supports both sync (DuckDB) and async (PostgreSQL, MySQL, SQLite) sessions
- Graceful degradation: one database failure doesn't stop others
- **Frontend observability** - ParallelDatabaseMetrics component with real-time visualization

**Connection Pooling (PRODUCTION-READY - December 6, 2025):**
- `ConnectionPoolManager` (`src/core/connection_pool_manager.py`) - **30x faster connection reuse**
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

**Schema Management:**
- `SchemaInspector` (`src/core/schema_inspector.py`) - Introspects database schemas
- `SchemaValidator` (`src/core/schema_validator.py`) - Validates table/column references with fuzzy matching
- `LocationMapper` (`src/core/location_mapper.py`) - Converts location names to database codes (e.g., "New York" → "NY")
- Schema sampling for value-aware validation

**Execution Safety:**
- `SQLExecutor` (`src/core/executor.py`) - Executes SQL with timeout protection and row limits
- Default: 1000 row limit, 30 second timeout
- Handles both async and sync database sessions
- Automatic truncation with warnings

**Caching & Performance:**
- Redis caching for query results (`src/cache/redis_client.py`)
- **Semantic Caching (NEW - November 22, 2025)**: Intelligent query similarity matching
  - `EmbeddingService` (`src/cache/embedding_service.py`) - Text embeddings using Ollama or TF-IDF fallback
  - `SemanticCache` (`src/cache/semantic_cache.py`) - Matches similar queries (30-50% higher cache hit rate)
  - `LLMCache` (`src/cache/llm_cache.py`) - Caches LLM SQL generation responses (40-60% fewer LLM calls)
  - Schema fingerprinting ensures cache validity across schema changes
  - Configurable similarity thresholds (default: 0.85 for semantic, 0.88 for LLM)
- **Conditional Result Verification** - Skips verification for high-confidence results (1-100 rows, first attempt)
- Rate limiting middleware (100 requests/60 seconds)
- Async operations throughout for concurrency

**User Feedback System:**
- Users can correct SQL/schema errors via UI
- `FeedbackValidator` (`src/llm/feedback_validator.py`) - Validates feedback before auto-learning
- 3 validation modes: strict (production), moderate (balanced), lenient (testing)
- Blocks destructive operations (DELETE, UPDATE, DROP) from auto-learning
- Comprehensive testing validates corrections actually improve results

**Learned Mapping System (NEW - November 10, 2025):**
- `ColumnMapper` (`src/llm/column_mapper.py`) - Learns and applies column name corrections
- `TableMapper` (`src/llm/table_mapper.py`) - Learns and applies table name corrections
- `ResultPatternLearner` (`src/llm/result_pattern_learner.py`) - Learns result validation patterns
- **Management API** (`src/api/endpoints/mappings.py`) - View, filter, and manage learned patterns
- **Filtering** - By connection_name, table_name, database_type, pattern_type, action
- **Statistics** - Usage counts, success rates, helpfulness ratings
- **Frontend Dashboard** - 5 components for browsing and managing mappings
- Auto-learns from non-SQL feedback types (column_name, table_name, result_issue)

**Security System (NEW - November 2, 2025):**
- `PromptSanitizer` (`src/security/prompt_sanitizer.py`) - Multi-layer prompt injection protection
- Input sanitization at API boundary (Pydantic validators)
- Injection detection (15+ attack patterns)
- Safe prompt construction with XML-like delimiters
- Token limits prevent resource exhaustion
- Security logging for monitoring
- 29 comprehensive security tests passing

### Database Schema

The system maintains its own metadata database (`database_guru.db`):

**Key Tables:**
- `database_connections` - User database connection configs
- `query_history` - All executed queries with results
- `chat_sessions` - Conversation sessions with context
- `learned_corrections` - Patterns learned from successful fixes
- `confidence_scores` - Historical confidence predictions
- `user_feedback` - User-submitted corrections and reports
- `system_settings` - Configuration for auto-learning, validation, and per-task model settings (NEW: model_sql_generation, model_narratives, model_query_planning, model_error_correction, per-task timeouts, enable_query_templates, enable_location_preprocessing)
- `column_mappings` - Learned column name corrections (NEW - Nov 10, 2025)
- `table_mappings` - Learned table name corrections (NEW - Nov 10, 2025)
- `result_validation_patterns` - Learned result validation patterns (NEW - Nov 10, 2025)

### API Structure

Endpoints organized by domain (`src/api/endpoints/`):
- `query.py` - Main query processing endpoint (supports session_id for conversational context)
- `multi_db_query.py` - Multi-database query handling
- `connections.py` - Database connection management
- `chat.py` - Chat session management + conversation context endpoints (GET/DELETE /sessions/{id}/context)
- `feedback.py` - User feedback submission and stats
- `learned_corrections.py` - View learned patterns
- `mappings.py` - **Mapping management API (NEW - Nov 10, 2025)** - View/manage column/table/pattern mappings
  - **10 endpoints total**: GET/DELETE for columns, tables, patterns + stats + helpful tracking
  - Advanced filtering by connection_name, table_name, database_type, pattern_type, action
  - Pagination support (limit/offset)
  - Statistics aggregation and analytics
- `result_verification.py` - Manual result verification
- `query_planning.py` - Query plan generation
- `confidence.py` - Confidence scoring API (if exists)
- `settings.py` - System settings and configuration
- `schema.py` - Schema introspection
- `models.py` - Available Ollama models
- `tools.py` - **Tool management API (NEW - Nov 21, 2025)** - Tool registry and execution
  - `GET /api/tools` - List available tools (filterable by category)
  - `GET /api/tools/stats` - Get execution statistics
  - `GET /api/tools/stats/{tool_name}` - Get stats for specific tool
  - `GET /api/tools/prompt` - Get tools formatted for LLM prompt
  - `POST /api/tools/{tool_name}/invalidate-cache` - Invalidate tool cache
  - `POST /api/tools/invalidate-all-cache` - Invalidate all tool caches
- `cache.py` - **Cache management API (NEW - Nov 22, 2025)** - Semantic cache monitoring and control
  - `GET /api/cache/stats` - Get combined cache statistics (semantic + LLM + embedding)
  - `GET /api/cache/semantic/recent` - Get recent cached queries with filtering
  - `DELETE /api/cache/semantic` - Clear semantic query cache
  - `DELETE /api/cache/llm` - Clear LLM response cache
  - `DELETE /api/cache/all` - Clear all caches
  - `DELETE /api/cache/semantic/connection/{id}` - Clear cache for specific connection

## Important Implementation Details

### Testing Strategy

- Use `pytest` with async support (`pytest-asyncio`)
- Mock database connections with in-memory SQLite
- Mock Ollama LLM responses for deterministic tests
- Separate unit tests (`tests/unit/`) from integration tests (`tests/`)
- Test markers: `@pytest.mark.asyncio`, `@pytest.mark.integration`, `@pytest.mark.slow`

**Common Test Patterns:**
```python
# Mock database session
@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

# Mock Ollama client
class MockOllamaClient:
    async def generate(self, model: str, prompt: str):
        return {"response": "SELECT * FROM test_table"}
```

### Frontend Component Structure

Located in `frontend/src/`:
- `components/` - React components (QueryInterface, ConnectionManager, ConfidenceDisplay, ConversationContextPanel, etc.)
- `services/` - API client (`api.ts`) using axios
- `hooks/` - Custom React hooks (`useQuery`, `useConnections`, etc.)
- `types/` - TypeScript type definitions (includes ConversationContext types)
- Uses TanStack Query for server state management
- Zustand for client state (if used)

**Learned Mapping Components (NEW - November 10, 2025):**
- `LearnedMappingsPanel.tsx` (+95 lines) - Main tabbed interface for browsing mappings
- `ColumnMappingsList.tsx` (+165 lines) - Column mappings with filtering and delete
- `TableMappingsList.tsx` (+170 lines) - Table mappings with filtering and delete
- `ResultPatternsList.tsx` (+195 lines) - Result patterns with helpfulness tracking
- `MappingStatsDisplay.tsx` (+315 lines) - Statistics dashboard with charts
- `mappingsApi.ts` (+155 lines) - API service layer for mapping endpoints
- Total: **1,095 lines** of new UI code for mapping management

**Tool-Using Agent UI Components (NEW - November 22, 2025):**
- `ToolsPanel.tsx` (~112 lines) - Main tabbed container with 3 views (Overview, Directory, Usage Stats)
- `ToolsOverview.tsx` (~271 lines) - Summary dashboard with stats cards, category breakdown, quick actions
- `ToolDirectory.tsx` (~237 lines) - Browsable tool list with filtering and expandable details
- `ToolUsageStats.tsx` (~277 lines) - Per-tool execution metrics with visual bars and sorting
- `toolsApi.ts` (~100 lines) - API service layer for tools endpoints (6 methods)
- **App.tsx** - Updated to include "Tools" as 4th main tab with orange color scheme
- Total: **~1,000 lines** of new UI code for Tool-Using Agent management
- Tests: `ToolsPanel.test.tsx` with 30 comprehensive tests

**Row Limit & Pagination Components (NEW - December 27, 2025):**
- `QueryInput.tsx` - Updated with row limit dropdown selector (10-10,000 rows)
- `QueryResults.tsx` - Added pagination with 10/25/50/100 rows per page, navigation controls
- `MultiDatabaseResults.tsx` - Per-database pagination with independent controls
- Tests: `QueryResults.test.tsx` with 10 new pagination tests, `MultiDatabaseResults.test.tsx` with 16 tests

**Semantic Cache UI Components (NEW - November 22, 2025):**
- `SemanticCachePanel.tsx` (~110 lines) - Main tabbed container with 3 views (Overview, Statistics, Recent)
- `CacheOverview.tsx` (~370 lines) - Summary dashboard with stats cards, cache breakdown, quick actions
- `CacheStatistics.tsx` (~270 lines) - Hit rate distribution charts, performance metrics
- `RecentCachedQueries.tsx` (~230 lines) - Browsable cached query list with expandable SQL
- `QueryResults.tsx` - Updated with inline cache badge (exact/semantic hit indicators)
- `cacheApi.ts` (~150 lines) - API service layer for cache endpoints (6 methods)
- **App.tsx** - Updated to include "Cache" as 5th main tab with amber color scheme
- Total: **~2,100 lines** of new UI code for Semantic Cache management
- Backend Tests: `test_cache_endpoints.py` with 9 tests
- Frontend Tests: `SemanticCachePanel.test.tsx` with 34 tests

**Small Model Optimization UI Components (NEW - January 2, 2026)** (Updated January 11, 2026):
- `ModelConfigPanel.tsx` (465 lines) - Per-task model configuration with:
  - 4 task cards: SQL Generation, Narratives, Query Planning, Error Correction
  - Model dropdown for each task (fetches from Ollama)
  - Timeout slider (5-120s) with default indicators
  - Optimization feature toggles: Query Templates, Location Preprocessing
  - **Prompt Optimization toggle (NEW - Jan 11, 2026)**: Schema compression, example selection, model size detection
    - Sub-options: Model size (auto/small/medium/large), Schema compression toggle, Max tables slider, Example selection toggle, Max examples slider
  - Color-coded task cards (blue, green, purple, orange)
- `SettingsPanel.tsx` - Updated to include ModelConfigPanel integration
- `QueryInput.tsx` - Row limit integration with per-task settings

### LLM Prompts

All prompts in `src/llm/prompts.py`:
- Structured with clear examples
- Include schema context and database-specific syntax
- Use few-shot learning patterns
- Chain-of-thought prompting for complex queries

### Error Handling

- Self-correcting agent retries up to 3 times
- Each retry uses different strategy: quick fix → learned patterns → LLM regeneration
- Graceful fallbacks when agents fail
- Detailed error messages with context
- All errors logged with structured logging

### Configuration

Settings managed via Pydantic in `src/config/settings.py`:
- Environment variables from `.env` file
- Type-safe configuration with validation
- Default values for all settings
- Supports multiple deployment environments

## Development Workflow

### Adding a New Feature

1. **Backend**: Add endpoint in `src/api/endpoints/`, use existing patterns for database access and LLM integration
2. **Database Models**: Add SQLAlchemy models in `src/database/models.py` if needed
3. **Schemas**: Add Pydantic schemas in `src/models/schemas.py` for request/response
4. **Tests**: Add tests in `tests/` following existing test structure
5. **Frontend**: Add/modify components in `frontend/src/components/`
6. **API Integration**: Update `frontend/src/services/api.ts`

### Debugging Tips

- Backend logs to console and `backend.log`
- Frontend logs to console and `frontend.log`
- Use `logger.info()` extensively for debugging agent decisions
- Check `AgentTrace` steps in API responses for execution details
- Use `/api/docs` (Swagger UI) for API testing
- Enable verbose logging: `logging.getLogger("src").setLevel(logging.DEBUG)`

### Common Issues

**Ollama Connection**: Ensure Ollama is running (`ollama serve`) and the correct model is pulled
**Port Conflicts**: Kill processes on ports 3000/8000 before starting
**Schema Issues**: Check database connection is active and schema introspection works
**Async/Sync Mixing**: DuckDB uses sync sessions, others use async - `SQLExecutor` handles both
**Import Cycles**: Avoid circular imports between agents by importing within functions if needed

## Key Code Locations

- **Main application entry**: `src/main.py:54` - FastAPI app initialization
- **Query processing flow**: `src/api/endpoints/query.py:32` - `/api/query/` endpoint
- **Conversational memory**: `src/llm/conversational_memory_agent.py` - Context retrieval and management
- **Context endpoints**: `src/api/endpoints/chat.py` - GET/DELETE context endpoints
- **Self-correction logic**: `src/llm/self_correcting_agent.py:541` - `generate_and_execute_with_retry()` method
- **Parallel corrections (PRODUCTION-READY)**: `src/llm/self_correcting_agent.py:373` - `_try_parallel_fixes()` method (1.6x speedup + timeout + metrics)
- **Confidence scoring**: `src/llm/confidence_scorer.py:147` - `score_correction()` method
- **Multi-DB queries (PRODUCTION-READY)**: `src/core/multi_db_handler.py:481` - `execute_multi_database_query()` method (3x speedup + throttling + timeout + metrics)
- **Parallel schema introspection**: `src/core/multi_db_handler.py:75` - `build_combined_schema()` with parallel execution
- **Parallel DB throttling**: `src/core/multi_db_handler.py:561` - `execute_with_semaphore()` - intelligent concurrency control with timeout
- **Schema validation**: `src/core/schema_validator.py` - `validate_schema_references()`
- **SQL execution**: `src/core/executor.py:42` - `execute_query()` with timeout handling
- **Security/Prompt Sanitization**: `src/security/prompt_sanitizer.py` - Input sanitization and injection detection
- **Security Tests**: `tests/test_prompt_sanitizer.py` - 29 comprehensive security tests
- **Parallel Multi-DB Tests (PRODUCTION-READY)**: `tests/test_parallel_multi_db.py` - 6 tests (3x speedup + timeout verification)
- **Parallel Corrections Tests (PRODUCTION-READY)**: `tests/test_parallel_corrections.py` - 7 tests (1.6x speedup + timeout + metrics verification)
- **Frontend Parallel Metrics**: `frontend/src/components/ParallelExecutionMetrics.tsx` - Real-time visualization (42 tests total)
- **Row Limit & Pagination (NEW - Dec 27, 2025)**:
  - `frontend/src/components/QueryInput.tsx` - Row limit dropdown (10-10,000 rows)
  - `frontend/src/components/QueryResults.tsx` - Table pagination with page size selector
  - `frontend/src/components/MultiDatabaseResults.tsx` - Per-database pagination controls
  - `src/models/schemas.py` - `row_limit` field in QueryRequest (1-10000, default 100)
  - `src/api/endpoints/query.py` - Passes row_limit to agent chain
  - `src/core/multi_db_handler.py` - Passes row_limit through multi-database execution
  - `frontend/tests/QueryResults.test.tsx` - 10 pagination tests
  - `frontend/tests/MultiDatabaseResults.test.tsx` - 16 pagination tests
- **Multi-Database Query Validation (NEW - Jan 7, 2026)**:
  - `src/llm/multi_db_query_validator.py` - Pre-flight validation with sqlparse (1061 lines)
  - `src/llm/multi_db_query_validator.py:289` - `_extract_requirements()` - SQL parsing with layered fallback
  - `src/llm/multi_db_query_validator.py:650` - `_extract_requirements_from_question()` - NL question analysis
  - `src/llm/multi_db_query_validator.py:767` - Location requirement validation
  - `src/api/endpoints/multi_db_query.py:662` - Pre-validation integration in API
  - `frontend/src/components/SchemaGlance.tsx` - Database schema overview (382 lines)
  - `frontend/src/components/MultiDatabaseAssessment.tsx` - Capability selection UI (264 lines)
  - `frontend/src/components/QueryFeasibilityBadge.tsx` - Status badges (194 lines)
  - `tests/test_multi_db_query_validator.py` - 27 comprehensive tests
- **Tool-Using Agent (NEW)**: `src/llm/tool_using_agent.py` - Schema exploration and context building for SQL generation
- **Tool Registry (NEW)**: `src/tools/tool_registry.py` - Central registry with caching (follows ColumnMapper pattern)
- **Schema Tools (NEW)**: `src/tools/schema_tools.py` - 4 tools for schema exploration (search_schema, get_table_info, find_columns, get_relationships)
- **Data Tools (NEW)**: `src/tools/data_tools.py` - 3 tools for data sampling (get_sample_data, get_column_values, count_rows)
- **Query Tools (NEW)**: `src/tools/query_tools.py` - 3 tools for query validation (test_query, validate_sql, explain_query)
- **Tools API (NEW)**: `src/api/endpoints/tools.py` - REST API for tool management (6 endpoints)
- **Tools Tests (NEW)**: `tests/test_tools.py` - 26 comprehensive tests for tool system
- **Tools UI Components (NEW)**: `frontend/src/components/ToolsPanel.tsx` - Main tabbed container for Tool-Using Agent
- **Tools UI Tests (NEW)**: `frontend/tests/ToolsPanel.test.tsx` - 30 comprehensive frontend tests
- **Tools API Service (NEW)**: `frontend/src/services/toolsApi.ts` - API service for tools endpoints
- **Semantic Caching (NEW - Nov 22, 2025)**:
  - `src/cache/embedding_service.py` - Text embeddings for similarity matching (Ollama or TF-IDF fallback)
  - `src/cache/semantic_cache.py` - Query result caching with semantic similarity
  - `src/cache/llm_cache.py` - LLM response caching with schema fingerprinting
  - `tests/test_semantic_caching.py` - 20 comprehensive tests for caching system
- **Result Narrator (NEW - Dec 13, 2025)**:
  - `src/llm/result_narrator.py` - Narrative generation with advanced analysis (anomalies, trends, correlations)
  - `src/llm/result_narrator.py:63` - `generate_narrative()` - Main entry point, orchestrates all analysis
  - `src/llm/result_narrator.py:346` - `_detect_anomalies()` - Z-score outlier detection
  - `src/llm/result_narrator.py:593` - `_detect_trends()` - Linear regression on temporal data
  - `src/llm/result_narrator.py:694` - `_calculate_correlations()` - Pearson correlation analysis
  - `frontend/src/components/ResultSummary.tsx` - Narrative display with anomaly/trend/correlation alerts
  - `frontend/src/components/ChatInterface.tsx` - Narratives enable/disable toggle
  - `tests/test_result_narrator.py` - 41 unit tests (core + advanced features)
  - `tests/test_performance_narratives.py` - 11 performance tests (<3s latency validation)
  - `tests/test_e2e_narratives.py` - 12 end-to-end tests (realistic query scenarios)
  - **NEW - Multi-Database Narratives (Dec 13, 2025)**:
    - `src/api/endpoints/multi_db_query.py` - Extended with narrative generation (lines 662-740)
    - `MultiDatabaseQueryRequest.enable_narratives` - Flag to enable narratives for multi-database queries
    - `DatabaseQueryResult.result_analysis` - Per-database narrative field
    - `MultiDatabaseQueryResponse.combined_analysis` - Synthesized narrative across all databases
    - Generates BOTH: per-database narratives + combined multi-database analysis
    - `tests/test_multi_db_narratives.py` - 10 comprehensive multi-database narrative tests
- **Semantic Cache UI (NEW - Nov 22, 2025)**:
  - `src/api/endpoints/cache.py` - REST API for cache management (6 endpoints)
  - `frontend/src/components/SemanticCachePanel.tsx` - Main tabbed container (Overview, Statistics, Recent)
  - `frontend/src/components/CacheOverview.tsx` - Stats dashboard with clear actions
  - `frontend/src/components/CacheStatistics.tsx` - Hit distribution and performance metrics
  - `frontend/src/components/RecentCachedQueries.tsx` - Cached query browser with SQL expand
  - `frontend/src/components/QueryResults.tsx` - Updated with inline cache badge
  - `frontend/src/services/cacheApi.ts` - API service for cache endpoints
  - `tests/test_cache_endpoints.py` - 9 backend tests
  - `frontend/tests/SemanticCachePanel.test.tsx` - 34 frontend tests
- **Connection Pooling (PRODUCTION-READY - Dec 6, 2025)**:
  - `src/core/connection_pool_manager.py` - Global singleton pool manager (489 lines, 30x speedup)
  - `src/core/user_db_connector.py` - Modified to use pools instead of creating engines
  - `src/api/endpoints/pools.py` - REST API for pool monitoring (4 endpoints, 240 lines)
  - `src/config/settings.py` - 10 pool configuration settings
  - `frontend/src/components/ConnectionPoolMetrics.tsx` - Real-time dashboard (435 lines)
  - `frontend/src/services/poolsApi.ts` - API service for pool endpoints (150 lines)
  - `tests/test_connection_pool_manager.py` - Unit tests (18 tests, 200 lines)
  - `tests/test_pooled_query_execution.py` - Integration tests (8 tests, 360 lines)
  - `tests/test_pooling_performance.py` - Performance tests (3 tests, 320 lines)
  - `tests/fixtures/docker-compose.test.yml` - Test database infrastructure (PostgreSQL, MySQL, MongoDB)
  - `scripts/setup_test_databases.sh` - One-command test database setup (180 lines)
- **Advanced Visualization (Phase 8 & 10 - Dec 20-26, 2025)**:
  - `frontend/src/utils/chartIntelligence.ts` - Pattern detection engine (~700 lines)
  - `frontend/src/utils/chartIntentParser.ts` - NL chart request parsing (~240 lines)
  - `frontend/src/utils/timeSeriesDetector.ts` - Periodic pattern detection (~180 lines)
  - `frontend/src/utils/hierarchyDetector.ts` - Parent-child data detection (~150 lines)
  - `frontend/src/utils/hierarchicalChartUtils.ts` - Treemap/Sunburst data prep (~300 lines)
  - `frontend/src/utils/statisticalChartUtils.ts` - Box plot/histogram calculations (~360 lines)
  - `frontend/src/components/visualization/TreemapView.tsx` - Treemap chart (~180 lines)
  - `frontend/src/components/visualization/SunburstView.tsx` - Radial hierarchy (~190 lines)
  - `frontend/src/components/visualization/HistogramView.tsx` - Distribution histogram (~190 lines)
  - `frontend/src/components/visualization/BoxPlotView.tsx` - Statistical box plot (~240 lines)
  - `frontend/src/components/visualization/AreaChartView.tsx` - Time-series area (~190 lines)
  - `frontend/src/components/visualization/BubbleChartView.tsx` - 3-variable scatter (~140 lines)
  - `frontend/src/components/visualization/ChartVisualization.tsx` - Main chart container
  - `frontend/src/components/visualization/ChartToggle.tsx` - Table/chart toggle with type selector
  - `frontend/tests/AdvancedCharts.test.tsx` - 61 comprehensive tests
  - `frontend/tests/chartIntelligence.test.ts` - Pattern detection tests
- **Small Model Optimization (NEW - Jan 2, 2026)** (Updated Jan 11, 2026):
  - `src/llm/model_router.py` - Per-task model routing (246 lines)
  - `src/llm/query_templates.py` - Template-based SQL for simple patterns (1024 lines, updated with dialect support)
  - `src/llm/dialect_registry.py` - Database dialect rules and SQL syntax (205 lines) **NEW - Jan 10, 2026**
  - `src/llm/query_preprocessor.py` - Location normalization and preprocessing (504 lines)
  - `src/llm/prompt_optimizer.py` - Prompt compression and schema optimization (1013 lines) **NEW - Jan 11, 2026**
  - `src/llm/quality_profile.py` - Added `enable_prompt_optimization` field **UPDATED - Jan 11, 2026**
  - `src/llm/self_correcting_agent.py` - Template matching + preprocessing integration (lines 821-907, 1068-1111)
  - `src/database/models.py` - Per-task model/timeout fields + prompt optimization settings in SystemSettings
  - `src/api/endpoints/settings.py` - Model configuration API endpoints
  - `src/api/endpoints/query.py` - Passes prompt optimization settings to QualityProfile
  - `src/api/endpoints/models.py` - Filter embedding models from model list
  - `frontend/src/components/ModelConfigPanel.tsx` - Per-task model configuration UI + prompt optimization toggle (465 lines)
  - `frontend/src/components/SettingsPanel.tsx` - Updated with ModelConfigPanel integration
  - `tests/test_model_router.py` - 220 lines of model router tests
  - `tests/test_query_preprocessor.py` - 264 lines of preprocessor tests
  - `tests/test_query_templates.py` - 510 lines of template engine tests (updated with dialect tests)
  - `tests/test_dialect_registry.py` - 72 lines of dialect registry tests **NEW - Jan 10, 2026**
  - `tests/test_prompt_optimizer.py` - 600 lines of prompt optimizer tests (52 tests) **NEW - Jan 11, 2026**

## Documentation

Key docs in `docs/`:

**Guides** (`docs/guides/`):
- `guides/AUTO_LEARNING_GUIDE.md` - User feedback and auto-learning
- `guides/MULTI_DATABASE_GUIDE.md` - Multi-database queries (UPDATED with production-ready parallel execution)
- `guides/CONNECTION_POOLING_GUIDE.md` - **Connection Pooling Guide (PRODUCTION-READY - Dec 6, 2025)** - Configuration, monitoring, performance tuning, troubleshooting
- `guides/TEST_DATABASE_SETUP.md` - **Test Database Setup Guide (Dec 6, 2025)** - Docker Compose test infrastructure setup and usage
- `guides/DATA_NARRATIVES_GUIDE.md` - **Intelligent Data Narratives & Human Insights (NEW - Dec 13, 2025)** - Complete feature guide
- `guides/MULTI_DB_VALIDATION_GUIDE.md` - **Multi-Database Validation Guide (NEW - Jan 7, 2026)** - Pre-flight validation architecture and API reference
- `guides/testing/TESTING.md` - Testing guide

**Technical** (`docs/technical/`):
- `technical/PARALLEL_EXECUTION.md` - **Parallel execution technical guide (PRODUCTION-READY - Nov 8, 2025!)** - Timeout protection, metrics, frontend integration
- `technical/CONVERSATIONAL_MEMORY_IMPLEMENTATION.md` - Conversational memory technical guide
- `technical/SECURITY_IMPROVEMENTS.md` - Recent security fixes and remaining issues
- `technical/CONFIDENCE_SCORING.md` - Confidence scoring system
- `technical/LEARNING_FROM_CORRECTIONS.md` - Correction learning system
- `technical/SECURITY_POLICY.md` - Security controls and validation
- `technical/SEMANTIC_CACHING.md` - **Semantic Caching guide (NEW - Nov 22, 2025)** - Phase 3.2 backend implementation
- `technical/SEMANTIC_CACHE_UI.md` - **Semantic Cache UI guide (NEW - Nov 22, 2025)** - Phase 3.3 frontend components
- `technical/MULTI_DB_NARRATIVES.md` - **Multi-Database Narratives (NEW - Dec 13, 2025)** - Per-database + combined analysis
- `technical/SQL_GENERATION_PIPELINE.md` - **SQL Generation Pipeline (UPDATED - Jan 7, 2026)** - Complete pipeline with Phase 2.4 multi-database validation

**Modules** (`docs/modules/`):
- `modules/QUERY_PLANNING_AGENT.md` - Query planning system deep dive
- `modules/RESULT_VERIFICATION_AGENT.md` - Result verification details
- `modules/TOOL_USING_AGENT.md` - **Tool-Using Agent guide (NEW - Nov 21, 2025)** - Phase 3.1 implementation

**Planning** (`docs/planning/`):
- `planning/FUTURE_PLANS.md` - Prioritized roadmap (UPDATED with production-ready parallel features - Nov 8, 2025!)
- `planning/CONNECTION_POOLING_IMPLEMENTATION_PLAN.md` - **5-day implementation plan (80% complete)** - Day 4 complete
- `planning/ADVANCED_VISUALIZATION_PHASE2_PLAN.md` - **Advanced Visualization Phase 2 (Dec 20-26, 2025)** - Chart Intelligence + Advanced Charts
- `planning/SEMANTIC_TYPE_INTELLIGENCE_PLAN.md` - **Semantic Type Intelligence Roadmap (NEW - Jan 8, 2026)** - Future plan for Date/Time, Status/Enum, Boolean intelligence

**Reports** (`docs/reports/`):
- `reports/CODE_REVIEW_PARALLEL_EXECUTION.md` - **Code review documentation (9.0/10 score)** - All critical & important issues resolved
- `reports/PHASE_1_COMPLETE.md` - Conversational memory completion summary
- `reports/TEST_CONVERSATIONAL_MEMORY.md` - Conversational memory testing guide
- `reports/SMALL_MODEL_OPTIMIZATION_PHASE_2_PR_REVIEW.md` - **Phase 2 PR Review (UPDATED - Jan 7, 2026)** - Code review with all issues resolved
