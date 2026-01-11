# Prompt Optimization for Small Models

## Overview

This document describes the Prompt Optimization system (Phase 2.2) which intelligently compresses prompts to fit within smaller LLM context windows while preserving SQL generation accuracy.

---

## Architecture

### High-Level Flow

```
User Query + Schema
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MODEL DETECTION                              │
├─────────────────────────────────────────────────────────────────┤
│  1. Check KNOWN_MODEL_SIZES registry for exact match            │
│  2. Parse model name for size indicators (7b, 70b, etc.)        │
│  3. Detect model family (Llama, Qwen, Gemma, etc.)              │
│  4. Default to MEDIUM if unknown                                 │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TOKEN BUDGETING                              │
├─────────────────────────────────────────────────────────────────┤
│  Allocate tokens by model size:                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Component       │ SMALL  │ MEDIUM │ LARGE  │               ││
│  │─────────────────┼────────┼────────┼────────│               ││
│  │ System Prompt   │  400   │  600   │  1000  │               ││
│  │ Schema Context  │  800   │  1500  │  3000  │               ││
│  │ Examples        │   0    │  400   │  800   │               ││
│  │ History         │   0    │  300   │  500   │               ││
│  │ User Query      │  100   │  150   │  200   │               ││
│  │ Response Buffer │  700   │  1050  │  1500  │               ││
│  │─────────────────┼────────┼────────┼────────│               ││
│  │ TOTAL           │ ~2000  │ ~4000  │ ~7000  │               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SCHEMA COMPRESSION                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Keyword extraction from user question                        │
│  2. Table relevance scoring based on:                            │
│     - Keyword matches in table/column names                      │
│     - Foreign key relationships to matched tables                │
│  3. Select top N tables to fit token budget                      │
│  4. Generate compressed schema representation                    │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TEMPLATE FORMATTING                          │
├─────────────────────────────────────────────────────────────────┤
│  Apply model-specific prompt markers:                            │
│  - Llama:    <|start_header_id|>system<|end_header_id|>         │
│  - Qwen:     <|im_start|>system ... <|im_end|>                  │
│  - Gemma:    <start_of_turn>user ... <end_of_turn>              │
│  - Mistral:  [INST] instruction [/INST]                         │
│  - Phi:      <|system|> ... <|end|>                             │
│  - DuckDB:   ### Database Schema: ... ### SQL:                  │
│  - SQLCoder: ### Task ... ### Question ... ### SQL              │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OPTIMIZED PROMPT                             │
├─────────────────────────────────────────────────────────────────┤
│  OptimizedPrompt dataclass containing:                           │
│  - system_prompt: Compact task-specific instructions             │
│  - user_prompt: Question with compressed schema                  │
│  - compressed_schema: Relevant tables only                       │
│  - examples: 0-5 based on model size                            │
│  - metrics: Token counts, compression ratio                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Model Size Detection

#### Enum: `ModelSize`
Three tiers based on typical context window sizes:

| Size | Parameters | Typical Context | Token Budget |
|------|-----------|-----------------|--------------|
| `SMALL` | < 7B | < 4K | ~2000 tokens |
| `MEDIUM` | 7-13B | 4-8K | ~4000 tokens |
| `LARGE` | 13B+ | 8K+ | ~7000 tokens |

#### Known Model Registry (`KNOWN_MODEL_SIZES`)
Exact matches for common models:

```python
# Small models (< 7B)
"phi", "phi3", "tinyllama", "gemma:2b", "qwen2.5:3b", ...

# Medium models (7-13B)
"llama3.2", "llama3:8b", "gemma:7b", "mistral:7b", "duckdb-nsql", ...

# Large models (13B+)
"llama3:70b", "qwen2.5:32b", "gemma2:27b", "codellama:34b", ...
```

#### Auto-Detection Algorithm
If not in registry, parses model name:

```python
def get_model_size_for_model(model_name: str) -> ModelSize:
    # 1. Check exact match in KNOWN_MODEL_SIZES
    # 2. Parse for size indicators: "70b" → LARGE, "7b" → MEDIUM
    # 3. Default to MEDIUM
```

### 2. Model Family Detection

#### Enum: `ModelFamily`
Seven supported families with distinct training formats:

| Family | Example Models | Prompt Style |
|--------|----------------|--------------|
| `LLAMA` | llama3, llama2 | Chat with special tokens |
| `QWEN` | qwen2.5-coder | Chat with im_start/im_end |
| `GEMMA` | gemma, gemma2 | Turn-based format |
| `MISTRAL` | mistral, mixtral | [INST] markers |
| `PHI` | phi, phi3 | System/user/assistant tags |
| `DUCKDB_NSQL` | duckdb-nsql | Schema-focused SQL format |
| `SQLCODER` | sqlcoder | Task/Question/SQL format |

### 3. Token Budgeting

#### Dataclass: `PromptBudget`
Allocates tokens across prompt components:

```python
@dataclass
class PromptBudget:
    system_prompt: int    # Max tokens for system instructions
    schema_context: int   # Max tokens for schema definition
    examples: int         # Max tokens for few-shot examples
    history: int          # Max tokens for conversation history
    user_query: int       # Max tokens for user question
    buffer: int           # Reserved for LLM response
```

#### Budget Allocation by Size

| Component | SMALL | MEDIUM | LARGE |
|-----------|-------|--------|-------|
| System Prompt | 400 | 600 | 1000 |
| Schema Context | 800 | 1500 | 3000 |
| Examples | 0 | 400 | 800 |
| History | 0 | 300 | 500 |
| User Query | 100 | 150 | 200 |
| Response Buffer | 700 | 1050 | 1500 |
| **Total** | **2000** | **4000** | **7000** |

### 4. Schema Compression

#### Algorithm
1. **Keyword Extraction**: Extract nouns and technical terms from question
2. **Table Scoring**: Score each table by keyword matches
3. **Relationship Expansion**: Include foreign key related tables
4. **Selection**: Choose top tables within token budget
5. **Formatting**: Generate minimal schema representation

#### Example

```
Question: "Show customers in California"

Keywords: ["customers", "california"]

Table Scores:
  customers: 1.0 (direct match)
  orders: 0.3 (FK to customers)
  products: 0.0 (no match)
  categories: 0.0 (no match)

Selected Tables (SMALL budget):
  - customers (id, name, state, email)
  - orders (id, customer_id, total)  [via FK]
```

### 5. Model-Specific Templates

#### Dataclass: `ModelPromptTemplate`
Defines prompt formatting markers:

```python
@dataclass
class ModelPromptTemplate:
    system_prefix: str    # Start of system message
    system_suffix: str    # End of system message
    user_prefix: str      # Start of user message
    user_suffix: str      # End of user message
    assistant_prefix: str # Start of assistant response
    uses_chat_format: bool
```

#### Template Examples

**Llama 3:**
```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Generate PostgreSQL SQL. Rules:
- Only use tables from schema
- Return ONLY SQL, no explanation
- Use LIMIT for SELECT queries<|eot_id|>
<|start_header_id|>user<|end_header_id|>

Schema: ...
Question: Show all customers<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
```

**DuckDB-NSQL (SQL-specialized):**
```
### Database Schema:
CREATE TABLE customers (id INT, name VARCHAR, state VARCHAR);
CREATE TABLE orders (id INT, customer_id INT, total DECIMAL);

### Question:
Show all customers

### SQL:
```

### 6. Compact System Prompts

Task-specific prompts sized for each model tier:

#### SQL Generation Prompts

**SMALL (concise):**
```
Generate {dialect} SQL. Rules:
- Only use tables from schema
- Return ONLY SQL, no explanation
- Use LIMIT for SELECT queries
```

**MEDIUM (standard):**
```
You are a SQL generator. Generate valid {dialect} SQL.

Rules:
1. Only use tables/columns from the provided schema
2. Return ONLY the SQL query, no explanations
3. Use appropriate JOINs for multi-table queries
4. Include LIMIT for SELECT queries (default: 100)
5. For impossible queries, return: CANNOT_ANSWER: reason
```

**LARGE (detailed):**
```
You are an expert SQL developer specializing in {dialect}.

Your task is to convert natural language questions into valid SQL queries.

Critical Rules:
1. ONLY use tables and columns that exist in the provided schema
2. Return ONLY the SQL query - no explanations, no markdown
3. Use proper JOIN syntax for multi-table queries
4. Include LIMIT clause for SELECT queries (default: 100)
5. Use {dialect}-specific syntax for dates, strings, etc.
6. If the query cannot be answered with the given schema, return:
   CANNOT_ANSWER: [brief reason]

Output Format: Raw SQL only
```

---

## Token Counting

### Safety Margin
Token counting uses a 20% safety margin to account for SQL/code tokenization differences:

```python
def _count_tokens(text: str) -> int:
    """Estimate token count from text with safety margin."""
    if not text:
        return 0
    base_estimate = len(text) // 4  # ~4 chars per token
    # Add 20% safety margin for SQL keywords
    return int(base_estimate * 1.2)
```

### Why Safety Margin?
- SQL keywords may tokenize differently than English
- Special characters (parentheses, commas) affect token count
- Different tokenizers have varying behavior

---

## Integration Points

### 1. Quality Profile
The feature is controlled via `QualityProfile.enable_prompt_optimization`:

```python
# In quality_profile.py
@dataclass
class QualityProfile:
    enable_prompt_optimization: bool = False  # User opt-in
```

### 2. SQL Generator Integration
When enabled, the optimizer is called before LLM generation:

```python
# In sql_generator.py (lines 485-505)
if quality_profile.enable_prompt_optimization:
    optimizer = get_prompt_optimizer(model_name=model)
    optimized = optimizer.optimize_prompt(
        task="sql_generation",
        question=question,
        schema_dict=schema_dict,
        database_type=database_type,
    )
    # Use optimized.system_prompt, optimized.user_prompt
```

### 3. Settings API
Exposed via system settings:

```python
# In settings.py
enable_prompt_optimization: bool = Field(
    default=False,
    description="Enable prompt optimization for smaller models"
)
```

### 4. Frontend Toggle
UI toggle in `ModelConfigPanel.tsx`:

```typescript
<input
  type="checkbox"
  checked={settings.enable_prompt_optimization}
  onChange={(e) => updateSettings({ enable_prompt_optimization: e.target.checked })}
/>
```

---

## Data Flow

```
User enables toggle → SystemSettings DB → QualityProfile → SQLGenerator → PromptOptimizer
                                                                              ↓
                                                               OptimizedPrompt (compressed schema, examples)
                                                                              ↓
                                                                         LLM Call
```

---

## Configuration

### Environment Variables
None specific to prompt optimization. Uses existing:
- `OLLAMA_MODEL` - Default model for size detection
- `OLLAMA_BASE_URL` - Ollama server URL

### System Settings Fields
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_prompt_optimization` | bool | False | Enable/disable the feature |

### API Configuration
```bash
# Enable prompt optimization
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "enable_prompt_optimization": true
  }'
```

---

## Metrics & Observability

### OptimizedPrompt Metrics
Each optimization returns metadata:

```python
optimized.metrics = {
    "original_schema_tokens": 5000,
    "compressed_schema_tokens": 800,
    "compression_ratio": 0.16,
    "tables_included": 3,
    "tables_excluded": 12,
    "model_size": "MEDIUM",
    "model_family": "LLAMA",
}
```

### Logging
Detailed logging at DEBUG level:
```
DEBUG - Model llama3.2 detected as MEDIUM (8B params)
DEBUG - Schema compressed: 15 tables → 3 tables (800 tokens)
DEBUG - Using Llama template with chat format
```

---

## Test Coverage

### Test File: `tests/test_prompt_optimizer.py`
52 comprehensive tests covering:

| Category | Tests | Coverage |
|----------|-------|----------|
| Model size detection | 6 | Size inference from name patterns |
| Model family detection | 6 | Family matching from model names |
| Prompt budgets | 5 | Token allocation by size |
| Model templates | 5 | Template markers for each family |
| Compact system prompts | 4 | Task-specific prompt generation |
| Schema compression | 6 | Table selection and formatting |
| Example selection | 4 | Few-shot example picking |
| End-to-end optimization | 4 | Full pipeline testing |
| Template formatting | 2 | Prompt assembly |
| Factory functions | 4 | API convenience functions |
| Token counting | 3 | Estimation with safety margin |
| Edge cases | 3 | Empty inputs, unknown models |

**Run Tests:**
```bash
./run_tests.sh tests/test_prompt_optimizer.py
# 52 passed in 0.17s
```

---

## File Reference

| Component | File | Key Elements |
|-----------|------|--------------|
| Core Optimizer | `src/llm/prompt_optimizer.py` | `PromptOptimizer`, `OptimizedPrompt` |
| Model Size Registry | `src/llm/prompt_optimizer.py:144` | `PROMPT_BUDGETS` dict |
| Model Templates | `src/llm/prompt_optimizer.py:176` | `MODEL_TEMPLATES` dict |
| Compact Prompts | `src/llm/prompt_optimizer.py:248` | `COMPACT_SYSTEM_PROMPTS` dict |
| Known Models | `src/llm/prompt_optimizer.py:338` | `KNOWN_MODEL_SIZES` dict |
| Size Detection | `src/llm/prompt_optimizer.py:390` | `get_model_size_for_model()` |
| Family Detection | `src/llm/prompt_optimizer.py:430` | `get_model_family()` |
| Schema Compression | `src/llm/prompt_optimizer.py:550` | `compress_schema()` |
| Example Selection | `src/llm/prompt_optimizer.py:650` | `select_examples()` |
| Quality Profile | `src/llm/quality_profile.py:106` | `enable_prompt_optimization` field |
| Settings Schema | `src/models/schemas.py:478-484` | Pydantic field definitions |
| Frontend Toggle | `frontend/src/components/ModelConfigPanel.tsx` | UI checkbox |
| Tests | `tests/test_prompt_optimizer.py` | 52 comprehensive tests |

---

## Known Limitations

### 1. Singular/Plural Table Detection
The table matching uses simple `rstrip('s')` which may miss:
- Irregular plurals (e.g., "addresses" → "addres" instead of "address")
- Words ending in 's' that aren't plural

**Mitigation**: Falls back to exact matching if alias fails.

### 2. Token Counting Approximation
Uses 4 chars/token estimate with 20% buffer. May be less accurate for:
- Non-English text
- Highly technical SQL with many special characters
- Models with unusual tokenizers

**Mitigation**: Safety margin provides buffer; budget limits are conservative.

### 3. Schema Compression Trade-offs
Aggressive compression may exclude relevant tables:
- Indirect relationships (table A → B → C)
- Implicit relationships not captured in foreign keys

**Mitigation**: Always includes FK-related tables; users can disable optimization for complex queries.

---

## Future Improvements

### Planned Enhancements
1. **Adaptive Token Counting** - Use model-specific tokenizer when available
2. **Learning from Success** - Track which tables are actually used in successful queries
3. **Query-Type Specific Budgets** - Different allocations for aggregations vs. lookups
4. **Dynamic Example Selection** - Choose examples based on query similarity

### Performance Tracking
| Metric | Current | Target |
|--------|---------|--------|
| Token reduction | ~40% | 50% |
| Accuracy with small models | ~70% | 85% |
| Compression overhead | <10ms | <5ms |

---

## Conclusion

The Prompt Optimization system enables effective SQL generation with smaller, faster LLM models by:

1. **Intelligent Model Detection** - Auto-detects model size and family
2. **Token Budgeting** - Allocates tokens appropriately for context window
3. **Schema Compression** - Includes only relevant tables
4. **Model-Specific Templates** - Uses correct prompt formatting
5. **Safe Defaults** - Feature is opt-in with graceful fallback

This allows users to:
- Use smaller, faster models (phi3, gemma2:2b) for simple queries
- Reduce LLM costs and latency
- Maintain SQL generation accuracy

**Documentation:**
- [SQL Generation Pipeline](SQL_GENERATION_PIPELINE.md) - Overall pipeline architecture
- [Small Model Optimization Guide](../reports/SMALL_MODEL_OPTIMIZATION_PHASE_2_PR_REVIEW.md) - Phase 2 implementation
