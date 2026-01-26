# Agent System Reference

Detailed documentation for all agents in the Database Guru system.

## Core Agents

### 1. Self-Correcting Agent
**File**: `src/llm/self_correcting_agent.py`
**Status**: PRODUCTION-READY (November 8, 2025)

Main orchestrator for query processing with:
- Retry logic with automatic error recovery
- **Parallel correction attempts**: 1.6x speedup with timeout protection
  - Tries quick fix, learned, and LLM strategies simultaneously
  - 10-second configurable timeout prevents hanging
  - Comprehensive metrics tracking (winning strategy, success rates)
  - Smart fallback on timeout
- Integrates all other agents and components
- Uses `AgentTrace` for execution transparency

**Key methods**: `process_query()`, `_try_parallel_fixes()`

### 2. Conversational Memory Agent
**File**: `src/llm/conversational_memory_agent.py`

- Manages conversation context for multi-turn dialogs
- Retrieves recent queries from chat session history
- Builds context-aware prompts with conversation history
- Smart detection of contextual vs standalone questions (SECURITY FIXED)
- **Production-grade security**: Uses `create_safe_context_prompt()` with prompt injection protection
- Default 3-query window (configurable)

**Key methods**: `get_context()`, `build_context_prompt()`, `should_use_context()`

### 3. Query Planning Agent
**File**: `src/llm/query_planning_agent.py`

- Chain-of-thought reasoning for complex queries
- Creates structured execution plans before SQL generation
- Validates schema references and suggests corrections
- 4x better accuracy on multi-table queries

**Key method**: `create_plan()` - generates `QueryPlan` dataclass

### 4. Confidence Scorer
**File**: `src/llm/confidence_scorer.py`

- Predicts success probability of SQL corrections (0.0-1.0)
- 5 weighted factors: error type (30%), schema match (25%), historical success (20%), complexity (15%), similarity (10%)
- Auto-skips corrections below 20% confidence

**Key method**: `score_correction()` - returns `ConfidenceScore` dataclass

### 5. Result Verification Agent
**File**: `src/llm/result_verification_agent.py`

- Validates query results for logical correctness
- Detects empty results, NULL values, extreme values, suspicious counts
- Triggers re-generation on high-confidence issues

**Key method**: `verify_result()` - returns `VerificationResult`

### 6. Correction Learner
**File**: `src/llm/correction_learner.py`

- Learns from successful corrections for instant future fixes
- 50% faster recovery on repeated errors
- Pattern-based matching with fuzzy similarity

**Key methods**: `learn_correction()`, `try_apply_learned_fix()`

### 7. Schema-Aware Fixer
**File**: `src/llm/schema_aware_fixer.py`

- Fast typo correction without LLM calls (200x faster)
- Uses fuzzy matching against actual schema
- Handles table names, column names, and common SQL errors

**Key method**: `try_quick_fix()` - returns corrected SQL or None

### 8. Prompt Sanitizer
**File**: `src/security/prompt_sanitizer.py`

- Multi-layer prompt injection protection
- Input sanitization (removes control chars, normalizes whitespace)
- Injection detection (15+ attack patterns blocked)
- Safe prompt construction with XML-like delimiters
- Token limits (500 chars for questions, 8000 for prompts)
- Defense in depth: API → Agent → Prompt layers

**Key methods**: `sanitize_input()`, `detect_injection_attempts()`, `create_safe_context_prompt()`

### 9. Multi-Database Handler
**File**: `src/core/multi_db_handler.py`
**Status**: PRODUCTION-READY (November 8, 2025)

- **Parallel multi-database execution**: 3x speedup with intelligent throttling
  - Queries execute simultaneously across multiple databases
  - Intelligent throttling (max 10 concurrent databases, configurable)
  - Dual timeout protection (35-second timeout prevents hanging)
  - Comprehensive metrics (speedup calculation, concurrency tracking, success rates)
- Handles both async (PostgreSQL, MySQL, SQLite) and sync (DuckDB) sessions
- Parallel schema introspection with `asyncio.gather()`
- Graceful degradation: one database failure doesn't stop others

**Key methods**: `build_combined_schema()`, `execute_multi_database_query()`, `execute_with_semaphore()`

### 10. Tool-Using Agent
**File**: `src/llm/tool_using_agent.py`
**Added**: November 21, 2025

- Enhances SQL generation by gathering schema context before query generation
- Analyzes user questions and automatically plans tool calls
- Executes tools to explore schema and sample data
- Builds enriched context for better first-attempt accuracy
- Calculates confidence scores based on tool results

**Key methods**: `analyze_question()`, `execute_tools()`, `build_context()`

### 11. Tool Registry
**File**: `src/tools/tool_registry.py`

- Central registry for all available tools with caching support
- Follows ColumnMapper pattern, uses MappingCache for performance
- Manages tool definitions, categories, and execution metrics
- Tracks execution statistics (times_executed, success_rate, cache_hit_rate)

**Key methods**: `register_tool()`, `get_tool()`, `get_tools_by_category()`, `invalidate_cache()`

### 12. Result Narrator Agent
**File**: `src/llm/result_narrator.py`
**Added**: December 13, 2025 (Updated Dec 24, 2025)

Generates human-readable narratives from query results with advanced analysis:

**Core Features**:
- Summary (1-2 sentences), Key Insights (3-5 bullets), Direct Answer
- Confidence Score (0.0-1.0), Statistics extraction

**Advanced Features** (all optional, never block):
- Anomaly Detection: Z-score outlier detection (|z| ≥ 1.95 threshold)
- Comparative Analysis: Compares results to historical similar queries
- Trend Detection: Linear regression on temporal columns (R² ≥ 0.3)
- Correlation Analysis: Pearson correlation between numeric columns (|r| > 0.7, minimum 10 rows)

**Performance**: <3 seconds for all features (99th percentile), <500ms for small datasets

**Key methods**: `generate_narrative()`, `_extract_json_object()`, `_detect_anomalies()`, `_detect_trends()`, `_calculate_correlations()`

### 13. Model Router
**File**: `src/llm/model_router.py`
**Added**: January 2, 2026

Routes LLM tasks to appropriate models based on task type and user configuration:
- SQL Generation: Use specialized SQL models (duckdb-nsql, sqlcoder)
- Narratives: Use general-purpose models (llama3.2, gemma)
- Query Planning: Use reasoning-capable models
- Error Correction: Use code-focused models

**Per-Task Timeouts**: Configurable timeout per task type (SQL: 30s, Narratives: 15s, Planning: 20s, Correction: 15s)

**Key methods**: `get_model_for_task()`, `get_timeout_for_task()`, `get_config_for_task()`

### 14. Query Template Engine
**File**: `src/llm/query_templates.py`
**Added**: January 2, 2026 (Updated January 10, 2026)

Template-based SQL generation that bypasses LLM for simple query patterns:

**Supported Patterns**:
- `list_all`: "show all products" → `SELECT * FROM products LIMIT 100`
- `count`: "how many customers" → `SELECT COUNT(*) FROM customers`
- `top_n`: "top 5 by price" → `SELECT * FROM X ORDER BY Y DESC LIMIT 5`
- `filter_location`: "orders from California" → `SELECT * FROM orders WHERE state = 'CA'`
- `filter_value`: "customers where status is active" → `SELECT * FROM customers WHERE status = 'active'`
- `filter_date`: "orders from last 7 days" → Dialect-specific date math
- `search`: "find products containing 'widget'" → Dialect-specific case-insensitive search
- `sum_total`, `average`, `group_by`: Aggregation patterns

**Key method**: `try_match()` - returns `TemplateMatch` or None

### 15. Dialect Registry
**File**: `src/llm/dialect_registry.py`
**Added**: January 10, 2026

Defines database-specific SQL syntax rules for cross-database compatibility:
- **Supported Dialects**: PostgreSQL, MySQL, SQLite, DuckDB
- Covers: Date/Time functions, Date math, String functions, Boolean handling, NULL handling, JSON/Array support

**Key classes**: `DatabaseDialect`, `DialectRules`, `DIALECT_RULES`

### 16. Query Preprocessor
**File**: `src/llm/query_preprocessor.py`
**Added**: January 2, 2026

Pre-processes natural language queries before LLM generation:
- **Bidirectional Location Normalization**: Detects DB format and converts accordingly
- **Entity Detection**: Extracts tables, columns, and values from questions
- **Schema Validation**: Early detection of impossible queries
- **Enhanced Context**: Builds LLM hints with matched entities and format guidance

**Key method**: `preprocess()` - returns `PreprocessedQuery`

### 17. Multi-Database Query Validator
**File**: `src/llm/multi_db_query_validator.py`
**Added**: January 7, 2026

Pre-flight validation for multi-database queries before execution:
- Assesses each database's capability: FULL / PARTIAL / CANNOT
- **SQL Parsing**: Uses `sqlparse` library with regex fallback
- **Location Detection**: Validates location columns across ALL tables
- **Fuzzy Matching**: Finds alternative columns for missing ones
- **Suggested SQL**: Generates modified SQL for PARTIAL capability databases

**Key methods**: `validate_query()`, `assess_database()`, `_extract_requirements()`

### 18. Prompt Optimizer
**File**: `src/llm/prompt_optimizer.py`
**Added**: January 11, 2026

Optimizes prompts for smaller LLM models:
- **Model Size Detection**: Auto-detects from name patterns (e.g., "7b" → MEDIUM)
- **Model Family Support**: 7 families (Llama, Qwen, Gemma, Mistral, Phi, DuckDB-NSQL, SQLCoder)
- **Schema Compression**: Includes only relevant tables based on question keywords
- **Smart Example Selection**: Chooses relevant few-shot examples
- **Token Budgeting**: Allocates tokens across system prompt, schema, examples, user input

**Key methods**: `optimize_prompt()`, `compress_schema()`, `select_examples()`

## Data Lineage System
**Location**: `src/lineage/`
**Added**: January 2026

### SQL Lineage Parser
**File**: `src/lineage/sql_lineage_parser.py` (835 lines)

Parses SQL queries to extract column-level lineage:
- **Node Types**: SOURCE_TABLE, SOURCE_COLUMN, TRANSFORMATION, OUTPUT_COLUMN
- **Transformation Types**: DIRECT, AGGREGATION, EXPRESSION, FUNCTION
- Handles JOINs, subqueries, aggregations, CASE expressions
- Table alias resolution and schema-qualified names

**Key methods**: `parse()`, `_extract_tables()`, `_extract_select_columns()`, `_process_select_item()`

### Impact Analyzer
**File**: `src/lineage/impact_analyzer.py` (341 lines)

Assesses impact of schema changes on existing queries:
- **Risk Levels**: LOW (<5 queries), MEDIUM (5-20), HIGH (>20)
- **Impact Types**: SELECT, FILTER, JOIN, GROUP, ORDER
- Word-boundary regex matching to avoid false positives

**Key methods**: `analyze_table_impact()`, `analyze_column_impact()`, `get_queries_for_table()`

### Query Pattern Analyzer
**File**: `src/lineage/query_pattern_analyzer.py` (399 lines)

Analyzes query patterns for heatmap visualization:
- **Table Usage Frequency**: Count table appearances across queries
- **Join Patterns**: Common join table pairs with sample SQL
- **Performance Bottlenecks**: High-frequency, high-latency tables (bottleneck_score 0-1)
- Time range filtering: 7, 30, 90 days or all history

**Key methods**: `get_table_usage_frequency()`, `get_common_join_patterns()`, `identify_bottlenecks()`, `get_heatmap_data()`

## Tool System
**Location**: `src/tools/`

10 specialized tools across 4 categories:

### Schema Tools (`src/tools/schema_tools.py`)
- `search_schema` - Search tables/columns by keyword with fuzzy matching
- `get_table_info` - Get detailed table information including columns, PKs, relationships
- `find_columns` - Find columns across all tables
- `get_relationships` - Get foreign key relationships and join suggestions

### Data Tools (`src/tools/data_tools.py`)
- `get_sample_data` - Sample rows from tables (max 20 rows)
- `get_column_values` - Get distinct column values (essential for 'CA' vs 'California')
- `count_rows` - Count rows with optional WHERE filter (has SQL injection protection)

### Query Tools (`src/tools/query_tools.py`)
- `test_query` - Test SQL syntax validity using EXPLAIN
- `validate_sql` - Validate SQL references against schema with fuzzy suggestions
- `explain_query` - Get query execution plan
