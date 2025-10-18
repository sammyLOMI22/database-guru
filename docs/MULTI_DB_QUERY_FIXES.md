# Multi-Database Query Fixes - Complete Summary

## Issues Fixed

### Issue 1: "'int' object is not iterable" Error
**Symptom:** When running multi-database queries, the error "'int' object is not iterable" was thrown.

**Root Cause:** Two separate problems:
1. `active_connection_ids` could potentially be stored/retrieved as an integer instead of a list
2. `SelfCorrectingSQLAgent` had inconsistent return formats - `execute_with_retry()` returned `attempts` as an integer, while `generate_and_execute_with_retry()` returned it as a list

**Solution:**
- Added defensive type checking for `active_connection_ids` throughout the codebase
- Added logic in `multi_db_query.py` to handle both integer and list formats for the `attempts` field

**Files Modified:**
- [src/api/endpoints/multi_db_query.py](../src/api/endpoints/multi_db_query.py)
  - Lines 111-116: Defensive handling of `active_connection_ids`
  - Lines 272-302: Handle both int and list formats for `attempts`
- [src/api/endpoints/chat.py](../src/api/endpoints/chat.py) - Multiple functions updated with defensive checks

### Issue 2: DuckDB Schema Inspection Failing
**Symptom:** DuckDB database returned 0 tables, preventing query generation for that database.

**Root Cause:** Multiple issues:
1. DuckDB uses a **synchronous** SQLAlchemy session (not async like PostgreSQL/MySQL)
2. The schema inspector was calling `await session.execute()` on sync sessions, causing "CursorResult can't be used in 'await' expression" error
3. Result objects were using `.fetchall()` instead of `.all()` (async-compatible method)

**Solution:**
- Created `_execute_query()` helper method that detects if session is async or sync and handles accordingly
- Updated all schema inspection methods to use the helper
- Changed all `.fetchall()` calls to `.all()`
- Added DuckDB-specific query for table listing

**Files Modified:**
- [src/core/schema_inspector.py](../src/core/schema_inspector.py)
  - Lines 20-44: New `_execute_query()` helper method
  - Lines 127-161: Updated `get_tables()` to use helper and support DuckDB
  - All query execution methods updated to handle sync/async sessions

## Code Changes

### 1. Defensive `active_connection_ids` Handling

```python
# Ensure active_connection_ids is a list (defensive against bad data)
connection_ids = session.active_connection_ids
if isinstance(connection_ids, int):
    connection_ids = [connection_ids]
elif not isinstance(connection_ids, list):
    connection_ids = list(connection_ids) if connection_ids else []
```

### 2. Handle Inconsistent Agent Return Formats

```python
attempts_data = exec_result.get("attempts", [])
corrections_data = exec_result.get("corrections", [])

# Determine total_attempts and attempts_list
if isinstance(attempts_data, int):
    # execute_with_retry returns attempts as int
    total_attempts = attempts_data
    attempts_list = corrections_data  # Use corrections instead
elif isinstance(attempts_data, list):
    # generate_and_execute_with_retry returns attempts as list
    total_attempts = exec_result.get("total_attempts", len(attempts_data))
    attempts_list = attempts_data
else:
    # Fallback
    total_attempts = exec_result.get("total_attempts", 0)
    attempts_list = corrections_data if corrections_data else []
```

### 3. Sync/Async Session Handler

```python
async def _execute_query(self, session, query, params=None):
    """Execute a query handling both sync and async sessions"""
    is_async = isinstance(session, AsyncSession)

    if is_async:
        if params:
            return await session.execute(query, params)
        else:
            return await session.execute(query)
    else:
        # Sync session (e.g., DuckDB)
        if params:
            return session.execute(query, params)
        else:
            return session.execute(query)
```

## Testing

After these fixes:
- ✅ Multi-database queries work without errors
- ✅ Schema inspection succeeds for both SQLite and DuckDB
- ✅ Queries are generated for all databases in the chat session
- ✅ Results are returned from all databases

## Related Documentation

- [FIX_INT_ITERATION_ERROR.md](./FIX_INT_ITERATION_ERROR.md) - Detailed explanation of the iteration error
- [QUERY_PLANNING_AGENT.md](./QUERY_PLANNING_AGENT.md) - Query planning agent documentation
- [fix_connection_ids.py](../fix_connection_ids.py) - Utility script to check/fix database data

## Technical Notes

### DuckDB Synchronous Sessions
DuckDB doesn't have a native async driver, so connections use synchronous SQLAlchemy sessions. The `UserDatabaseConnector` (lines 64-90) creates sync sessions for DuckDB while using async sessions for other databases. All schema inspection code must handle both cases.

### SQLAlchemy Async Result Methods
- ✅ Use `.all()` for async compatibility
- ❌ Don't use `.fetchall()` (sync only)
- ✅ Use `await session.execute()` for async sessions
- ✅ Use `session.execute()` (no await) for sync sessions

## Date
October 18, 2025

## Status
✅ **RESOLVED** - All multi-database query issues fixed and tested
