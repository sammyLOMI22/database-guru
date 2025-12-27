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
│  1. Tool-Using Agent (optional) explores schema                  │
│  2. LLM generates SQL via Ollama                                 │
│  3. "CANNOT_ANSWER" detection for impossible queries             │
│  4. Table validation (reject SQL with non-existent tables)       │
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

### 3. SQL Generation

#### LLM Prompts (`src/llm/prompts.py`)
Key instructions in system prompt:
- **Schema First**: Only use tables from provided schema
- **Cannot Answer**: Return `CANNOT_ANSWER: reason` if query impossible
- **Location Handling**: Use 2-letter state codes (CA, TX, NY)

#### SQL Generator (`src/llm/sql_generator.py`)
1. Applies location hints to question
2. Checks LLM cache for similar queries
3. Sends prompt to Ollama
4. Detects `CANNOT_ANSWER` responses
5. Cleans and validates SQL output

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

### Phase 1: Semantic Understanding (Priority: High)

#### 1.1 Query Intent Classification
Before SQL generation, classify the query intent:
- **Lookup**: "Show all products" → Simple SELECT
- **Aggregation**: "Total sales by category" → GROUP BY
- **Comparison**: "Products cheaper than $50" → WHERE with comparison
- **Relationship**: "Orders with their products" → JOIN
- **Impossible**: "Customer locations" (no customer table) → CANNOT_ANSWER

**Implementation**:
```python
class QueryIntentClassifier:
    def classify(self, question: str, schema: Dict) -> QueryIntent:
        # Analyze question against available schema
        # Return intent + required tables/columns
        pass
```

#### 1.2 Required Data Detection
Before generation, identify what data is needed:
```python
required = {
    "tables": ["orders", "products"],
    "columns": {"orders": ["total"], "products": ["name"]},
    "filters": [{"column": "state", "value": "TX"}]
}

# Check if schema can satisfy requirements
missing = schema_validator.find_missing(required, schema)
if missing:
    return f"CANNOT_ANSWER: Missing {missing}"
```

### Phase 2: Schema-Aware Generation (Priority: High)

#### 2.1 Dynamic Few-Shot Examples
Generate examples based on ACTUAL schema:
```python
def generate_schema_specific_examples(schema: Dict) -> str:
    examples = []
    for table in schema['tables']:
        # Generate example query for this specific table
        example = f"Question: Show all {table}\nSQL: SELECT * FROM {table} LIMIT 10"
        examples.append(example)
    return "\n\n".join(examples)
```

#### 2.2 Column Value Awareness
When schema includes sample values, use them in prompts:
```
Table: products
  - state: VARCHAR  // Actual values: 'TX', 'CA', 'NY', 'FL'

For query "products from Texas", note that state column uses codes like 'TX'
```

### Phase 3: Validation Improvements (Priority: Medium)

#### 3.1 Pre-Generation Validation
Check if query CAN be answered before asking LLM:
```python
def can_answer_query(question: str, schema: Dict) -> tuple[bool, str]:
    # Extract entities from question
    entities = extract_entities(question)  # ["customers", "Texas"]

    # Check if schema supports these entities
    if "customers" in entities and "customers" not in schema["tables"]:
        return False, "No customers table in this database"

    if "Texas" in entities and not has_location_column(schema):
        return False, "No location/state column in this database"

    return True, ""
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

---

## Conclusion

The SQL generation pipeline has evolved to include:
1. **Quality-aware generation** with user-controlled accuracy/speed tradeoffs
2. **Schema-first approach** preventing references to non-existent tables
3. **Location intelligence** for state code normalization
4. **Graceful failure** with CANNOT_ANSWER for impossible queries
5. **Self-correction** with parallel fix strategies

Future improvements focus on:
- Pre-generation intent classification
- Schema-specific example generation
- Semantic validation of generated SQL
- Continuous learning from successful queries
