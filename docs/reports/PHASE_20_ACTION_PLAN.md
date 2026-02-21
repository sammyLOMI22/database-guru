# Phase 20 Action Plan: Critical Fixes

Based on the technical audit, please address the following high-priority issues:

## 1. Fix Batched Data Migration Offset Literal (Logic Bug)
The `DataMigrationAssistant` outputs the strict literal string `OFFSET {offset}` in the SQL because it's generating a Python format string template instead of raw executable SQL. This breaks script downloads.

**Fix Suggestion:** 
If the script is meant to be run manually by users, use parameters or generate all the individual batch offsets directly in the SQL (e.g. `OFFSET 0; OFFSET 1000;`). If it's strictly a template for a future script runner engine, it should be clearly documented as such.
For now, you can mitigate the UX issue by setting an explicit `OFFSET 0` or stripping the placeholder.

```python
# src/migration/data_migration_assistant.py  (Lines ~263-278)

# Change this:
f"LIMIT {self.batch_size} OFFSET {{offset}};"

# To a manual-friendly alternative:
f"LIMIT {self.batch_size} OFFSET 0;" 
```

## 2. API Endpoint explicit Rollback
Add explicit `await db.rollback()` in the `except` blocks of the `migration.py` endpoints before raising the `HTTPException` to prevent dangling transactions.

```python
# src/api/endpoints/migration.py 

# Apply to plan, diff, and scripts handlers:
    except Exception as e:
        await db.rollback() # <--- add this
        logger.error(f"Schema diff failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Schema diff failed: {str(e)}")
```
