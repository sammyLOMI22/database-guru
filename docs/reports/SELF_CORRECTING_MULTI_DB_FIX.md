# Self-Correcting Agent - Multi-Database Fix

## Problem

The self-correcting SQL agent wasn't working for queries that went through the multi-database endpoint (`/api/multi-query/`). When users asked questions like "do we have headphones", the generated SQL used incorrect column names (e.g., `product_name` instead of `name`), and the error wasn't automatically corrected.

### Root Cause

The self-correcting agent was only integrated into the single-database query endpoint (`/api/query/` in [query.py](src/api/endpoints/query.py#L106-L121)). The multi-database endpoint ([multi_db_query.py](src/api/endpoints/multi_db_query.py)) was calling `MultiDatabaseHandler.execute_query_on_database()` directly, which bypassed the self-correction logic.

### Evidence

From the backend logs:
```
database_type: 'multi_db_1'  # Indicates multi-database endpoint
Error: (sqlite3.OperationalError) no such column: product_name
SQL: SELECT * FROM products WHERE product_name LIKE '%headphones%' LIMIT 10
```

The correct column name is `name`, not `product_name`, but the agent didn't retry with a corrected query.

---

## Solution

Integrated the self-correcting agent into the multi-database query flow:

### 1. Added New Method to MultiDatabaseHandler

**File**: [src/core/multi_db_handler.py](src/core/multi_db_handler.py)

Added `execute_query_with_self_correction()` method (lines 195-323):

```python
async def execute_query_with_self_correction(
    self,
    connection: DatabaseConnection,
    question: str,
    schema: str,
    sql_generator: SQLGenerator,
    initial_sql: Optional[str] = None,
    allow_write: bool = False,
    max_rows: int = 1000,
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Execute a SQL query on a specific database WITH self-correction"""
```

This method:
- Creates a `SelfCorrectingSQLAgent` instance
- Uses the agent's `execute_with_retry()` method for pre-generated SQL
- Returns results with correction attempt metadata

### 2. Added execute_with_retry() to SelfCorrectingSQLAgent

**File**: [src/llm/self_correcting_agent.py](src/llm/self_correcting_agent.py)

Added new method (lines 348-483) to handle retries for pre-generated SQL:

```python
async def execute_with_retry(
    self,
    sql: str,
    schema: str,
    session,
    database_type: str,
    question: str,
    allow_write: bool = False,
) -> Dict[str, Any]:
    """Execute pre-generated SQL with automatic error correction and retry"""
```

This complements the existing `generate_and_execute_with_retry()` method:
- `generate_and_execute_with_retry()`: Generates SQL from scratch, then retries on error
- `execute_with_retry()`: Takes pre-generated SQL, then retries on error (useful for multi-DB)

### 3. Updated Multi-Database Query Endpoint

**File**: [src/api/endpoints/multi_db_query.py](src/api/endpoints/multi_db_query.py)

**Changed** (lines 257-264):
```python
# OLD: Direct execution without self-correction
exec_result = await multi_db_handler.execute_query_on_database(
    connection=connection,
    sql=sql,
    allow_write=request.allow_write,
)

# NEW: Execute with self-correction
exec_result = await multi_db_handler.execute_query_with_self_correction(
    connection=connection,
    question=request.question,
    schema=db_schema or combined_schema_text,
    sql_generator=sql_generator,
    initial_sql=sql,
    allow_write=request.allow_write,
)
```

**Added correction metadata to response** (lines 45-46):
```python
correction_attempts: Optional[int] = 0
corrections: Optional[List[Dict[str, Any]]] = None
```

---

## How It Works Now

### Scenario: User asks "do we have headphones"

1. **Query Generation**:
   - LLM generates: `SELECT * FROM products WHERE product_name LIKE '%headphones%' LIMIT 10`
   - (Incorrect: column should be `name`, not `product_name`)

2. **First Execution Attempt**:
   - Query fails: `no such column: product_name`
   - Error categorized as `COLUMN_NOT_FOUND`

3. **Self-Correction** (Attempt 2):
   - Agent extracts error context: `product_name` doesn't exist
   - Generates fix hints: "Check schema for correct column name"
   - LLM generates corrected SQL: `SELECT * FROM products WHERE name LIKE '%headphones%' LIMIT 10`

4. **Second Execution**:
   - Query succeeds!
   - Returns results with metadata:
     ```json
     {
       "success": true,
       "sql": "SELECT * FROM products WHERE name LIKE '%headphones%' LIMIT 10",
       "results": [...],
       "correction_attempts": 2,
       "corrections": [
         {
           "attempt_number": 1,
           "sql": "SELECT * FROM products WHERE product_name LIKE '%headphones%' LIMIT 10",
           "error": "no such column: product_name",
           "error_type": "column_not_found",
           "success": false
         },
         {
           "attempt_number": 2,
           "sql": "SELECT * FROM products WHERE name LIKE '%headphones%' LIMIT 10",
           "success": true,
           "row_count": 3
         }
       ]
     }
     ```

---

## Benefits

1. **Automatic Error Recovery**: Column name errors, table name typos, and syntax issues are automatically corrected
2. **Consistent Behavior**: Both single-database and multi-database endpoints now have self-correction
3. **Transparency**: Users can see how many correction attempts were made
4. **Better UX**: Queries that would have failed now succeed automatically

---

## Error Types Handled

The self-correcting agent can handle 6 types of errors:

1. **COLUMN_NOT_FOUND** - Wrong column names (like this case)
2. **TABLE_NOT_FOUND** - Wrong table names
3. **SYNTAX_ERROR** - SQL syntax mistakes
4. **TYPE_MISMATCH** - Data type issues
5. **PERMISSION_DENIED** - Access issues
6. **TIMEOUT** - Query timeouts

---

## Testing

To test the fix:

```bash
# Start the server
python -m src.main

# Test query that previously failed
curl -X POST http://localhost:8000/api/multi-query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "do we have headphones",
    "connection_ids": [7]
  }'
```

Expected result:
- Query should succeed
- `correction_attempts` should be > 0 if a correction was made
- `corrections` array should show the error and fix

---

## Files Changed

1. **src/llm/self_correcting_agent.py** - Added `execute_with_retry()` method
2. **src/core/multi_db_handler.py** - Added `execute_query_with_self_correction()` method
3. **src/api/endpoints/multi_db_query.py** - Updated to use self-correction

---

## Backward Compatibility

All changes are backward compatible:
- ✅ Single-database queries still work with self-correction
- ✅ Direct execution method (`execute_query_on_database`) still exists for cases where self-correction isn't needed
- ✅ Response format is extended, not changed (new optional fields)
- ✅ No breaking changes to existing APIs

---

## Next Steps

The self-correcting agent is now fully integrated across all query endpoints. Future enhancements from [NEXT_FEATURES_ROADMAP.md](NEXT_FEATURES_ROADMAP.md) Phase 0:

1. **Learning from Corrections** - Remember successful fixes
2. **Confidence Scoring** - Predict if correction will work
3. **Schema-Aware Fixes** - Use schema metadata for smarter fixes
4. **User Feedback Integration** - Learn from user corrections
5. **Parallel Corrections** - Try multiple fixes simultaneously

---

## Summary

The self-correcting agent now works for **both** single-database and multi-database queries, automatically fixing common SQL errors like incorrect column names, table names, and syntax mistakes. This significantly improves the user experience by reducing failed queries.
