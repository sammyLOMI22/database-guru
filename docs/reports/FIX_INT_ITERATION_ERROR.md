# Fix: 'int' object is not iterable Error

## Problem

When running multi-database queries, the error "'int' object is not iterable" was occurring. This was caused by TWO separate issues:

### Root Cause #1: active_connection_ids Type Mismatch

The `active_connection_ids` column in the `chat_sessions` table is defined as a JSON column that should always contain an array of integers (e.g., `[1]`, `[1, 2]`). However, under certain conditions, it might be stored or retrieved as a single integer (e.g., `1` instead of `[1]`).

When the code attempts to iterate over this value with:
```python
DatabaseConnection.id.in_(session.active_connection_ids)
```

If `active_connection_ids` is an integer, Python throws: `'int' object is not iterable`

### Root Cause #2: Inconsistent Return Format from SelfCorrectingSQLAgent

The `SelfCorrectingSQLAgent` has two methods that return results in different formats:

1. **`execute_with_retry()`** - Returns `"attempts": attempt_num` (an **integer**)
2. **`generate_and_execute_with_retry()`** - Returns `"attempts": attempts` (a **list**)

The multi_db_query.py code was trying to iterate over `attempts` assuming it was always a list:

```python
for attempt in attempts_list:  # Error if attempts_list is an int!
```

## Solution

### Fix #1: Defensive Handling of active_connection_ids

Added defensive code to ensure `active_connection_ids` is always treated as a list, even if the database contains malformed data.

**Files Changed:**

1. **src/api/endpoints/multi_db_query.py** (Line 111-116)
   - Added check to convert integer to list before querying

2. **src/api/endpoints/chat.py** (Multiple locations)
   - Added defensive checks in:
     - `create_chat_session()`
     - `list_chat_sessions()`
     - `get_chat_session()`
     - `update_chat_session()`

**Code Pattern Added:**

```python
# Ensure active_connection_ids is a list (defensive against bad data)
connection_ids = session.active_connection_ids
if isinstance(connection_ids, int):
    connection_ids = [connection_ids]
elif not isinstance(connection_ids, list):
    connection_ids = list(connection_ids) if connection_ids else []
```

This pattern:
1. Checks if the value is an integer and wraps it in a list
2. Checks if it's not already a list and attempts to convert it
3. Defaults to empty list if the value is None or empty

### Fix #2: Handle Inconsistent Agent Return Formats

Added logic to detect whether `attempts` is returned as an integer or a list, and handle both cases.

**Files Changed:**

1. **src/api/endpoints/multi_db_query.py** (Line 272-302)
   - Added type checking for `attempts` field
   - Falls back to `corrections` field when `attempts` is an integer
   - Safely handles both return formats

**Code Pattern Added:**

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

## Data Migration

A helper script `fix_connection_ids.py` has been created to scan the database and fix any malformed data:

```bash
python3 fix_connection_ids.py
```

This script:
- Reads all chat sessions from the database
- Identifies sessions with non-list `active_connection_ids`
- Converts integers to single-element lists
- Commits the fixes to the database

## Prevention

To prevent this issue in the future:

1. **Database Constraints**: The ChatSession model already has `default=list` on the column definition
2. **API Validation**: The ChatSessionCreate and ChatSessionUpdate models require `List[int]` for connection_ids
3. **Defensive Coding**: The added checks ensure the code handles unexpected data gracefully

## Testing

After applying this fix:
1. Multi-database queries should work regardless of how `active_connection_ids` is stored
2. Chat session endpoints will normalize the data to always return lists
3. No breaking changes to the API

## Related Files

- [src/api/endpoints/multi_db_query.py](../../src/api/endpoints/multi_db_query.py)
- [src/api/endpoints/chat.py](../../src/api/endpoints/chat.py)
- [src/database/models.py](../../src/database/models.py#L117-L126) (ChatSession model)
- [fix_connection_ids.py](../../fix_connection_ids.py) (Data migration script)

## Additional Issue: DuckDB Schema Inspection

While fixing the iteration error, we discovered a second issue preventing DuckDB queries:

**Problem:** DuckDB schema inspection was failing with "object CursorResult can't be used in 'await' expression"

**Root Cause:** DuckDB uses synchronous SQLAlchemy sessions (not async), but the schema inspector was treating all sessions as async.

**Solution:** Created a `_execute_query()` helper method in `SchemaInspector` that detects sync vs async sessions and handles them appropriately.

See [MULTI_DB_QUERY_FIXES.md](../technical/MULTI_DB_QUERY_FIXES.md) for complete details.

## Status
✅ **RESOLVED** (October 18, 2025) - All issues fixed and tested. Multi-database queries now work correctly with both SQLite and DuckDB.
