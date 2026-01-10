# SQL Generation Pipeline

## Overview

This document describes how Database Guru converts natural language questions into SQL queries, including the quality control mechanisms and planned improvements.

---

## Current Architecture

### High-Level Flow

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INPUT PROCESSING                             │
├─────────────────────────────────────────────────────────────────┤
│  1. Prompt Sanitizer (security)                                  │
│  2. Conversational Memory Agent (context from chat history)      │
│  3. Quality Profile Selection (based on user's quality slider)   │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SCHEMA PREPARATION                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Schema Cache retrieval (or fresh introspection)              │
│  2. Schema formatting with prominent table list                  │
│  3. Location hint enhancement (if quality >= 31%)                │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│              ⚡ TEMPLATE MATCHING (NEW - Jan 2026)               │
├─────────────────────────────────────────────────────────────────┤
│  TemplateEngine tries to match simple patterns:                  │
│  - "show all products" → SELECT * FROM products LIMIT 100       │
│  - "count customers" → SELECT COUNT(*) FROM customers           │
│  - "top 5 by price" → SELECT * FROM X ORDER BY Y DESC LIMIT 5  │
│  If matched: Execute directly, bypass LLM entirely!             │
│  If not matched: Continue to Query Planning                      │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│              🗺️ QUERY PREPROCESSING (NEW - Jan 2026)            │
├─────────────────────────────────────────────────────────────────┤
│  QueryPreprocessor normalizes inputs before LLM:                 │
│  - Bidirectional location normalization (California ↔ CA)       │
│  - Entity detection (tables, columns mentioned)                  │
│  - Schema validation (early impossible query detection)          │
│  - Enhanced context building for LLM                             │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     QUERY PLANNING (Optional)                    │
├─────────────────────────────────────────────────────────────────┤
│  QueryPlanningAgent analyzes complexity                          │
│  - If complex: Creates structured plan before SQL generation     │
│  - If force_planning (quality >= 71%): Always plans              │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SQL GENERATION                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Model Router selects per-task model (NEW - Jan 2026)         │
│  2. Tool-Using Agent (optional) explores schema                  │
│  3. LLM generates SQL via Ollama                                 │
│  4. "CANNOT_ANSWER" detection for impossible queries             │
│  5. Table validation (reject SQL with non-existent tables)       │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION & VERIFICATION                     │
├─────────────────────────────────────────────────────────────────┤
│  1. SQL Executor runs query with timeout protection              │
│  2. Result Verification Agent checks logical correctness         │
│  3. Confidence Scorer predicts success probability               │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ERROR CORRECTION (If Needed)                 │
├─────────────────────────────────────────────────────────────────┤
│  Self-Correcting Agent tries parallel fixes:                     │
│  1. Schema-Aware Quick Fix (no LLM, fastest)                     │
│  2. Learned Corrections (from past successes)                    │
│  3. LLM Regeneration (with error context)                        │
│  4. Tool-Using Agent (re-explore schema)                         │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RESPONSE                                     │
├─────────────────────────────────────────────────────────────────┤
│  1. Result Narrator generates human-readable summary             │
│  2. Save to chat history (if session_id provided)                │
│  3. Learn from corrections (if successful fix)                   │
└─────────────────────────────────────────────────────────────────┘

---

## Multi-Database Query Pipeline (Phase 2.4 - January 2026)

When querying multiple databases simultaneously, an additional pre-flight validation
layer ensures queries are only sent to databases that can answer them.

### Multi-Database Flow

```
User Question (Multi-DB Mode)
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│              🔍 PRE-FLIGHT VALIDATION (NEW - Jan 2026)          │
├─────────────────────────────────────────────────────────────────┤
│  MultiDatabaseQueryValidator assesses each database:            │
│  - Parses SQL using sqlparse (production-grade parser)          │
│  - Extracts required tables, columns, and values                │
│  - Validates against each database's schema                     │
│  - Assigns capability: FULL / PARTIAL / CANNOT                  │
│  - Finds alternatives for missing columns (fuzzy matching)      │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     USER ASSESSMENT UI                           │
├─────────────────────────────────────────────────────────────────┤
│  MultiDatabaseAssessment component shows:                        │
│  - Which databases can answer (FULL capability)                  │
│  - Which need modifications (PARTIAL capability)                 │
│  - Which cannot answer (CANNOT capability + reason)              │
│  - Users can select/deselect databases before execution          │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│              🚀 PARALLEL EXECUTION (Selected DBs Only)          │
├─────────────────────────────────────────────────────────────────┤
│  - FULL databases: Execute original SQL                          │
│  - PARTIAL databases: Execute suggested_sql with alternatives    │
│  - CANNOT databases: Skip with informative error message         │
│  - Per-database result narratives generated                      │
│  - Combined analysis synthesizes insights across all databases   │
└─────────────────────────────────────────────────────────────────┘
```

### Query Capability Assessment

| Capability | Description | UI Treatment |
|------------|-------------|--------------|
| **FULL** | Database has all required tables/columns | ✅ Green badge, auto-selected |
| **PARTIAL** | Missing columns but alternatives found | 🟡 Amber badge, auto-selected |
| **CANNOT** | Missing required data, no alternatives | ❌ Red badge, disabled |

### Pre-Flight Validation Details

#### SQL Parsing with sqlparse
The validator uses `sqlparse` (not regex) for production-grade SQL parsing:

```python
# From multi_db_query_validator.py
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Parenthesis

# Handles complex SQL patterns:
# - Schema-qualified names: public.orders → orders
# - Multiple tables: FROM orders, customers
# - All JOIN types: INNER, LEFT, RIGHT, OUTER, CROSS
# - Aliased tables: orders o, customers AS c
```

#### Location Detection
Intelligent detection of location-based queries:

```python
# Detects when query needs location filtering
# "orders from California" → needs state/region column

# Checks ALL tables for location columns (enables JOINs)
LOCATION_COLUMNS = [
    "state", "state_code", "region", "province",
    "ship_state", "shipping_state", "bill_state",
    # ... comprehensive list
]
```

#### Fuzzy Matching for Alternatives
When a required column is missing, finds close matches:

```python
COMMON_ALTERNATIVES = {
    "state": ["region", "province", "territory", "state_code"],
    "price": ["cost", "amount", "unit_price", "total_price"],
    "name": ["title", "label", "description", "full_name"],
    # ... more mappings
}

# Also uses SequenceMatcher for fuzzy similarity
# "state" → "us_state" (similarity > 0.6)
```

### Example Assessment

**Query**: "Show orders from California"

| Database | Schema | Capability | Reason |
|----------|--------|------------|--------|
| Sales DB | `orders.state` exists | FULL | Has state column |
| Inventory DB | No state column, has `region` | PARTIAL | Using `region` as alternative |
| Products DB | No location columns | CANNOT | No location data in schema |

### API Response Structure

```typescript
interface MultiDatabaseValidationResult {
  assessments: Record<number, DatabaseQueryAssessment>;
  can_execute_any: boolean;
  all_full: boolean;
  primary_sql: string;
  warnings: string[];
}

interface DatabaseQueryAssessment {
  connection_id: number;
  connection_name: string;
  database_type: string;
  capability: "full" | "partial" | "cannot";
  missing_tables: string[];
  missing_columns: Record<string, string[]>;
  available_alternatives: Record<string, string>;
  suggested_sql: string | null;
  reason: string;
  confidence: number;
}
```

### Frontend Components

| Component | Purpose |
|-----------|---------|
| `SchemaGlance.tsx` | Overview of all database schemas with location warnings |
| `MultiDatabaseAssessment.tsx` | Per-database capability selection UI |
| `QueryFeasibilityBadge.tsx` | Compact/expanded capability indicators |
| `MultiDatabaseResults.tsx` | Results with "Cannot Answer" differentiation |
```

---

## Detailed Component Breakdown

### 1. Input Processing

#### Prompt Sanitizer (`src/security/prompt_sanitizer.py`)
- Removes control characters and normalizes whitespace
- Detects 15+ prompt injection attack patterns
- Enforces token limits (500 chars for questions)

#### Conversational Memory Agent (`src/llm/conversational_memory_agent.py`)
- Retrieves previous queries from chat session
- Builds context-aware prompts for follow-up questions
- Smart detection of contextual vs standalone questions

#### Quality Profile (`src/llm/quality_profile.py`)
Based on the user's quality slider (0-100%):

| Level | Range | Key Settings |
|-------|-------|--------------|
| **Fast** | 0-30% | 1 retry, no location hints, skip verification |
| **Balanced** | 31-70% | 3 retries, location hints ON, verification ON |
| **Thorough** | 71-100% | 5 retries, force planning, tool exploration ON |

### 2. Schema Preparation

#### Schema Cache (`src/core/schema_cache.py`)
- Caches introspected schemas for 30 minutes
- Reduces repeated database introspection

#### Schema Formatting (`src/core/schema_inspector.py:format_schema_for_llm`)
Current format sent to LLM:
```
==================================================
AVAILABLE TABLES (USE ONLY THESE):
products, orders, order_items, categories, reviews
==================================================

Database Schema:
Table Count: 5
Total Columns: 25

Table: products
  Columns:
    - id: INTEGER NOT NULL [PK]
    - name: VARCHAR NOT NULL
    - category_id: INTEGER NULL  // Examples: 1, 2, 3
    - state: VARCHAR NULL  // Examples: 'TX', 'CA', 'NY'
  Foreign Keys:
    - category_id -> categories.id

...

==================================================
REMINDER: Only use tables: products, orders, ...
DO NOT use tables from examples if they don't exist above!
==================================================
```

#### Location Mapper (`src/core/location_mapper.py`)
When quality >= 31% and schema_dict is available:
- Detects location mentions in query ("Texas", "New York", etc.)
- Adds hints: `"'texas' should use code: 'TX'"`
- Enhances question before sending to LLM

### 2.5 Template Matching (NEW - January 2026, Updated January 10, 2026)

#### Template Engine (`src/llm/query_templates.py`)
Bypasses LLM entirely for simple, common query patterns:

| Pattern | Example Question | Generated SQL |
|---------|-----------------|---------------|
| `list_all` | "show all products" | `SELECT * FROM products LIMIT 100` |
| `count` | "how many customers" | `SELECT COUNT(*) FROM customers` |
| `top_n` | "top 5 by price" | `SELECT * FROM X ORDER BY Y DESC LIMIT 5` |
| `filter_location` | "orders from California" | `SELECT * FROM orders WHERE state = 'CA'` |
| `filter_value` | "customers where status is active" | `SELECT * FROM customers WHERE status = 'active'` |
| `filter_date` | "orders from last 7 days" | Dialect-specific (see below) |
| `search` | "find products containing 'widget'" | Dialect-specific (see below) |
| `sum_total` | "total revenue" | `SELECT SUM(revenue) FROM orders` |
| `average` | "average price" | `SELECT AVG(price) FROM products` |
| `group_by` | "sales by category" | `SELECT category, COUNT(*) FROM X GROUP BY category` |

**Key Features:**
- Returns `TemplateMatch` with SQL, confidence score (0.9-0.95), explanation, and `dialect_used`
- Table alias handling (singular/plural, abbreviations: cust → customers)
- Column variation matching (price → unit_price, name → product_name)
- **Dialect-aware SQL generation (NEW - Jan 10, 2026)** - Uses `DialectRegistry` for database-specific syntax
- If matched: Execute directly, skip all LLM processing
- If not matched: Continue to preprocessing and LLM generation

### 2.5.1 Dialect Registry (NEW - January 10, 2026)

#### Dialect Registry (`src/llm/dialect_registry.py`)
Defines database-specific SQL syntax rules for accurate cross-database SQL generation:

**Supported Dialects:**
| Dialect | Current Timestamp | Date Math | Case-Insensitive | Boolean |
|---------|-------------------|-----------|------------------|---------|
| PostgreSQL | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP - INTERVAL '7 days'` | `ILIKE` | `TRUE/FALSE` |
| MySQL | `NOW()` | `DATE_SUB(NOW(), INTERVAL 7 DAY)` | `LIKE` (default collation) | `TRUE/FALSE` |
| SQLite | `datetime('now')` | `datetime('now', '-7 days')` | `LIKE` (ASCII only) | `1/0` |
| DuckDB | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP - INTERVAL '7 days'` | `ILIKE` | `TRUE/FALSE` |

**Key Components:**
- `DatabaseDialect` enum - Identifies target database type
- `DialectRules` dataclass - Contains syntax rules for date functions, string operations, pagination, booleans, JSON, arrays
- `DIALECT_RULES` dict - Maps dialects to their rules
- `build_dialect_context()` - Generates dialect-specific instructions for LLM prompts
- `get_dialect_for_database_type()` - Maps connection string to dialect

**Example: Date Filter Generation**
```
Query: "orders from last 7 days"

PostgreSQL: WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
SQLite: WHERE created_at > datetime('now', '-7 days')
MySQL: WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
DuckDB: WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
```

**Example: Case-Insensitive Search**
```
Query: "find products containing 'widget'"

PostgreSQL/DuckDB: WHERE name ILIKE '%widget%'
SQLite/MySQL: WHERE LOWER(name) LIKE LOWER('%widget%')
```

### 2.6 Query Preprocessing (NEW - January 2026)

#### Query Preprocessor (`src/llm/query_preprocessor.py`)
Pre-processes natural language before LLM generation:

**Bidirectional Location Normalization:**
```
Database uses codes (CA, NY, TX):
  "California" → "CA"  (normalize to match DB)

Database uses full names:
  "CA" → "California"  (expand to match DB)
```

**Entity Detection:**
- Extracts table/column mentions from question
- Validates against actual schema
- Detects impossible queries early

**Enhanced Context:**
- Builds LLM hints: `"'California' → 'CA' (state column uses codes)"`
- Provides format guidance based on sample values

**Output:** `PreprocessedQuery` dataclass with:
- `normalized`: Question with locations converted
- `detected_locations`: List of normalized locations
- `detected_entities`: Tables/columns mentioned
- `enhanced_context`: Hints for LLM
- `validation_warnings`: Early error detection

### 3. SQL Generation

#### Model Router (`src/llm/model_router.py`) (NEW - January 2026)
Routes different LLM tasks to specialized models:

| Task Type | Recommended Model | Default Timeout |
|-----------|-------------------|-----------------|
| `SQL_GENERATION` | duckdb-nsql, sqlcoder | 30s |
| `NARRATIVES` | llama3.2, gemma | 15s |
| `QUERY_PLANNING` | Reasoning-capable models | 20s |
| `ERROR_CORRECTION` | Code-focused models | 15s |

**Key Features:**
- Per-task model configuration stored in `SystemSettings`
- Falls back to default `OLLAMA_MODEL` if per-task model not set
- Per-task timeout configuration
- UI configuration via `ModelConfigPanel`

#### LLM Prompts (`src/llm/prompts.py`)
Key instructions in system prompt:
- **Schema First**: Only use tables from provided schema
- **Cannot Answer**: Return `CANNOT_ANSWER: reason` if query impossible
- **Location Handling**: Use 2-letter state codes (CA, TX, NY)

#### SQL Generator (`src/llm/sql_generator.py`)
1. Model Router selects appropriate model for task (NEW)
2. Applies location hints to question
3. Checks LLM cache for similar queries
4. Sends prompt to Ollama with per-task timeout
5. Detects `CANNOT_ANSWER` responses
6. Cleans and validates SQL output

#### Table Validation (NEW)
After SQL generation, validates all referenced tables exist:
```python
tables_valid, missing = SQLValidator.validate_tables_exist(sql, schema_tables)
if not tables_valid:
    # Triggers retry with explicit error message
    error = f"SQL references non-existent tables: {missing}"
```

### 4. Execution & Verification

#### SQL Executor (`src/core/executor.py`)
- 30-second timeout protection
- 1000 row limit (configurable)
- Handles both async and sync database sessions

#### Result Verification Agent (`src/llm/result_verification_agent.py`)
Checks for logical issues:
- Empty results when data expected
- Suspicious NULL patterns
- Extreme or unexpected values

#### Confidence Scorer (`src/llm/confidence_scorer.py`)
Predicts success probability (0.0-1.0) using:
- Error type weight (30%)
- Schema match (25%)
- Historical success (20%)
- Query complexity (15%)
- Similarity to past queries (10%)

### 5. Error Correction

#### Self-Correcting Agent (`src/llm/self_correcting_agent.py`)
Parallel correction strategies:
1. **Quick Fix** - Schema-aware typo correction (no LLM, 200x faster)
2. **Learned Fix** - Apply patterns from past successful corrections
3. **LLM Fix** - Regenerate with error context
4. **Tool Fix** - Re-explore schema with tool-using agent

---

## Current Quality Issues & Solutions

### Issue 1: LLM Uses Non-Existent Tables
**Symptom**: SQL references "customers" table that doesn't exist

**Root Cause**: Few-shot examples hardcode table names; LLM copies them

**Solutions Implemented**:
1. ✅ Prominent table list at top/bottom of schema
2. ✅ Post-generation table validation with retry
3. ✅ Removed hardcoded table names from examples
4. ✅ Added disclaimer that examples show patterns only

### Issue 2: Location Queries Fail
**Symptom**: "products from Texas" returns wrong results

**Root Cause**: LocationMapper was dead code; not wired up

**Solutions Implemented**:
1. ✅ LocationMapper now receives schema_dict properly
2. ✅ Adds location hints to questions
3. ✅ System prompt instructs to use state codes (TX, CA, NY)

### Issue 3: Impossible Queries Generate Garbage SQL
**Symptom**: Asking about data that doesn't exist produces nonsense SQL

**Root Cause**: LLM forced to generate something even when impossible

**Solutions Implemented**:
1. ✅ CANNOT_ANSWER response for impossible queries
2. ✅ User-friendly error message explaining schema limitation

---

## Planned Quality Improvements

### Phase 1: Semantic Understanding (Priority: High) ✅ IMPLEMENTED

#### 1.1 Query Intent Classification ✅ IMPLEMENTED (January 2026)
Implemented via `QueryPreprocessor` and `TemplateEngine`:
- **Lookup**: "Show all products" → Template match → `SELECT * FROM products LIMIT 100`
- **Aggregation**: "Total sales by category" → Template match → `SELECT category, SUM(...) GROUP BY`
- **Comparison**: Handled by entity detection in QueryPreprocessor
- **Impossible**: Early detection via schema validation in QueryPreprocessor

**Implementation**: `src/llm/query_preprocessor.py` and `src/llm/query_templates.py`

#### 1.2 Required Data Detection ✅ IMPLEMENTED (January 2026)
Implemented in `QueryPreprocessor._validate_schema_requirements()`:
- Detects tables/columns mentioned in question
- Validates against actual schema
- Returns `validation_warnings` for impossible queries

### Phase 2: Schema-Aware Generation (Priority: High) ✅ PARTIALLY IMPLEMENTED

#### 2.1 Dynamic Few-Shot Examples
🔄 Existing in Query Planning Agent, enhanced by Template Engine for simple cases.

#### 2.2 Column Value Awareness ✅ IMPLEMENTED (January 2026)
Implemented via `QueryPreprocessor`:
- Detects location columns from schema sample values
- Bidirectional normalization: California ↔ CA based on what DB stores
- Format hints provided to LLM: "Database uses 2-letter state codes"

**Implementation**: `src/llm/query_preprocessor.py:_detect_location_format()`

### Phase 3: Validation Improvements (Priority: Medium) ✅ PARTIALLY IMPLEMENTED

#### 3.1 Pre-Generation Validation ✅ IMPLEMENTED (January 2026)
Implemented in `QueryPreprocessor`:
```python
# From query_preprocessor.py
def _validate_schema_requirements(self, result: PreprocessedQuery):
    # Check if required tables exist
    for table in result.required_tables:
        if table.lower() not in tables_lower:
            result.schema_validation_passed = False
            result.validation_warnings.append(f"Table '{table}' not found")
```

#### 3.2 SQL Semantic Validation
After generation, verify SQL matches intent:
```python
def validate_sql_intent(sql: str, question: str) -> tuple[bool, str]:
    # Question asks for "customers from Texas"
    # SQL should have:
    # - Reference to customer-like table
    # - Filter on state/location column
    # - Value 'TX' or 'Texas'

    if "texas" in question.lower() and "'TX'" not in sql and "'Texas'" not in sql:
        return False, "SQL doesn't filter by Texas as requested"

    return True, ""
```

### Phase 4: Learning & Adaptation (Priority: Medium)

#### 4.1 Query Pattern Learning
Learn successful query patterns per database:
```python
# Store successful patterns
patterns = {
    "connection_1": {
        "location_filter": "WHERE state = '{code}'",  # learned from successes
        "category_join": "JOIN categories c ON p.category_id = c.id"
    }
}
```

#### 4.2 Schema-Specific Vocabulary
Learn that "Texas" → "TX" for a specific database:
```python
vocabulary = {
    "connection_1": {
        "Texas": "TX",
        "California": "CA",
        "shipped": "status = 'shipped'"
    }
}
```

### Phase 5: User Feedback Integration (Priority: Low)

#### 5.1 Inline Corrections
Allow users to correct SQL inline:
```
Generated: SELECT * FROM products WHERE state = 'Texas'
User: "state should be 'TX' not 'Texas'"
System: Learns this correction for future queries
```

#### 5.2 Query Refinement
Interactive refinement:
```
User: "Show products from Texas"
System: "This database doesn't have location data. Did you mean:
  1. Show all products
  2. Show products by category
  3. Show products with reviews"
```

---

## Metrics to Track

### Quality Metrics
| Metric | Current | Target |
|--------|---------|--------|
| First-attempt success rate | ~60% | 85% |
| CANNOT_ANSWER accuracy | New | 95% |
| Location query accuracy | ~70% | 95% |
| Table validation catches | New | 99% |

### Performance Metrics
| Metric | Current | Target |
|--------|---------|--------|
| Average query time | 2-5s | <2s |
| Retry rate | ~40% | <15% |
| Parallel correction speedup | 1.6x | 2x |

---

## File Reference

| Component | File | Key Methods |
|-----------|------|-------------|
| Quality Profile | `src/llm/quality_profile.py` | `get_quality_profile()` |
| SQL Generator | `src/llm/sql_generator.py` | `generate_sql()` |
| Self-Correcting Agent | `src/llm/self_correcting_agent.py` | `generate_and_execute_with_retry()` |
| Query Planning | `src/llm/query_planning_agent.py` | `plan_and_generate_sql()` |
| Schema Inspector | `src/core/schema_inspector.py` | `format_schema_for_llm()` |
| Location Mapper | `src/core/location_mapper.py` | `enhance_query_with_location_hints()` |
| Prompts | `src/llm/prompts.py` | `SYSTEM_PROMPT`, `SQL_GENERATION_TEMPLATE` |
| Result Narrator | `src/llm/result_narrator.py` | `generate_narrative()` |
| **Model Router (NEW)** | `src/llm/model_router.py` | `get_model_for_task()`, `get_timeout_for_task()` |
| **Template Engine (NEW)** | `src/llm/query_templates.py` | `try_match()`, `TemplateMatch` |
| **Dialect Registry (NEW - Jan 10)** | `src/llm/dialect_registry.py` | `DatabaseDialect`, `DialectRules`, `build_dialect_context()` |
| **Query Preprocessor (NEW)** | `src/llm/query_preprocessor.py` | `preprocess()`, `PreprocessedQuery` |
| **Model Config UI (NEW)** | `frontend/src/components/ModelConfigPanel.tsx` | Per-task model configuration |
| **Multi-DB Validator (NEW)** | `src/llm/multi_db_query_validator.py` | `validate_query()`, `assess_database()` |
| **Schema Glance UI (NEW)** | `frontend/src/components/SchemaGlance.tsx` | Database schema overview |
| **Assessment UI (NEW)** | `frontend/src/components/MultiDatabaseAssessment.tsx` | Per-DB capability selection |
| **Feasibility Badge (NEW)** | `frontend/src/components/QueryFeasibilityBadge.tsx` | Capability status badges |

---

## Conclusion

The SQL generation pipeline has evolved to include:
1. **Quality-aware generation** with user-controlled accuracy/speed tradeoffs
2. **Schema-first approach** preventing references to non-existent tables
3. **Location intelligence** for state code normalization
4. **Graceful failure** with CANNOT_ANSWER for impossible queries
5. **Self-correction** with parallel fix strategies
6. **Template matching (NEW - Jan 2026)** - Bypass LLM for simple query patterns
7. **Query preprocessing (NEW - Jan 2026)** - Bidirectional location normalization
8. **Per-task model routing (NEW - Jan 2026)** - Specialized models for different tasks
9. **Multi-DB pre-flight validation (NEW - Jan 2026)** - Assess query feasibility per database before execution
10. **Dialect-aware SQL generation (NEW - Jan 10, 2026)** - Database-specific syntax for dates, booleans, strings

Future improvements focus on:
- ~~Pre-generation intent classification~~ ✅ Implemented via TemplateEngine
- ~~Schema-specific example generation~~ ✅ Partially implemented via templates
- ~~Multi-database query intelligence~~ ✅ Implemented via MultiDatabaseQueryValidator
- Semantic validation of generated SQL (planned)
- Continuous learning from successful queries (existing via CorrectionLearner)
- Integration tests for per-task model routing
- Performance benchmarks for template matching

### Phase 2 Planned Improvements

See [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) for detailed planning:

| Improvement | Description | Expected Impact |
|-------------|-------------|-----------------|
| **Database Dialect Support** | Dialect-specific SQL generation (PostgreSQL, MySQL, SQLite, DuckDB) | 90% dialect accuracy (up from 60%) |
| **Prompt Optimization** | Token budgets, schema compression, model-specific templates | 40% token reduction |
| **Advanced Preprocessing** | Date, boolean, status, currency normalization | 90% date query accuracy |
| **Pattern Learning** | Learn successful patterns from executed queries | +15% template match rate |
| **Model Performance Tracking** | Track and optimize model selection per task | Auto-selection of best models |
