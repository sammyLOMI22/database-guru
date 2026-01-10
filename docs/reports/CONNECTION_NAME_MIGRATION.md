# Connection Name Migration Summary

**Date**: November 9, 2025
**Issue**: Column/table mappings need to be scoped to specific database instances, not just database types
**Solution**: Add `connection_name` field to mapping tables

---

## Problem

The original design used only `database_type` (e.g., "postgres", "mysql") to scope mappings. This doesn't work when:
- User has multiple PostgreSQL databases with different schemas
- "price" → "unit_price" mapping in "sales_db" shouldn't apply to "inventory_db"
- Each database instance needs independent mapping configuration

## Solution

Add `connection_name` field that references `DatabaseConnection.name`:
- Unique per database instance (e.g., "sales_db", "inventory_db", "prod_postgres")
- Allows per-database mapping configuration
- Maintains database_type for backward compatibility and filtering

---

## Changes Made

### 1. Database Schema ✅
**File**: `scripts/add_connection_name_to_mappings.py`

Added `connection_name VARCHAR(255) NULL` to:
- `column_mappings` table
- `table_mappings` table

Updated unique indexes to include `connection_name`:
```sql
-- column_mappings
UNIQUE INDEX (source_column, target_column, table_name, connection_name, database_type)

-- table_mappings
UNIQUE INDEX (source_table, target_table, connection_name, database_type)
```

### 2. Code Changes Required

#### ColumnMapper (IN PROGRESS)
**File**: `src/llm/column_mapper.py`

**Method signatures updated**:
```python
async def learn_from_feedback(
    ...,
    connection_name: str,  # NEW - required parameter
    database_type: str,
    ...
)

async def apply_mappings(
    ...,
    connection_name: str,  # NEW - required parameter
    database_type: str
)

async def suggest_correct_column(
    ...,
    connection_name: str,  # NEW - required parameter
    database_type: str
)
```

**SQL queries updated** to include `connection_name` in WHERE clauses and INSERT statements.

#### Tests (TODO)
**File**: `tests/test_column_mapper.py`

All 23 tests need to be updated to pass `connection_name="test_db"`.

#### TableMapper (TODO)
Same changes needed when implementing TableMapper.

#### Feedback Endpoint (TODO)
**File**: `src/api/endpoints/feedback.py`

When calling ColumnMapper/TableMapper, need to get connection_name from query context:
```python
# Get the database connection for this query
conn = await db_session.get(DatabaseConnection, query.database_connection_id)
connection_name = conn.name if conn else "unknown"

# Learn from feedback with connection_name
await column_mapper.learn_from_feedback(
    ...,
    connection_name=connection_name,
    database_type=query.database_type
)
```

---

## Migration Status

### ✅ Completed
1. Migration script created and executed
2. `connection_name` field added to both tables
3. Unique indexes updated
4. Connection name indexes added
5. ColumnMapper class methods updated (all signatures and SQL queries)
6. All 23 ColumnMapper tests updated and passing
7. Test fixture updated to include connection_name column

### ⏳ TODO
1. Update design document (../technical/NON_SQL_FEEDBACK_DESIGN.md)
2. Implement TableMapper with connection_name from start
3. Update feedback endpoint integration (src/api/endpoints/feedback.py)
4. Update SchemaValidator integration (if needed)
5. Add integration tests for connection-scoped mappings

---

## Usage Examples

### Before (Wrong):
```python
# This would apply to ALL postgres databases!
await mapper.learn_from_feedback(
    source_column="price",
    target_column="unit_price",
    table_name="products",
    database_type="postgres",  # Too broad!
    feedback_id=123
)
```

### After (Correct):
```python
# This applies ONLY to sales_db
await mapper.learn_from_feedback(
    source_column="price",
    target_column="unit_price",
    table_name="products",
    connection_name="sales_db",  # Specific database instance
    database_type="postgres",
    feedback_id=123
)
```

---

## Breaking Changes

⚠️ **API Breaking Change**: All calls to ColumnMapper methods must now include `connection_name` parameter.

**Migration Path**:
1. Update all existing code to pass `connection_name`
2. Get `connection_name` from `DatabaseConnection.name` via query context
3. For global mappings, use a default like "global" or specific connection name

---

## Testing Strategy

1. **Unit Tests**: Update all 23 tests to include `connection_name="test_db"`
2. **Integration Tests**: Test with multiple connections:
   - sales_db (PostgreSQL)
   - inventory_db (PostgreSQL)
   - Verify mappings don't cross-pollinate
3. **Migration Test**: Verify existing data (if any) handles NULL connection_name

---

## Rollback Plan

SQLite doesn't support DROP COLUMN, so rollback requires:
1. Export all data
2. Drop tables
3. Recreate with old schema
4. Re-import data

**Recommendation**: Don't rollback - fix forward by completing the migration.

---

## Final Status

**Database Migration**: ✅ Completed successfully
**ColumnMapper Updates**: ✅ Completed successfully (all 23 tests passing)
**Next Steps**:
1. Implement TableMapper class with connection_name from the start
2. Implement ResultPatternLearner class
3. Update feedback.py endpoint to extract connection_name from query context
4. Add integration tests with multiple database connections

**Last Updated**: November 9, 2025
