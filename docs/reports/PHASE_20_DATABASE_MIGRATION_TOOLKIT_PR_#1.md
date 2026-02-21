# PR Review: Phase 20 — Migration Toolkit

**Branch:** `phase-20-migration-toolkit` (1 commit, +5,676 lines, 26 files)

## Overall Assessment

Well-structured feature with clear separation: schema comparator (deterministic) -> planner (deterministic + LLM enrichment) -> script generator (template-based) ->
data migration assistant. Follows established project patterns (ImpactAdvisor, model_router integration). Good test coverage provided. All issues identified in the initial review have been resolved.

---

## Bugs / Correctness Issues

### 1. Data migration generates self-referencing INSERT (Critical) -- RESOLVED

`data_migration_assistant.py:253` — The `INSERT INTO ... SELECT ... FROM` used the **same table** for both source and target.

**Resolution:** Introduced a staging table pattern. The target is now `{table}__new`, so the SQL becomes:
```sql
INSERT INTO "users__new" (cols) SELECT exprs FROM "users";
```
The verify SQL now correctly compares counts between the source table and the staging table. Also collapsed the identical MySQL/SQLite batched SQL branches (#8).

---

### 2. SQLite recreate misses unchanged columns (`script_generator.py`) -- RESOLVED

The `_sqlite_recreate` method only iterated `td.column_diffs`, which only contains **changed** columns. Columns that didn't change were silently dropped from the recreated table.

**Resolution:** Threaded `source_schema`/`target_schema` through `ScriptGenerator.generate()` -> `_generate_up()` -> `_alter_table_ddl()` -> `_sqlite_recreate()`. When the target schema is available, all columns (changed + unchanged) are included. Fallback paths emit warnings. The API endpoint now fetches schemas and passes them to the generator.

---

### 3. `_topological_sort_tables` only considers constraint diffs, not existing FKs -- RESOLVED

The topo sort only looked at FK relationships found in `constraint_diffs`. Unchanged FKs weren't considered.

**Resolution:** `_topological_sort_tables` now accepts optional `source_schema`/`target_schema` parameters. After processing constraint diffs, it also reads `foreign_keys` from the full schema to include unchanged FK relationships in the dependency graph. The API endpoint fetches and passes schemas to `plan_migration()`.

---

### 4. Alembic migration `down_revision` mismatch (`b7e3a1d2f456`) -- RESOLVED

`down_revision = 'a3b9d1e4f567'` didn't match the actual last migration `f451a46c49e1`.

**Resolution:** Changed `down_revision` to `'f451a46c49e1'`.

---

## Design Concerns

### 5. Duplicated SchemaDiff reconstruction logic (3x) -- RESOLVED

`plan_migration()`, `generate_scripts()`, and `generate_data_migration_plan()` all contained identical ~20-line reconstruction blocks.

**Resolution:** Added `SchemaDiff.from_dict()` class method to `schema_comparator.py`. All three call sites now use a single-line `SchemaDiff.from_dict(diff_data)`.

---

### 6. `MigrationProject.updated_at` never updates -- RESOLVED (already correct)

The model already had `onupdate=lambda: datetime.now(timezone.utc)` defined. SQLAlchemy handles this at the ORM level, which is correct for all supported backends including SQLite.

---

### 7. `list_projects` N+1 query -- RESOLVED

For each project, two additional `db.get()` calls fetched connection names.

**Resolution:** Replaced with `selectinload(MigrationProject.source_connection)` and `selectinload(MigrationProject.target_connection)` in the query, reducing to 3 queries total regardless of project count. Applied the same optimization to `get_project`.

---

### 8. Batched insert duplicate branches -- RESOLVED

The MySQL and else branches were identical.

**Resolution:** Collapsed into a single else branch with PostgreSQL `ORDER BY ctid` as the only special case (done as part of Fix #1).

---

## Security

### 9. SQL injection in verify.sql -- RESOLVED

Table names were interpolated directly into `information_schema` / `sqlite_master` WHERE clauses using unescaped f-strings.

**Resolution:** Added `_escape_literal()` helper that escapes single quotes (`'` -> `''`). All string-literal interpolations in `_generate_verify()` now use the escaped value. Also collapsed the duplicate PostgreSQL/MySQL branches.

---

### 10. `download_script` filename validation is allowlist-based (good)

No changes needed — the existing allowlist approach is correct.

---

## Minor / Style

### 11. `generate_scripts` function name shadows the import -- RESOLVED

**Resolution:** Renamed the endpoint function from `generate_scripts` to `create_scripts`. The import alias `gen_scripts` is no longer needed.

---

### 12. `drift_detector.py` is defined but never wired

Intentional — this is scaffolding for a future drift detection feature. No action needed.

---

### 13. `MigrationStepSchema` appears twice in `schemas.py` -- RESOLVED

The Phase 20 version (line 1319) shadowed the ImpactAdvisor version (line 748) with different fields.

**Resolution:** Renamed the Phase 20 version to `MigrationToolkitStepSchema` with a docstring clarifying the distinction.

---

### 14. Commit message typo ("Intial" -> "Initial")

Cannot retroactively fix without history rewrite. Noted for future commits.

---

## Summary

| Category | Count | Resolved |
|----------|-------|----------|
| Bugs / Correctness | 4 | 4 of 4 |
| Design Concerns | 4 | 4 of 4 |
| Security | 1 (low risk) | 1 of 1 |
| Minor / Style | 4 | 3 of 4 (typo not fixable) |

All actionable issues have been resolved. 98 migration-related tests pass.