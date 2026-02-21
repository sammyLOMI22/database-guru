# PR Review: Phase 20 — Migration Toolkit

**Branch:** `phase-20-migration-toolkit` (1 commit, +5,676 lines, 26 files)

## Overall Assessment

Well-structured feature with clear separation: schema comparator (deterministic) -> planner (deterministic + LLM enrichment) -> script generator (template-based) ->
data migration assistant. Follows established project patterns (ImpactAdvisor, model_router integration). Good test coverage provided. A few issues worth addressing
before merge.

---

## Bugs / Correctness Issues

### 1. Data migration generates self-referencing INSERT (Critical) -- RESOLVED

`data_migration_assistant.py:253` — The `INSERT INTO ... SELECT ... FROM` used the **same table** for both source and target:

```python
insert_sql = f"INSERT INTO {qt} ({target_cols})\nSELECT {select_exprs}\nFROM {qt};"
```

This would double the data in the table or fail. The `count_verify_sql` had the same issue — it counted the same table for both source and target.

**Resolution:** Introduced a staging table pattern. The target is now `{table}__new`, so the SQL becomes:
```python
INSERT INTO "users__new" (cols) SELECT exprs FROM "users";
```
The verify SQL now correctly compares counts between the source table and the staging table. The `TableDataMigration.source_table` and `target_table` fields now reflect the distinct names. Tests updated to assert the staging table pattern.

---

### 2. SQLite recreate misses unchanged columns (`script_generator.py:245-264`) -- RESOLVED

The `_sqlite_recreate` method only iterated `td.column_diffs`, which only contains **changed** columns. Columns that didn't change were silently dropped from the recreated table. This would cause data loss on any table modification in SQLite.

**Resolution:** Threaded `source_schema`/`target_schema` through the `ScriptGenerator.generate()` -> `_generate_up()` -> `_alter_table_ddl()` -> `_sqlite_recreate()` call chain. When the target schema is available, `_sqlite_recreate` uses it as the authoritative column list (which includes both changed and unchanged columns). When only the source schema is available, unchanged columns are merged from the source schema. When neither is available, a warning is emitted. The API endpoint (`POST /migration/projects/{id}/scripts`) now fetches source and target schemas and passes them to the generator. Three new tests cover: schemas present, source-only fallback, and no-schemas-with-warning.

---

### 3. `_topological_sort_tables` only considers constraint diffs, not existing FKs (`migration_planner.py:162-171`)

The topo sort only looks at FK relationships found in `constraint_diffs`. If a table has existing FK relationships that weren't changed, they won't appear in the diff,
so the execution order could violate FK constraints during migration.

**Status:** Open — lower priority. To fix properly, the planner would need access to the full source/target schemas to build the complete FK dependency graph.

---

### 4. Alembic migration `down_revision` mismatch (`b7e3a1d2f456`) -- RESOLVED

Line 18: `down_revision = 'a3b9d1e4f567'` — but the last known migration in the repo is `f451a46c49e1` (LLM usage tables). The header comment said `Revises: f451a46c49e1`
but the actual `down_revision` field pointed to a different revision. This broke the migration chain.

**Resolution:** Changed `down_revision` from `'a3b9d1e4f567'` to `'f451a46c49e1'` to match the actual migration chain.

---

## Design Concerns

### 5. Duplicated SchemaDiff reconstruction logic (3x)

`plan_migration()`, `generate_scripts()`, and `generate_data_migration_plan()` all contain identical ~20-line blocks to reconstruct `SchemaDiff` from a dict. This should be
a class method like `SchemaDiff.from_dict()`.

### 6. `MigrationProject.updated_at` never updates

The model at `models.py:524` has `updated_at` with `server_default` but no `onupdate`. When the project status transitions through `draft -> planned -> scripted`, the
`updated_at` column stays at creation time. Add `onupdate=sa.func.current_timestamp()` or set it manually.

### 7. `list_projects` N+1 query (`migration.py:157-166`)

For each project, two additional `db.get()` calls fetch connection names. With many projects this becomes expensive. Use a joined query or eager loading instead.

### 8. Batched insert is MySQL/SQLite/PostgreSQL identical except for PostgreSQL's `ORDER BY ctid` (`data_migration_assistant.py:256-277`)

The MySQL and else branches were identical — collapsed the conditional so only PostgreSQL's `ORDER BY ctid` is the special case.

---

## Security

### 9. SQL injection in verify.sql (`script_generator.py:389`)

Table names are interpolated directly into `information_schema` queries using f-strings with unquoted values:

```python
f"WHERE table_name = '{td.table_name}'"
```

While `table_name` comes from schema introspection (not user input), it's still worth using parameterized patterns or at least escaping single quotes for defense in depth.

### 10. `download_script` filename validation is allowlist-based (good)

The `/scripts/{filename}` endpoint checks against a fixed `script_map` dict, which is the right approach.

---

## Minor / Style

### 11. `generate_scripts` function name shadows the import in `migration.py:301`

```python
from src.migration.script_generator import generate_scripts as gen_scripts
```

This works but the endpoint function `generate_scripts` at line 290 has the same name as the module function, requiring the alias. Consider renaming the endpoint function.

### 12. `drift_detector.py` is defined but never wired into any endpoint or scheduled task

Is this intentional for a future phase?

### 13. `MigrationStepSchema` appears twice in `schemas.py`

Once at line 758 (existing, from ImpactAdvisor) and again at line 1319 (new, for Phase 20). They have overlapping but different fields. The one at 758 (`MigrationStepSchema`) is used by `MigrationPlanSchema`; the one at 1319 is used by `MigrationPlanResponse`. This is confusing — consider renaming one.

### 14. The commit message says "Intial Commit" (typo for "Initial")

---

## Summary

| Category | Count | Resolved |
|----------|-------|----------|
| Bugs / Correctness | 4 | 3 of 4 |
| Design Concerns | 4 | 0 (follow-up) |
| Security | 1 (low risk) | 0 (follow-up) |
| Minor / Style | 4 | 0 (follow-up) |

All three critical items (#1, #2, #4) have been resolved. Item #3 (topo sort FK coverage) remains open as a lower-priority improvement. Design and style items are tracked for follow-up.
