# Small Model Optimization & Per-Task Model Routing

## Overview

This document outlines the strategy for improving SQL generation quality when using smaller, resource-efficient LLMs (3B-7B parameters) instead of large models (32B+). The key insight is that **specialized models excel at specific tasks** - a SQL-focused model produces excellent queries but poor narratives, while a general-purpose model produces good text but mediocre SQL.

## Problem Statement

### Current Architecture (Single Model)

```
User selects: duckdb-nsql (SQL-specialized)
                    ↓
    ┌───────────────────────────────────────┐
    │  ALL tasks use the same model:        │
    │  ✅ SQL Generation     ← Excellent    │
    │  ❌ Narrative Generation ← Poor       │
    │  ❌ Query Planning       ← Poor       │
    │  ❌ Error Explanation    ← Poor       │
    │  ❌ Intent Classification← Poor       │
    └───────────────────────────────────────┘
```

### Observed Issues with llama3.2:latest (3B)

From log analysis on 2025-12-30:

1. **Schema Hallucination** - Model invents tables/columns that don't exist
2. **Location Query Failures** - "orders from Texas" → `WHERE shipped_date LIKE '%/%/TX'`
3. **JSON Generation Errors** - Query planning fails with parse errors
4. **Low Confidence Scores** - Consistently 0.30 for query plans
5. **Self-Correction Loops** - 3 retries often can't fix fundamental errors

### Root Causes

| Issue | Root Cause |
|-------|------------|
| Schema hallucination | Model doesn't fully parse schema context |
| Location failures | No pre-processing of location names |
| JSON errors | Small models struggle with structured output |
| Low confidence | Model uncertainty propagates through pipeline |

---

## Solution Architecture

### Per-Task Model Routing

```
┌─────────────────────────────────────────────────────────┐
│  Task-Specific Model Assignment:                        │
│                                                          │
│  SQL Generation    → duckdb-nsql:latest (specialized)   │
│  Narratives        → llama3.2:latest (general purpose)  │
│  Query Planning    → llama3.2:latest (reasoning)        │
│  Error Correction  → llama3.2:latest (explanation)      │
│  Intent Detection  → Rule-based (no LLM needed)         │
└─────────────────────────────────────────────────────────┘
```

### Additional Optimizations

1. **Pre-Processing Pipeline** - Location normalization, entity extraction before LLM
2. **Schema Enhancement** - Include sample column values in prompts
3. **Query Templates** - Bypass LLM entirely for simple patterns
4. **Prompt Simplification** - Shorter, clearer prompts for small models
5. **Semantic Caching** - Reuse successful queries for similar questions

---

## Implementation Components

### 1. Model Router Service

**File:** `src/llm/model_router.py`

```python
class ModelRouter:
    """Routes LLM tasks to appropriate models based on configuration."""

    # Task type constants
    TASK_SQL_GENERATION = "sql_generation"
    TASK_NARRATIVES = "narratives"
    TASK_QUERY_PLANNING = "query_planning"
    TASK_ERROR_CORRECTION = "error_correction"

    def __init__(self, settings: ModelSettings):
        self.settings = settings
        self._clients: Dict[str, OllamaClient] = {}

    async def get_client_for_task(self, task: str) -> OllamaClient:
        """Get the appropriate OllamaClient for a specific task."""
        model = self._get_model_for_task(task)
        timeout = self._get_timeout_for_task(task)

        cache_key = f"{model}:{timeout}"
        if cache_key not in self._clients:
            self._clients[cache_key] = await OllamaClient.create(
                model=model,
                timeout=timeout
            )
        return self._clients[cache_key]
```

### 2. Model Settings Schema

**Database Table:** `model_settings`

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | INTEGER | PK | Primary key |
| model_sql_generation | VARCHAR(100) | "llama3.2:latest" | Model for SQL generation |
| model_narratives | VARCHAR(100) | "llama3.2:latest" | Model for narratives |
| model_query_planning | VARCHAR(100) | "llama3.2:latest" | Model for query planning |
| model_error_correction | VARCHAR(100) | "llama3.2:latest" | Model for error fixing |
| timeout_sql_generation | INTEGER | 30 | SQL generation timeout (seconds) |
| timeout_narratives | INTEGER | 15 | Narrative timeout (seconds) |
| timeout_query_planning | INTEGER | 20 | Query planning timeout (seconds) |
| timeout_error_correction | INTEGER | 15 | Error correction timeout (seconds) |
| updated_at | DATETIME | NOW() | Last update timestamp |

### 3. Pre-Processing Pipeline

**File:** `src/llm/query_preprocessor.py`

```python
class QueryPreprocessor:
    """Pre-processes natural language queries before LLM generation."""

    def __init__(self, schema_dict: Dict):
        self.schema = schema_dict
        self.location_mapper = LocationMapper()

    def preprocess(self, question: str) -> PreprocessedQuery:
        """
        Apply all pre-processing steps:
        1. Normalize locations (New York → NY)
        2. Extract entities (table names, column names)
        3. Detect query intent
        4. Build enhanced context
        """
        # Step 1: Location normalization
        normalized_question = self._normalize_locations(question)

        # Step 2: Entity extraction
        entities = self._extract_entities(question)

        # Step 3: Schema context with sample values
        enhanced_schema = self._build_enhanced_schema(entities)

        return PreprocessedQuery(
            original=question,
            normalized=normalized_question,
            entities=entities,
            enhanced_schema=enhanced_schema
        )
```

### 4. Query Templates

**File:** `src/llm/query_templates.py`

```python
QUERY_TEMPLATES = {
    # Pattern: (regex, template, required_entities)
    "list_all": (
        r"^(show|list|get|display)\s+(all\s+)?(\w+)s?$",
        "SELECT * FROM {table} LIMIT {limit}",
        ["table"]
    ),
    "count": (
        r"^(how many|count)\s+(\w+)s?",
        "SELECT COUNT(*) as count FROM {table}",
        ["table"]
    ),
    "top_n": (
        r"^(top|best|highest)\s+(\d+)\s+(\w+)s?\s+by\s+(\w+)",
        "SELECT * FROM {table} ORDER BY {column} DESC LIMIT {n}",
        ["table", "column", "n"]
    ),
    "filter_by_value": (
        r"^(\w+)s?\s+(from|in|where)\s+(\w+)\s*=?\s*['\"]?(\w+)['\"]?",
        "SELECT * FROM {table} WHERE {column} = '{value}' LIMIT {limit}",
        ["table", "column", "value"]
    ),
}

class TemplateEngine:
    """Matches questions to SQL templates, bypassing LLM for simple queries."""

    def try_match(self, question: str, schema: Dict) -> Optional[str]:
        """Try to match question to a template. Returns SQL or None."""
        for name, (pattern, template, required) in QUERY_TEMPLATES.items():
            match = re.match(pattern, question.lower().strip())
            if match:
                entities = self._extract_from_match(match, required)
                if self._validate_entities(entities, schema):
                    return template.format(**entities, limit=100)
        return None
```

### 5. Enhanced Schema Context

**File:** `src/core/schema_enhancer.py`

```python
class SchemaEnhancer:
    """Enhances schema with sample values for better LLM understanding."""

    def enhance(self, schema_dict: Dict, session) -> str:
        """
        Build enhanced schema string with:
        - Table descriptions
        - Column types and sample values
        - Foreign key relationships with join hints
        - Location hints for state/country columns
        """
        enhanced = []
        for table_name, table_info in schema_dict.get("tables", {}).items():
            enhanced.append(f"\n=== TABLE: {table_name} ===")

            for col in table_info.get("columns", []):
                col_str = f"  - {col['name']} ({col['type']})"

                # Add sample values for categorical columns
                if col.get("sample_values"):
                    samples = col["sample_values"][:5]
                    col_str += f" [Values: {', '.join(repr(v) for v in samples)}]"

                # Add location hints
                if col.get("location_type"):
                    col_str += f" [LOCATION:{col['location_type']}]"

                enhanced.append(col_str)

            # Add foreign key hints
            for fk in table_info.get("foreign_keys", []):
                enhanced.append(f"  → JOIN: {table_name}.{fk['column']} → {fk['references']['table']}.{fk['references']['column']}")

        return "\n".join(enhanced)
```

---

## UI Components

### Model Configuration Panel

**File:** `frontend/src/components/ModelConfigPanel.tsx`

```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Model Configuration                            [?] Help │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ SQL Generation ─────────────────────────────────────┐   │
│  │ Model: [duckdb-nsql:latest        ▼]                 │   │
│  │ Timeout: [30] seconds                                │   │
│  │ 💡 Specialized SQL models: duckdb-nsql, sqlcoder     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Narratives & Insights ──────────────────────────────┐   │
│  │ Model: [llama3.2:latest           ▼]                 │   │
│  │ Timeout: [15] seconds                                │   │
│  │ 💡 General purpose models work best for narratives   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Query Planning ─────────────────────────────────────┐   │
│  │ Model: [llama3.2:latest           ▼]                 │   │
│  │ Timeout: [20] seconds                                │   │
│  │ 💡 Reasoning-capable models recommended              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Error Correction ───────────────────────────────────┐   │
│  │ Model: [llama3.2:latest           ▼]                 │   │
│  │ Timeout: [15] seconds                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Advanced Options ───────────────────────────────────┐   │
│  │ ☑ Enable query templates (bypass LLM for simple)     │   │
│  │ ☑ Pre-process locations (NY ↔ New York)              │   │
│  │ ☑ Include sample values in schema                    │   │
│  │ ☑ Enable semantic caching                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Reset to Defaults]                    [Save Configuration] │
└─────────────────────────────────────────────────────────────┘
```

---

## Recommended Model Combinations

### For Resource-Constrained Environments (8GB VRAM)

| Task | Model | Size | Notes |
|------|-------|------|-------|
| SQL Generation | duckdb-nsql:latest | 7B | Optimized for SQL |
| Narratives | llama3.2:latest | 3B | Fast, good text |
| Query Planning | llama3.2:latest | 3B | Adequate for planning |
| Error Correction | llama3.2:latest | 3B | Quick fixes |

### For Better Quality (16GB+ VRAM)

| Task | Model | Size | Notes |
|------|-------|------|-------|
| SQL Generation | sqlcoder:15b | 15B | Excellent SQL |
| Narratives | gemma3:27b | 27B | Rich narratives |
| Query Planning | qwen2.5-coder:14b | 14B | Strong reasoning |
| Error Correction | codellama:13b | 13B | Code understanding |

### For Maximum Quality (24GB+ VRAM)

| Task | Model | Size | Notes |
|------|-------|------|-------|
| SQL Generation | qwen2.5-coder:32b | 32B | Best overall |
| All Other Tasks | qwen2.5-coder:32b | 32B | Single model simplicity |

---

## Performance Expectations

### Before Optimization (Single small model)

| Metric | Value |
|--------|-------|
| First-attempt SQL success | ~40% |
| Location query success | ~20% |
| Narrative quality | Poor (for SQL models) |
| Average query time | 3-5 seconds |

### After Optimization

| Metric | Expected Value |
|--------|----------------|
| First-attempt SQL success | ~70-80% |
| Location query success | ~90% (with pre-processing) |
| Narrative quality | Good (using appropriate model) |
| Average query time | 2-4 seconds |
| Template matches (no LLM) | ~20% of queries |

---

## Implementation Phases

### Phase 1: Core Infrastructure (Priority: High) ✅ COMPLETE
- [x] Create ModelSettings database table → Added to `SystemSettings` in `src/database/models.py`
- [x] Implement ModelRouter service → `src/llm/model_router.py` (246 lines)
- [x] Add per-task model configuration to settings API → `src/api/endpoints/settings.py`
- [x] Database migration → Fields added to SystemSettings model

### Phase 2: Pre-Processing Pipeline (Priority: High) ✅ COMPLETE
- [x] Create QueryPreprocessor class → `src/llm/query_preprocessor.py` (504 lines)
- [x] Integrate LocationMapper into pre-processing → Bidirectional normalization (CA↔California)
- [x] Add sample value extraction to SchemaInspector → Already exists, used by preprocessor
- [x] Create SchemaEnhancer for richer context → Enhanced context in `PreprocessedQuery.enhanced_context`

### Phase 3: Query Templates (Priority: Medium) ✅ COMPLETE
- [x] Implement TemplateEngine → `src/llm/query_templates.py` (724 lines)
- [x] Add common query pattern templates → 10 template types (list_all, count, top_n, filter_location, etc.)
- [x] Integrate with SQL generation flow → `self_correcting_agent.py:821-907`
- [x] Add template match tracking/metrics → `TemplateMatch` with confidence scores in response

### Phase 4: UI Components (Priority: Medium) ✅ COMPLETE
- [x] Create ModelConfigPanel component → `frontend/src/components/ModelConfigPanel.tsx` (310 lines)
- [x] Add to Settings page → Integrated in `SettingsPanel.tsx`
- [x] Model dropdown with descriptions → Fetches from Ollama, shows recommendations
- [x] Timeout configuration inputs → Slider 5-120s with default indicators
- [x] Advanced options toggles → Query Templates + Location Preprocessing toggles

### Phase 5: Testing & Validation (Priority: High) 🔄 IN PROGRESS
- [x] Unit tests for ModelRouter → `tests/test_model_router.py` (220 lines)
- [x] Unit tests for QueryPreprocessor → `tests/test_query_preprocessor.py` (264 lines)
- [x] Unit tests for TemplateEngine → `tests/test_query_templates.py` (252 lines)
- [ ] Integration tests for per-task routing → Planned
- [ ] Performance benchmarks → Planned
- [ ] A/B testing framework → Future consideration

---

## API Endpoints

### GET /api/settings/models
Returns current model configuration.

### PUT /api/settings/models
Updates model configuration.

```json
{
  "model_sql_generation": "duckdb-nsql:latest",
  "model_narratives": "llama3.2:latest",
  "model_query_planning": "llama3.2:latest",
  "model_error_correction": "llama3.2:latest",
  "timeout_sql_generation": 30,
  "timeout_narratives": 15,
  "timeout_query_planning": 20,
  "timeout_error_correction": 15,
  "enable_query_templates": true,
  "enable_location_preprocessing": true,
  "enable_sample_values": true
}
```

### POST /api/settings/models/reset
Resets to default configuration.

---

## Configuration Environment Variables

```bash
# Default models (overridden by database settings)
MODEL_SQL_GENERATION=llama3.2:latest
MODEL_NARRATIVES=llama3.2:latest
MODEL_QUERY_PLANNING=llama3.2:latest
MODEL_ERROR_CORRECTION=llama3.2:latest

# Default timeouts
TIMEOUT_SQL_GENERATION=30
TIMEOUT_NARRATIVES=15
TIMEOUT_QUERY_PLANNING=20
TIMEOUT_ERROR_CORRECTION=15

# Feature flags
ENABLE_QUERY_TEMPLATES=true
ENABLE_LOCATION_PREPROCESSING=true
ENABLE_SAMPLE_VALUES=true
ENABLE_PER_TASK_MODELS=true
```

---

## Related Documentation

- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - **Phase 2 planning** (dialect support, prompt optimization, learning)
- [SQL_GENERATION_PIPELINE.md](SQL_GENERATION_PIPELINE.md) - Pipeline overview with template/preprocessing integration
- [CLAUDE.md](../../CLAUDE.md) - Main project documentation
- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Roadmap
- [SEMANTIC_CACHING.md](SEMANTIC_CACHING.md) - Caching system
- [TOOL_USING_AGENT.md](TOOL_USING_AGENT.md) - Tool system

---

## Changelog

- **2026-01-02**: Implementation complete (Phases 1-4), testing in progress (Phase 5)
  - ModelRouter service implemented with per-task model/timeout configuration
  - QueryPreprocessor with bidirectional location normalization
  - TemplateEngine with 10 query patterns bypassing LLM
  - ModelConfigPanel UI component with full configuration
  - 736 lines of test code across 3 test files
- **2025-12-30**: Initial documentation created
