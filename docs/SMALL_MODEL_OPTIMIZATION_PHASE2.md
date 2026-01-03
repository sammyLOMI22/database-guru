# Small Model Optimization - Phase 2

## Overview

This document outlines the next phase of optimizations for improving SQL generation quality with smaller LLMs. Building on Phase 1 (Model Router, Query Templates, Query Preprocessor), Phase 2 focuses on:

1. **Database-Specific Optimizations** - Dialect-aware SQL generation
2. **Prompt Engineering** - Token reduction and context optimization
3. **Model-Specific Tuning** - Tailored prompts per model family
4. **Advanced Preprocessing** - Beyond location normalization
5. **Learning & Adaptation** - Continuous improvement from usage

---

## Phase 1 Recap (Completed - January 2026)

| Component | Status | Impact |
|-----------|--------|--------|
| Model Router | ✅ Complete | Per-task model selection |
| Query Templates | ✅ Complete | ~20% queries bypass LLM |
| Query Preprocessor | ✅ Complete | Bidirectional location normalization |
| ModelConfigPanel UI | ✅ Complete | User-configurable models |
| Unit Tests | ✅ Complete | 736 lines of tests |

---

## Phase 2: Database-Specific Optimizations

### Problem Statement

Different databases have different SQL dialects, functions, and syntax. Small models often generate generic SQL that fails on specific databases.

**Critical Issue: Multi-Database Schema Differences**

When querying multiple databases simultaneously, each may have different schemas:

```
Query: "Show orders from California"

Database A (orders table HAS state column):
  ✅ SELECT * FROM orders WHERE state = 'CA'  → Works!

Database B (orders table has NO state column):
  ❌ SELECT * FROM orders WHERE state = 'CA'  → Error: column "state" does not exist
```

**Current behavior**: Same SQL sent to all databases, causing failures.
**Desired behavior**: Per-database SQL generation OR graceful "cannot answer" response.

**Current Issues Observed:**
```sql
-- PostgreSQL expects:
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days'

-- SQLite expects:
SELECT * FROM orders WHERE created_at > datetime('now', '-7 days')

-- MySQL expects:
SELECT * FROM orders WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)

-- DuckDB expects:
SELECT * FROM orders WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
```

### 2.1 Database Dialect Registry

**File:** `src/llm/dialect_registry.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

class DatabaseDialect(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    MONGODB = "mongodb"  # For future MQL generation

@dataclass
class DialectRules:
    """Database-specific SQL rules and syntax."""

    # Date/Time functions
    current_timestamp: str  # NOW(), CURRENT_TIMESTAMP, datetime('now')
    date_diff: str  # INTERVAL syntax or DATE_SUB
    date_format: str  # TO_CHAR, DATE_FORMAT, strftime

    # String functions
    concat: str  # ||, CONCAT(), +
    substring: str  # SUBSTRING, SUBSTR
    string_length: str  # LENGTH, LEN, CHAR_LENGTH
    case_insensitive: str  # ILIKE, LOWER() LIKE, COLLATE

    # Pagination
    limit_syntax: str  # LIMIT n, LIMIT n OFFSET m, TOP n
    offset_syntax: str  # OFFSET, SKIP

    # Boolean handling
    true_value: str  # TRUE, 1, 'true'
    false_value: str  # FALSE, 0, 'false'

    # NULL handling
    null_safe_equals: str  # IS NOT DISTINCT FROM, <=>
    coalesce: str  # COALESCE, IFNULL, NVL

    # Type casting
    cast_syntax: str  # CAST(x AS type), x::type, CONVERT()

    # JSON support
    json_extract: str  # ->, ->>, JSON_EXTRACT
    json_array: str  # JSON_BUILD_ARRAY, JSON_ARRAY

    # Array support (PostgreSQL, DuckDB)
    array_contains: str  # @>, ARRAY_CONTAINS
    array_length: str  # ARRAY_LENGTH, CARDINALITY

# Dialect configurations
DIALECT_RULES: Dict[DatabaseDialect, DialectRules] = {
    DatabaseDialect.POSTGRESQL: DialectRules(
        current_timestamp="CURRENT_TIMESTAMP",
        date_diff="INTERVAL '{n} {unit}'",
        date_format="TO_CHAR({col}, '{format}')",
        concat="||",
        substring="SUBSTRING({col} FROM {start} FOR {len})",
        string_length="LENGTH({col})",
        case_insensitive="ILIKE",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        true_value="TRUE",
        false_value="FALSE",
        null_safe_equals="IS NOT DISTINCT FROM",
        coalesce="COALESCE({args})",
        cast_syntax="{expr}::{type}",
        json_extract="{col}->'{key}'",
        json_array="JSON_BUILD_ARRAY({args})",
        array_contains="{col} @> ARRAY[{val}]",
        array_length="ARRAY_LENGTH({col}, 1)",
    ),
    DatabaseDialect.SQLITE: DialectRules(
        current_timestamp="datetime('now')",
        date_diff="datetime('now', '-{n} {unit}')",
        date_format="strftime('{format}', {col})",
        concat="||",
        substring="SUBSTR({col}, {start}, {len})",
        string_length="LENGTH({col})",
        case_insensitive="LIKE",  # SQLite LIKE is case-insensitive for ASCII
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        true_value="1",
        false_value="0",
        null_safe_equals="IS",  # Limited support
        coalesce="COALESCE({args})",
        cast_syntax="CAST({expr} AS {type})",
        json_extract="JSON_EXTRACT({col}, '$.{key}')",
        json_array="JSON_ARRAY({args})",
        array_contains="",  # Not supported
        array_length="",  # Not supported
    ),
    # ... MySQL and DuckDB configurations
}
```

### 2.2 Dialect-Aware Template Engine

Extend `TemplateEngine` to generate dialect-specific SQL:

```python
class DialectAwareTemplateEngine(TemplateEngine):
    """Generates database-specific SQL from templates."""

    def __init__(self, schema_dict: Dict, dialect: DatabaseDialect, default_limit: int = 100):
        super().__init__(schema_dict, default_limit)
        self.dialect = dialect
        self.rules = DIALECT_RULES[dialect]

    def _generate_date_filter(self, column: str, period: str, value: int) -> str:
        """Generate date filter for specific dialect."""
        if self.dialect == DatabaseDialect.POSTGRESQL:
            return f"{column} > CURRENT_TIMESTAMP - INTERVAL '{value} {period}'"
        elif self.dialect == DatabaseDialect.SQLITE:
            return f"{column} > datetime('now', '-{value} {period}')"
        elif self.dialect == DatabaseDialect.MYSQL:
            return f"{column} > DATE_SUB(NOW(), INTERVAL {value} {period.upper()})"
        elif self.dialect == DatabaseDialect.DUCKDB:
            return f"{column} > CURRENT_TIMESTAMP - INTERVAL '{value} {period}'"
```

### 2.3 Dialect Context in Prompts

Add dialect-specific instructions to LLM prompts:

```python
def build_dialect_context(dialect: DatabaseDialect) -> str:
    """Build dialect-specific prompt context."""

    contexts = {
        DatabaseDialect.POSTGRESQL: """
DATABASE: PostgreSQL
- Use double quotes for identifiers: "column_name"
- Boolean: TRUE/FALSE (not 1/0)
- Date math: INTERVAL '7 days'
- String concat: || operator
- Case-insensitive: ILIKE
- Arrays: ARRAY[1,2,3], @> for contains
- JSON: column->'key', column->>'key' for text
""",
        DatabaseDialect.SQLITE: """
DATABASE: SQLite
- Identifiers: no quotes needed or use double quotes
- Boolean: 1/0 (not TRUE/FALSE)
- Date math: datetime('now', '-7 days')
- String concat: || operator
- Case-insensitive: LIKE (for ASCII)
- No arrays or advanced JSON in older versions
- Use COALESCE for NULL handling
""",
        DatabaseDialect.MYSQL: """
DATABASE: MySQL
- Use backticks for identifiers: `column_name`
- Boolean: TRUE/FALSE or 1/0
- Date math: DATE_SUB(NOW(), INTERVAL 7 DAY)
- String concat: CONCAT(a, b) function
- Case-insensitive: LIKE (default collation)
- JSON: column->'$.key', JSON_EXTRACT
""",
        DatabaseDialect.DUCKDB: """
DATABASE: DuckDB
- PostgreSQL-compatible syntax
- Boolean: TRUE/FALSE
- Date math: INTERVAL '7 days'
- String concat: || operator
- Arrays: [1, 2, 3], list_contains()
- Excellent JSON support: column.key notation
- Supports QUALIFY for window functions
""",
    }
    return contexts.get(dialect, "")
```

### 2.4 Per-Database Query Intelligence (Multi-DB Fix)

**Problem**: When querying multiple databases, we generate ONE SQL and send it to ALL databases. This fails when schemas differ.

**Solution**: Pre-flight schema validation per database before execution.

**File:** `src/llm/multi_db_query_validator.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum

class QueryCapability(Enum):
    FULL = "full"           # Can answer completely
    PARTIAL = "partial"     # Can answer with modifications
    CANNOT = "cannot"       # Cannot answer at all

@dataclass
class DatabaseQueryAssessment:
    """Assessment of whether a database can answer a query."""
    connection_id: int
    connection_name: str
    capability: QueryCapability
    missing_tables: List[str]
    missing_columns: Dict[str, List[str]]  # table -> [columns]
    available_alternatives: Dict[str, str]  # missing -> suggested alternative
    suggested_sql: Optional[str]  # Modified SQL if PARTIAL
    reason: str

class MultiDatabaseQueryValidator:
    """Validates query feasibility across multiple databases."""

    def __init__(self, schemas: Dict[int, Dict]):
        """
        Args:
            schemas: Map of connection_id -> schema_dict
        """
        self.schemas = schemas

    def assess_query(self, question: str, base_sql: str) -> Dict[int, DatabaseQueryAssessment]:
        """
        Assess each database's ability to answer the query.

        Returns:
            Map of connection_id -> assessment
        """
        assessments = {}

        # Extract required tables/columns from base SQL
        required = self._extract_requirements(base_sql)

        for conn_id, schema in self.schemas.items():
            assessment = self._assess_database(conn_id, schema, required, question)
            assessments[conn_id] = assessment

        return assessments

    def _assess_database(self, conn_id: int, schema: Dict,
                        required: Dict, question: str) -> DatabaseQueryAssessment:
        """Assess a single database's capability."""

        tables = set(schema.get("tables", {}).keys())
        missing_tables = []
        missing_columns = {}
        alternatives = {}

        # Check required tables
        for table in required.get("tables", []):
            if table.lower() not in {t.lower() for t in tables}:
                missing_tables.append(table)
                # Try to find similar table
                similar = self._find_similar(table, tables)
                if similar:
                    alternatives[table] = similar

        # Check required columns
        for table, columns in required.get("columns", {}).items():
            table_schema = schema.get("tables", {}).get(table, {})
            available_cols = {c["name"].lower() for c in table_schema.get("columns", [])}

            for col in columns:
                if col.lower() not in available_cols:
                    if table not in missing_columns:
                        missing_columns[table] = []
                    missing_columns[table].append(col)

                    # Try to find similar column
                    similar = self._find_similar(col, available_cols)
                    if similar:
                        alternatives[f"{table}.{col}"] = similar

        # Determine capability
        if not missing_tables and not missing_columns:
            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=schema.get("name", f"DB {conn_id}"),
                capability=QueryCapability.FULL,
                missing_tables=[],
                missing_columns={},
                available_alternatives={},
                suggested_sql=None,
                reason="All required tables and columns available"
            )
        elif alternatives:
            # Can potentially answer with modifications
            suggested_sql = self._generate_alternative_sql(
                required, missing_tables, missing_columns, alternatives, schema
            )
            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=schema.get("name", f"DB {conn_id}"),
                capability=QueryCapability.PARTIAL,
                missing_tables=missing_tables,
                missing_columns=missing_columns,
                available_alternatives=alternatives,
                suggested_sql=suggested_sql,
                reason=f"Missing {len(missing_columns)} columns, but alternatives found"
            )
        else:
            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=schema.get("name", f"DB {conn_id}"),
                capability=QueryCapability.CANNOT,
                missing_tables=missing_tables,
                missing_columns=missing_columns,
                available_alternatives={},
                suggested_sql=None,
                reason=f"Missing required data: {missing_tables or missing_columns}"
            )
```

**Integration with Multi-Database Handler:**

```python
# In multi_db_handler.py - execute_multi_database_query()

async def execute_multi_database_query(self, question: str, ...):
    # Step 1: Generate base SQL from first/primary database
    base_sql = await self._generate_sql(question, primary_schema)

    # Step 2: Validate against all databases (NEW)
    validator = MultiDatabaseQueryValidator(all_schemas)
    assessments = validator.assess_query(question, base_sql)

    # Step 3: Execute per-database with appropriate SQL
    results = []
    for conn_id, assessment in assessments.items():
        if assessment.capability == QueryCapability.FULL:
            # Use base SQL
            result = await self._execute(conn_id, base_sql)
        elif assessment.capability == QueryCapability.PARTIAL:
            # Use suggested alternative SQL
            result = await self._execute(conn_id, assessment.suggested_sql)
            result.warning = f"Modified query: {assessment.reason}"
        else:
            # Return informative error instead of SQL error
            result = DatabaseQueryResult(
                success=False,
                error=f"Cannot answer: {assessment.reason}",
                missing_data=assessment.missing_columns,
                suggestion="This database doesn't have the required data"
            )
        results.append(result)

    return results
```

### 2.5 Schema Exploration UI

**Problem**: Users don't know what data is available before asking questions, leading to failed queries.

**Solution**: Interactive schema explorer that shows what's queryable.

> **Note**: This feature integrates with **Phase 7: ER Diagram Generator** from [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md)

#### Schema Explorer Panel

**File:** `frontend/src/components/SchemaExplorer.tsx`

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Schema Explorer                              [Expand All]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🔗 Production DB (PostgreSQL)                                  │
│  ├─ 📁 orders (15,432 rows)                                     │
│  │   ├─ id (INTEGER) [PK]                                       │
│  │   ├─ customer_id (INTEGER) [FK → customers.id]               │
│  │   ├─ order_date (TIMESTAMP)                                  │
│  │   ├─ total (DECIMAL)                                         │
│  │   └─ state (VARCHAR) ← Values: 'CA', 'NY', 'TX'...           │
│  │                                                               │
│  ├─ 📁 customers (2,150 rows)                                   │
│  │   ├─ id (INTEGER) [PK]                                       │
│  │   ├─ name (VARCHAR)                                          │
│  │   └─ email (VARCHAR)                                         │
│  │                                                               │
│  🔗 Analytics DB (DuckDB)                                       │
│  ├─ 📁 orders (45,000 rows)                                     │
│  │   ├─ id (INTEGER) [PK]                                       │
│  │   ├─ customer_id (INTEGER)                                   │
│  │   ├─ order_date (DATE)                                       │
│  │   └─ total (DOUBLE)                                          │
│  │   ⚠️ No location column (state/city/country)                 │
│  │                                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  💡 Schema Comparison                                     │   │
│  │  • 'state' column: Only in Production DB                 │   │
│  │  • Location queries will only work on Production DB      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [🔍 Search columns...]  [📊 View ER Diagram]  [📋 Copy Schema] │
└─────────────────────────────────────────────────────────────────┘
```

#### Schema Comparison View

**File:** `frontend/src/components/SchemaComparison.tsx`

```
┌─────────────────────────────────────────────────────────────────┐
│  🔄 Schema Comparison: Production DB vs Analytics DB            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Table: orders                                                ││
│  ├──────────────────┬──────────────────┬───────────────────────┤│
│  │ Column           │ Production DB    │ Analytics DB          ││
│  ├──────────────────┼──────────────────┼───────────────────────┤│
│  │ id               │ ✅ INTEGER       │ ✅ INTEGER            ││
│  │ customer_id      │ ✅ INTEGER [FK]  │ ✅ INTEGER            ││
│  │ order_date       │ ✅ TIMESTAMP     │ ✅ DATE               ││
│  │ total            │ ✅ DECIMAL       │ ✅ DOUBLE             ││
│  │ state            │ ✅ VARCHAR       │ ❌ Missing            ││
│  │ shipping_address │ ✅ TEXT          │ ❌ Missing            ││
│  └──────────────────┴──────────────────┴───────────────────────┘│
│                                                                  │
│  📋 Query Compatibility:                                        │
│  • "Show all orders" → ✅ Both databases                        │
│  • "Orders from California" → ⚠️ Production only               │
│  • "Total by customer" → ✅ Both databases                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Query Feasibility Indicator

Show users BEFORE they submit which databases can answer their question:

**File:** `frontend/src/components/QueryFeasibilityBadge.tsx`

```
┌─────────────────────────────────────────────────────────────────┐
│  Ask a question about your data                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Show me orders from California                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Query Feasibility:                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ✅ Production DB - Can answer (has 'state' column)          ││
│  │ ⚠️ Analytics DB - Cannot filter by location                 ││
│  │    Missing: orders.state                                     ││
│  │    💡 Try: "Show me all orders" (works on both)              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  [Submit Query - Results from 1 of 2 databases]                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Integration with Phase 7 ER Diagrams

The Schema Explorer should integrate with the planned ER Diagram Generator:

```
┌─────────────────────────────────────────────────────────────────┐
│  Schema Explorer                                                │
│  ┌──────────┬──────────┬──────────┬──────────┐                 │
│  │ 📋 List  │ 🔄 Compare│ 📊 ER    │ 🔍 Search │                 │
│  │  View    │  View    │ Diagram  │  Columns │                 │
│  └──────────┴──────────┴──────────┴──────────┘                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [ER Diagram View - from Phase 7]                               │
│                                                                  │
│  ┌──────────┐         ┌───────────┐         ┌──────────┐       │
│  │ customers│─────────│  orders   │─────────│ products │       │
│  │          │   1:N   │           │   N:M   │          │       │
│  │ • id [PK]│         │ • id [PK] │         │ • id [PK]│       │
│  │ • name   │         │ • cust_id │         │ • name   │       │
│  │ • email  │         │ • total   │         │ • price  │       │
│  │          │         │ • state ⚠️│         │          │       │
│  └──────────┘         └───────────┘         └──────────┘       │
│                                                                  │
│  Legend: ⚠️ = Column not in all databases                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 2: Prompt Engineering Optimizations

### Problem Statement

Small models have limited context windows and struggle with long prompts. Current prompts may include unnecessary information, wasting tokens.

**Token Analysis (Current State):**
| Prompt Component | Approx Tokens | Necessity |
|-----------------|---------------|-----------|
| System prompt | 800-1200 | Required |
| Schema context | 500-2000 | Varies by DB |
| Few-shot examples | 400-800 | Often redundant |
| Conversation history | 200-500 | Sometimes needed |
| **Total** | **1900-4500** | Can reduce by 40% |

### 3.1 Dynamic Prompt Compression

**File:** `src/llm/prompt_optimizer.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class ModelSize(Enum):
    SMALL = "small"      # < 7B params, < 4K context
    MEDIUM = "medium"    # 7-13B params, 4-8K context
    LARGE = "large"      # 13B+ params, 8K+ context

@dataclass
class PromptBudget:
    """Token budget allocation for prompt components."""
    system_prompt: int
    schema_context: int
    examples: int
    history: int
    user_query: int
    buffer: int  # Reserved for response

    @property
    def total(self) -> int:
        return sum([
            self.system_prompt, self.schema_context,
            self.examples, self.history, self.user_query, self.buffer
        ])

# Budget allocations by model size
PROMPT_BUDGETS: Dict[ModelSize, PromptBudget] = {
    ModelSize.SMALL: PromptBudget(
        system_prompt=400,    # Minimal instructions
        schema_context=800,   # Essential tables only
        examples=0,           # Zero-shot for small models
        history=0,            # No conversation history
        user_query=100,
        buffer=700,           # Reserve for SQL output
    ),  # Total: 2000 tokens

    ModelSize.MEDIUM: PromptBudget(
        system_prompt=600,
        schema_context=1500,
        examples=400,         # 2-3 examples
        history=300,
        user_query=150,
        buffer=1050,
    ),  # Total: 4000 tokens

    ModelSize.LARGE: PromptBudget(
        system_prompt=1000,
        schema_context=3000,
        examples=800,         # 4-5 examples
        history=500,
        user_query=200,
        buffer=1500,
    ),  # Total: 7000 tokens
}

class PromptOptimizer:
    """Optimizes prompts based on model size and context budget."""

    def __init__(self, model_size: ModelSize):
        self.model_size = model_size
        self.budget = PROMPT_BUDGETS[model_size]

    def compress_schema(self, schema_dict: Dict, question: str) -> str:
        """Compress schema to fit budget, prioritizing relevant tables."""
        # 1. Extract entities from question
        mentioned_tables = self._extract_table_mentions(question, schema_dict)

        # 2. Add related tables (FK relationships)
        related_tables = self._get_related_tables(mentioned_tables, schema_dict)

        # 3. Build compressed schema with only relevant tables
        relevant_tables = mentioned_tables | related_tables

        # 4. If still under budget, add remaining tables as list
        return self._format_compressed_schema(schema_dict, relevant_tables)

    def select_examples(self, question: str, available_examples: List[Dict]) -> List[Dict]:
        """Select most relevant examples within budget."""
        if self.budget.examples == 0:
            return []  # Zero-shot for small models

        # Score examples by relevance to question
        scored = []
        for ex in available_examples:
            score = self._compute_relevance(question, ex)
            scored.append((score, ex))

        # Select top examples within token budget
        scored.sort(reverse=True)
        selected = []
        tokens_used = 0

        for score, ex in scored:
            ex_tokens = self._count_tokens(ex)
            if tokens_used + ex_tokens <= self.budget.examples:
                selected.append(ex)
                tokens_used += ex_tokens

        return selected
```

### 3.2 Model-Specific Prompt Templates

Different models respond better to different prompt formats:

```python
# Prompt templates optimized for different model families
PROMPT_TEMPLATES = {
    "llama": {
        "system": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|>",
        "user": "<|start_header_id|>user<|end_header_id|>\n{user}<|eot_id|>",
        "assistant": "<|start_header_id|>assistant<|end_header_id|>\n",
    },
    "qwen": {
        "system": "<|im_start|>system\n{system}<|im_end|>",
        "user": "<|im_start|>user\n{user}<|im_end|>",
        "assistant": "<|im_start|>assistant\n",
    },
    "duckdb-nsql": {
        # Specialized SQL model - minimal prompting
        "system": "Generate SQL for the following schema and question.",
        "user": "Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:",
        "assistant": "",
    },
    "sqlcoder": {
        # Another SQL-specialized model
        "system": "### Task\nGenerate a SQL query to answer the question.\n\n### Database Schema\n{schema}",
        "user": "### Question\n{question}\n\n### SQL",
        "assistant": "",
    },
    "gemma": {
        "system": "<start_of_turn>user\n{system}\n{user}<end_of_turn>",
        "user": "",
        "assistant": "<start_of_turn>model\n",
    },
    "default": {
        "system": "{system}",
        "user": "{user}",
        "assistant": "",
    },
}

def get_model_template(model_name: str) -> Dict[str, str]:
    """Get prompt template for specific model."""
    model_lower = model_name.lower()

    for prefix, template in PROMPT_TEMPLATES.items():
        if prefix in model_lower:
            return template

    return PROMPT_TEMPLATES["default"]
```

### 3.3 Compact System Prompts by Task

Different tasks need different system prompts:

```python
COMPACT_SYSTEM_PROMPTS = {
    "sql_generation": {
        ModelSize.SMALL: """
Generate SQL. Rules:
- Only use tables from schema
- Return ONLY SQL, no explanation
- Use {dialect} syntax
""",
        ModelSize.MEDIUM: """
You are a SQL generator. Generate valid {dialect} SQL.

Rules:
1. Only use tables/columns from the provided schema
2. Return ONLY the SQL query, no explanations
3. Use appropriate JOINs for multi-table queries
4. Include LIMIT for SELECT queries (default: 100)
5. For impossible queries, return: CANNOT_ANSWER: reason
""",
        ModelSize.LARGE: """
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
""",
    },

    "error_correction": {
        ModelSize.SMALL: """
Fix the SQL error. Return only corrected SQL.
Error: {error}
""",
        ModelSize.MEDIUM: """
Fix this SQL error. Return only the corrected SQL query.

Error: {error}
Original SQL: {sql}

Common fixes:
- Check table/column names against schema
- Fix syntax for {dialect}
- Correct JOIN conditions
""",
    },

    "narratives": {
        ModelSize.SMALL: """
Summarize query results in 1-2 sentences.
""",
        ModelSize.MEDIUM: """
Summarize the query results. Include:
- Direct answer to the question
- Key statistics if numeric data
- Notable patterns

Keep response under 100 words.
""",
    },
}
```

---

## Phase 2: Advanced Preprocessing

### 4.1 Entity Type Normalization

Extend preprocessing beyond locations:

```python
@dataclass
class EntityNormalization:
    """Normalized entity with original and database-compatible forms."""
    original: str
    normalized: str
    entity_type: str  # "location", "date", "currency", "boolean", "status"
    confidence: float
    column_hint: Optional[str] = None

class AdvancedPreprocessor(QueryPreprocessor):
    """Extended preprocessor with multi-entity normalization."""

    def preprocess(self, question: str) -> PreprocessedQuery:
        result = super().preprocess(question)

        # Additional normalizations
        result = self._normalize_dates(result)
        result = self._normalize_booleans(result)
        result = self._normalize_currency(result)
        result = self._normalize_status_values(result)

        return result

    def _normalize_dates(self, result: PreprocessedQuery) -> PreprocessedQuery:
        """Normalize date expressions to SQL-compatible forms."""
        patterns = {
            r"last (\d+) days?": lambda m: f"created_at > datetime('now', '-{m.group(1)} days')",
            r"this month": "strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
            r"yesterday": "date(created_at) = date('now', '-1 day')",
            r"today": "date(created_at) = date('now')",
            r"this year": "strftime('%Y', created_at) = strftime('%Y', 'now')",
            r"last year": "strftime('%Y', created_at) = strftime('%Y', 'now', '-1 year')",
            r"(\d{1,2})/(\d{1,2})/(\d{4})": lambda m: f"'{m.group(3)}-{m.group(1):0>2}-{m.group(2):0>2}'",
        }
        # Apply patterns and add to enhanced context
        return result

    def _normalize_booleans(self, result: PreprocessedQuery) -> PreprocessedQuery:
        """Normalize boolean expressions."""
        boolean_mappings = {
            # True values
            "active": ("status", "active"),
            "enabled": ("is_enabled", "1"),
            "yes": ("is_active", "1"),
            "available": ("is_available", "1"),

            # False values
            "inactive": ("status", "inactive"),
            "disabled": ("is_enabled", "0"),
            "no": ("is_active", "0"),
            "unavailable": ("is_available", "0"),
        }
        # Detect and normalize
        return result

    def _normalize_status_values(self, result: PreprocessedQuery) -> PreprocessedQuery:
        """Normalize status-related terms to database values."""
        # Detect status column in schema and sample its values
        # Map common terms to actual values:
        # "shipped" → "SHIPPED" or "shipped" depending on DB
        # "pending" → "PENDING" or "pending"
        # "completed" → "COMPLETED" or "complete" or "done"
        return result
```

### 4.2 Schema-Aware Column Value Detection

Detect column format from sample values:

```python
class ColumnFormatDetector:
    """Detects data format patterns in columns."""

    def detect_format(self, column_name: str, sample_values: List) -> Dict:
        """Analyze sample values to determine format."""
        if not sample_values:
            return {"format": "unknown"}

        # Check for common patterns
        formats = {
            "location_code": self._is_location_code(sample_values),
            "location_full": self._is_location_full(sample_values),
            "date_iso": self._is_date_iso(sample_values),
            "date_us": self._is_date_us(sample_values),
            "boolean_numeric": self._is_boolean_numeric(sample_values),
            "boolean_text": self._is_boolean_text(sample_values),
            "status_upper": self._is_status_upper(sample_values),
            "status_lower": self._is_status_lower(sample_values),
            "currency_symbol": self._is_currency_with_symbol(sample_values),
            "currency_numeric": self._is_currency_numeric(sample_values),
        }

        # Return detected format with confidence
        detected = [(k, v) for k, v in formats.items() if v > 0.7]
        return {
            "format": detected[0][0] if detected else "unknown",
            "confidence": detected[0][1] if detected else 0.0,
            "sample_values": sample_values[:5],
        }
```

---

## Phase 2: Learning & Adaptation

### 5.1 Query Pattern Learning

Learn successful patterns from executed queries:

```python
@dataclass
class LearnedPattern:
    """A learned SQL generation pattern."""
    question_pattern: str  # Regex or template
    sql_template: str
    table_pattern: str
    success_count: int
    failure_count: int
    last_used: datetime
    dialect: str

    @property
    def confidence(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total

class PatternLearner:
    """Learns SQL patterns from successful queries."""

    def learn_from_success(self, question: str, sql: str,
                          schema: Dict, dialect: str):
        """Extract and store patterns from successful query."""
        # 1. Generalize the question
        pattern = self._generalize_question(question)

        # 2. Templatize the SQL
        template = self._templatize_sql(sql, schema)

        # 3. Store or update pattern
        self._store_pattern(pattern, template, dialect)

    def try_apply_pattern(self, question: str, schema: Dict,
                         dialect: str) -> Optional[str]:
        """Try to apply learned pattern to new question."""
        # Find matching patterns
        matches = self._find_matching_patterns(question, dialect)

        # Apply best pattern if confidence is high
        for pattern in matches:
            if pattern.confidence > 0.8:
                sql = self._apply_template(pattern.sql_template,
                                          question, schema)
                if sql:
                    return sql
        return None
```

### 5.2 Model Performance Tracking

Track which models perform best for which tasks:

```python
@dataclass
class ModelPerformance:
    """Tracks performance metrics for a model on a task."""
    model_name: str
    task_type: str
    total_attempts: int
    successful_attempts: int
    avg_latency_ms: float
    avg_tokens_used: int
    last_updated: datetime

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts

class ModelPerformanceTracker:
    """Tracks and optimizes model selection based on performance."""

    def record_attempt(self, model: str, task: str, success: bool,
                      latency_ms: float, tokens: int):
        """Record a model attempt."""
        pass

    def get_best_model(self, task: str,
                       min_success_rate: float = 0.7) -> Optional[str]:
        """Get best performing model for a task."""
        pass

    def get_performance_report(self) -> Dict:
        """Generate performance report for all models."""
        pass
```

---

## Implementation Phases

### Phase 2.1: Database Dialect Support (Priority: High)
- [ ] Create `DialectRegistry` with rules for PostgreSQL, MySQL, SQLite, DuckDB
- [ ] Update `TemplateEngine` to generate dialect-specific SQL
- [ ] Add dialect context to LLM prompts
- [ ] Update tests for each dialect
- [ ] Add dialect selection in connection settings UI

### Phase 2.2: Prompt Optimization (Priority: High)
- [ ] Implement `PromptOptimizer` with token budgets
- [ ] Create model-specific prompt templates
- [ ] Add compact system prompts by task and model size
- [ ] Implement schema compression for large databases
- [ ] Benchmark token usage before/after

### Phase 2.3: Advanced Preprocessing (Priority: Medium)
- [ ] Extend `QueryPreprocessor` for date normalization
- [ ] Add boolean and status value normalization
- [ ] Implement `ColumnFormatDetector`
- [ ] Add currency and unit handling
- [ ] Update UI to show detected normalizations

### Phase 2.4: Per-Database Query Intelligence (Priority: Critical)
- [ ] Implement `MultiDatabaseQueryValidator` class
- [ ] Create `QueryCapability` assessment (FULL/PARTIAL/CANNOT)
- [ ] Build schema comparison logic for multi-database queries
- [ ] Add alternative column detection (fuzzy matching for similar columns)
- [ ] Create per-database SQL generation (different SQL for different schemas)
- [ ] Implement pre-flight validation before query execution
- [ ] Add `DatabaseQueryAssessment` to API responses
- [ ] Create unit tests for schema comparison logic
- [ ] Integration tests with multiple databases having different schemas

### Phase 2.5: Schema Exploration UI (Priority: High)
- [ ] Implement `SchemaExplorer.tsx` component with table browser
- [ ] Add column details with types, PKs, FKs, and sample values
- [ ] Create `SchemaComparison.tsx` for multi-database comparison view
- [ ] Build `QueryFeasibilityBadge.tsx` for real-time query assessment
- [ ] Add schema refresh button and last-updated timestamps
- [ ] Implement search/filter functionality for tables and columns
- [ ] Create schema export functionality (JSON/CSV)
- [ ] Add integration with connection manager
- [ ] Frontend tests for all schema exploration components

### Phase 2.6: Learning System (Priority: Medium)
- [ ] Implement `PatternLearner` for successful queries
- [ ] Create database table for learned patterns
- [ ] Add pattern matching to query flow
- [ ] Implement `ModelPerformanceTracker`
- [ ] Create analytics dashboard for patterns

### Phase 2.7: Integration with ER Diagrams (Priority: Medium)
- [ ] Connect Schema Exploration to Phase 7 ER Diagram work
- [ ] Link SchemaExplorer to ER visualization component
- [ ] Add click-to-explore from ER diagram entities
- [ ] Implement shared schema data model between features
- [ ] Ensure consistent styling and UX patterns

### Phase 2.8: Testing & Validation (Priority: High)
- [ ] Integration tests for all dialects
- [ ] Performance benchmarks (tokens, latency, accuracy)
- [ ] A/B testing framework for prompt variants
- [ ] Load testing with multiple databases
- [ ] Multi-database schema validation tests
- [ ] Schema exploration E2E tests

---

## Expected Improvements

| Metric | Phase 1 | Phase 2 Target |
|--------|---------|----------------|
| First-attempt SQL success | ~70% | 85% |
| Template match rate | ~20% | ~35% (with patterns) |
| Token usage per query | ~3000 | ~1800 (40% reduction) |
| Dialect-specific accuracy | ~60% | ~90% |
| Date query accuracy | ~50% | ~90% |
| Average latency | ~2.5s | ~1.8s |
| **Multi-DB query success** | ~50% | ~90% (with pre-validation) |
| **Schema mismatch detection** | 0% | 100% (pre-flight check) |
| **User schema understanding** | Low | High (with exploration UI) |

---

## API Additions

### GET /api/settings/dialect
Returns dialect configuration for a connection.

### PUT /api/settings/prompt-optimization
Updates prompt optimization settings.

```json
{
  "model_size": "small",
  "enable_schema_compression": true,
  "enable_example_selection": true,
  "max_examples": 3
}
```

### GET /api/analytics/model-performance
Returns model performance metrics.

### GET /api/analytics/learned-patterns
Returns learned query patterns with statistics.

### POST /api/query/validate-multi-db
Pre-validates a query against multiple database schemas.

```json
{
  "question": "Show orders by state",
  "connection_ids": [1, 2, 3]
}
```

Response:
```json
{
  "assessments": [
    {
      "connection_id": 1,
      "connection_name": "Sales DB",
      "capability": "full",
      "missing_tables": [],
      "missing_columns": {},
      "suggested_sql": "SELECT state, COUNT(*) FROM orders GROUP BY state"
    },
    {
      "connection_id": 2,
      "connection_name": "Warehouse DB",
      "capability": "cannot",
      "missing_tables": [],
      "missing_columns": {"orders": ["state"]},
      "available_alternatives": {"state": "region"},
      "reason": "Column 'state' not found in orders table. Alternative: 'region'"
    }
  ],
  "overall_capability": "partial"
}
```

### GET /api/schema/explore/{connection_id}
Returns full schema exploration data for a connection.

```json
{
  "tables": [
    {
      "name": "orders",
      "columns": [
        {"name": "id", "type": "INTEGER", "pk": true, "nullable": false},
        {"name": "customer_id", "type": "INTEGER", "fk": "customers.id"},
        {"name": "state", "type": "VARCHAR(2)", "sample_values": ["CA", "NY", "TX"]}
      ],
      "row_count": 15420,
      "relationships": ["customers", "order_items"]
    }
  ],
  "last_updated": "2026-01-03T10:30:00Z"
}
```

### GET /api/schema/compare
Compares schemas across multiple connections.

```json
{
  "connection_ids": [1, 2],
  "tables": ["orders", "customers"]
}
```

Response shows column differences, type mismatches, and missing elements.

---

## Configuration

```bash
# Prompt optimization
PROMPT_OPTIMIZATION_ENABLED=true
MODEL_SIZE_DETECTION=auto  # auto, small, medium, large
SCHEMA_COMPRESSION_ENABLED=true
MAX_SCHEMA_TABLES=20  # Compress if more tables

# Dialect handling
DIALECT_CONTEXT_ENABLED=true
DIALECT_TEMPLATE_STRICT=true  # Fail on unsupported dialect features

# Pattern learning
PATTERN_LEARNING_ENABLED=true
MIN_PATTERN_CONFIDENCE=0.8
MAX_PATTERNS_PER_DIALECT=1000

# Performance tracking
PERFORMANCE_TRACKING_ENABLED=true
PERFORMANCE_REPORT_INTERVAL=3600  # seconds
```

---

## Related Documentation

- [SMALL_MODEL_OPTIMIZATION.md](SMALL_MODEL_OPTIMIZATION.md) - Phase 1 documentation
- [SQL_GENERATION_PIPELINE.md](SQL_GENERATION_PIPELINE.md) - Pipeline overview
- [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md) - Phase 7 ER Diagrams (integrates with Schema Exploration)
- [MULTI_DATABASE_GUIDE.md](MULTI_DATABASE_GUIDE.md) - Multi-database query guide
- [CLAUDE.md](../CLAUDE.md) - Project documentation

---

## Changelog

- **2026-01-03**: Added Phase 2.4 Per-Database Query Intelligence (multi-DB schema validation)
- **2026-01-03**: Added Phase 2.5 Schema Exploration UI (user-facing schema browser)
- **2026-01-03**: Added Phase 2.7 Integration with ER Diagrams (links to Phase 7)
- **2026-01-03**: Updated Implementation Phases (now 8 phases total)
- **2026-01-03**: Added new API endpoints for schema exploration and multi-DB validation
- **2026-01-03**: Updated Expected Improvements with multi-DB metrics
- **2026-01-02**: Initial Phase 2 planning document created
