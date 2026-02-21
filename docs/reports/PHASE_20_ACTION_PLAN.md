# Phase 20 Action Plan: Critical Fixes

Based on the technical audit, the following high-priority issues have been addressed.

## 1. Fix Batched Data Migration Offset Literal (Logic Bug) — RESOLVED

**Issue:** The `DataMigrationAssistant` output the literal string `OFFSET {offset}` in generated SQL, producing non-executable scripts for users.

**Fix Applied:** Replaced the `{offset}` placeholder with `OFFSET 0` in both the PostgreSQL and generic branches of `data_migration_assistant.py` (lines ~263-278). Downloaded scripts now contain valid, executable SQL.

```python
# src/migration/data_migration_assistant.py (Lines ~263-278)
# Before: f"LIMIT {self.batch_size} OFFSET {{offset}};"
# After:  f"LIMIT {self.batch_size} OFFSET 0;"
```

## 2. API Endpoint Explicit Rollback — RESOLVED

**Issue:** The `except Exception` blocks in `migration.py` raised `HTTPException` without rolling back the database session, risking dangling transactions.

**Fix Applied:** Added `await db.rollback()` before `raise HTTPException` in all four endpoint exception handlers:
- `POST /diff` (schema diff)
- `POST /plan` (migration plan)
- `POST /scripts` (script generation)
- `POST /data-migration` (data migration)

```python
# src/api/endpoints/migration.py
    except Exception as e:
        await db.rollback()
        logger.error(...)
        raise HTTPException(...)
```
Changes made                                                                                                                                                         
                                                                                                                                                                       
  src/migration/data_migration_assistant.py                                                                                                                            
  - Issue 1: Added a -- Batch template: run with OFFSET 0, N, 2N, ... until 0 rows inserted. comment to every batched_insert_sql, making the iteration pattern       
  self-documenting.                                                                                                                                                    

  src/migration/script_generator.py
  - Issue 2 (_sqlite_rollback + _generate_down): Added a new _sqlite_rollback() helper that generates a CREATE __rollback → INSERT SELECT (with CAST for type
  reversals, NULL for dropped cols) → DROP → RENAME pattern. _generate_down() now routes all SQLite modified-table rollbacks through this helper instead of emitting
  nothing.
  - Issue 3 (_sort_removed_tables_for_drop): New helper using Kahn's algorithm on source-schema FK relationships. Child tables (those with FKs pointing to other
  removed tables) are dropped first, preventing FK constraint failures.
  - Issue 4 (_generate_verify): For each added column in a modified table, verify.sql now emits an information_schema.columns check (PostgreSQL/MySQL) or a
  pragma_table_info(...) check (SQLite) to confirm the column was actually created.

  Tests — 9 new tests added (107 total, all passing):
  - TestSQLiteDownRollback — 3 tests covering type-change rollback, added-column exclusion, dropped-column NULL fill
  - TestDropTableOrder — 2 tests covering FK-aware drop order and fallback
  - TestVerifyColumnExists — 3 tests covering PG/SQLite column checks and that type-changed columns aren't double-checked
  - test_batched_sql_includes_loop_comment — confirms batch template comment is present
