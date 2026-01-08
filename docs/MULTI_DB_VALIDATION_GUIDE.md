# Multi-Database Query Validation Guide

## Overview

The Multi-Database Query Validation system (Phase 2.4) provides **pre-flight validation** for queries across multiple databases with different schemas. Instead of blindly executing the same SQL on all databases and getting errors, the system:

1. Assesses each database's capability to answer the query
2. Shows users which databases can/cannot answer before execution
3. Suggests alternatives when columns are missing
4. Generates per-database SQL when schemas differ

**Key Benefits:**
- Prevents wasted execution on incompatible databases
- Provides clear "Cannot Answer" feedback instead of cryptic errors
- Enables intelligent multi-database querying across heterogeneous schemas

---

## Architecture

### Component Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         User Question                               │
│                    "Show orders from California"                    │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│              MultiDatabaseQueryValidator                            │
│  src/llm/multi_db_query_validator.py                               │
├────────────────────────────────────────────────────────────────────┤
│  1. Parse SQL requirements (sqlparse)                              │
│  2. Extract tables, columns, values needed                          │
│  3. Validate against each database schema                          │
│  4. Find alternatives for missing columns                          │
│  5. Return per-database capability assessment                      │
└────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌─────────┐   ┌─────────┐   ┌─────────┐
              │ Sales   │   │Inventory│   │Products │
              │   DB    │   │   DB    │   │   DB    │
              ├─────────┤   ├─────────┤   ├─────────┤
              │ orders  │   │ orders  │   │products │
              │  .state │   │ .region │   │  (no    │
              │         │   │         │   │location)│
              ├─────────┤   ├─────────┤   ├─────────┤
              │  FULL   │   │ PARTIAL │   │ CANNOT  │
              └─────────┘   └─────────┘   └─────────┘
                    │             │             │
                    ▼             ▼             ▼
┌────────────────────────────────────────────────────────────────────┐
│              MultiDatabaseAssessment (React)                        │
│  frontend/src/components/MultiDatabaseAssessment.tsx               │
├────────────────────────────────────────────────────────────────────┤
│  - Shows all databases with capability badges                       │
│  - Auto-selects FULL and PARTIAL databases                         │
│  - Disables CANNOT databases with reason                           │
│  - User can deselect databases before execution                    │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│              Parallel Execution (Selected DBs Only)                 │
│  src/core/multi_db_handler.py                                      │
├────────────────────────────────────────────────────────────────────┤
│  - FULL: Execute original SQL                                      │
│  - PARTIAL: Execute suggested_sql with alternatives                │
│  - CANNOT: Skip, return informative error                          │
└────────────────────────────────────────────────────────────────────┘
```

---

## Query Capability Assessment

### Capability Levels

| Level | Description | Action | UI |
|-------|-------------|--------|-----|
| **FULL** | All required tables/columns exist | Execute original SQL | ✅ Green, auto-selected |
| **PARTIAL** | Missing columns but alternatives found | Execute modified SQL | 🟡 Amber, auto-selected |
| **CANNOT** | Missing required data, no alternatives | Skip with error | ❌ Red, disabled |

### Assessment Process

1. **Parse SQL Requirements**
   ```python
   # Uses sqlparse for production-grade parsing
   required = {
       "tables": {"orders"},
       "columns": {"orders": {"id", "state", "amount"}},
       "needs_location": True,
       "detected_locations": ["california"]
   }
   ```

2. **Validate Against Schema**
   ```python
   # Check each table exists
   for table in required["tables"]:
       if table not in schema_tables:
           missing_tables.append(table)

   # Check each column exists
   for table, columns in required["columns"].items():
       for column in columns:
           if column not in schema_columns[table]:
               missing_columns[table].append(column)
   ```

3. **Find Alternatives**
   ```python
   # Common alternatives mapping
   COMMON_ALTERNATIVES = {
       "state": ["region", "province", "territory", "state_code"],
       "price": ["cost", "amount", "unit_price", "total_price"],
   }

   # Also fuzzy matching with SequenceMatcher
   # "state" → "us_state" (similarity > 0.6)
   ```

4. **Determine Capability**
   ```python
   if missing_tables:
       capability = CANNOT
   elif missing_columns and not alternatives_found:
       capability = CANNOT
   elif missing_columns and alternatives_found:
       capability = PARTIAL
   else:
       capability = FULL
   ```

---

## When to Use Pre-Flight vs Post-Execution

### Pre-Flight Validation (Before Execution)

Use pre-flight validation when:
- Querying **multiple databases** with potentially different schemas
- User needs to see which databases are **relevant** before waiting
- Schema differences are **expected** (e.g., regional databases)
- You want **graceful degradation** rather than errors

```python
# Pre-flight validation
validation_result = validator.validate_query(
    sql="SELECT * FROM orders WHERE state = 'CA'",
    question="Show orders from California",
    schemas=all_database_schemas
)

# User sees: "3 databases can answer, 2 cannot"
# User chooses which to execute
```

### Post-Execution Errors (After Execution)

Use post-execution errors when:
- Querying **single database** only
- Schema is **known and stable**
- Errors are **unexpected** (bugs, not schema differences)
- You need **detailed error messages** for debugging

```python
# Post-execution error
try:
    result = executor.execute(sql)
except Exception as e:
    # "Column 'state' does not exist in table 'orders'"
    return {"error": str(e)}
```

---

## PARTIAL Capability Flow

When a database has PARTIAL capability, the system:

1. **Identifies Missing Columns**
   ```python
   missing = {"orders": ["state"]}
   ```

2. **Finds Alternatives**
   ```python
   alternatives = {"orders.state": "region"}
   ```

3. **Generates Modified SQL**
   ```python
   # Original: SELECT * FROM orders WHERE state = 'CA'
   # Modified: SELECT * FROM orders WHERE region = 'CA'
   suggested_sql = "SELECT * FROM orders WHERE region = 'CA'"
   ```

4. **Adds LLM Hints**
   ```python
   # Appended to question for LLM context
   hint = "Note: This database uses 'region' instead of 'state'"
   ```

5. **Executes Modified Query**
   ```python
   # PARTIAL databases execute suggested_sql, not original
   result = execute(
       sql=assessment.suggested_sql,  # Modified SQL
       connection_id=assessment.connection_id
   )
   ```

---

## Performance Characteristics

### Validation Performance

| Operation | Time | Notes |
|-----------|------|-------|
| SQL Parsing (sqlparse) | ~5ms | Cached after first parse |
| Schema Validation | ~2ms/database | Scales linearly with databases |
| Fuzzy Matching | ~10ms/missing column | Only runs for missing columns |
| Total (10 databases) | ~50-100ms | Negligible vs execution time |

### When to Skip Validation

Skip validation for performance when:
- Single database query
- Schema is cached and known to be compatible
- Query pattern is known-good (template match)

```python
# Fast path: skip validation for known-good patterns
if template_engine.try_match(question):
    # Template matched, execute directly
    return execute_template(...)
```

### Parallel Execution Performance

| Databases | Serial Time | Parallel Time | Speedup |
|-----------|-------------|---------------|---------|
| 2 | 2s | 1s | 2x |
| 5 | 5s | 1.2s | ~4x |
| 10 | 10s | 1.5s | ~7x |

Limited by `MAX_PARALLEL_DATABASES` (default: 10) to prevent resource exhaustion.

---

## Troubleshooting

### Common Issues

#### 1. "CANNOT" for queries that should work

**Symptom:** Database marked CANNOT but query should work

**Cause:** Column name mismatch not caught by fuzzy matching

**Solution:**
1. Check if column exists with different name:
   ```sql
   -- List actual columns
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'orders';
   ```
2. Add to COMMON_ALTERNATIVES if pattern repeats:
   ```python
   COMMON_ALTERNATIVES["state"].append("location_state")
   ```

#### 2. Location queries always CANNOT

**Symptom:** "orders from California" marked CANNOT on all databases

**Cause:** No location columns detected in schema

**Solution:**
1. Check schema has location columns:
   ```python
   LOCATION_COLUMNS = [
       "state", "state_code", "region", "province",
       "ship_state", "shipping_state", "bill_state",
       # Add your column name if missing
   ]
   ```
2. Verify sample values exist (validator checks for data presence)

#### 3. PARTIAL uses wrong alternative

**Symptom:** "region" selected but data is different meaning

**Cause:** Column name matches but semantic meaning differs

**Solution:**
1. Add explicit mapping in connection settings
2. Use more specific column names in schema

#### 4. Slow validation with many databases

**Symptom:** Validation takes >2 seconds

**Cause:** Too many databases being validated

**Solution:**
1. Filter databases before validation (e.g., by type)
2. Use connection groups/tags
3. Increase `MAX_PARALLEL_DATABASES` if server has capacity

---

## API Reference

### Validator Class

```python
class MultiDatabaseQueryValidator:
    def __init__(
        self,
        schemas: Dict[int, Dict],  # connection_id -> schema
        columns_by_table: Dict[int, Dict[str, List[str]]]  # connection_id -> table -> columns
    )

    def validate_query(
        self,
        sql: str,
        question: str,
        connection_ids: Optional[List[int]] = None
    ) -> MultiDatabaseValidationResult

    def assess_database(
        self,
        connection_id: int,
        sql: str,
        question: str
    ) -> DatabaseQueryAssessment
```

### Response Types

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
  confidence: number;  // 0.0-1.0
}
```

### REST Endpoints

```
POST /api/multi-db-query/validate
Body: { question: string, connection_ids: number[] }
Response: MultiDatabaseValidationResult

POST /api/multi-db-query/
Body: { question: string, connection_ids: number[], skip_validation?: boolean }
Response: MultiDatabaseQueryResponse (with per-DB results)
```

---

## File Reference

| File | Purpose |
|------|---------|
| `src/llm/multi_db_query_validator.py` | Core validation logic (1061 lines) |
| `src/api/endpoints/multi_db_query.py` | API endpoints for multi-DB queries |
| `src/core/multi_db_handler.py` | Parallel execution handler |
| `frontend/src/components/SchemaGlance.tsx` | Schema overview with location warnings |
| `frontend/src/components/MultiDatabaseAssessment.tsx` | Capability selection UI |
| `frontend/src/components/QueryFeasibilityBadge.tsx` | Status badges |
| `frontend/src/components/MultiDatabaseResults.tsx` | Results with CANNOT differentiation |
| `tests/test_multi_db_query_validator.py` | 27 tests for validation logic |

---

## Related Documentation

- [SQL Generation Pipeline](SQL_GENERATION_PIPELINE.md) - Overall query pipeline
- [Multi-Database Guide](MULTI_DATABASE_GUIDE.md) - General multi-DB usage
- [Parallel Execution](PARALLEL_EXECUTION.md) - Performance optimization details
- [Phase 2 PR Review](SMALL_MODEL_OPTIMIZATION_PHASE_2_PR_REVIEW.md) - Code review findings
