# Phase 20: Database Migration Toolkit — Testing Guide

This guide covers how to verify the Phase 20 branch (`phase-20-migration-toolkit`) both via automated tests and manual end-to-end walkthroughs.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Running Automated Tests](#running-automated-tests)
3. [Test Coverage Summary](#test-coverage-summary)
4. [Manual Testing: Backend API](#manual-testing-backend-api)
5. [Manual Testing: Frontend UI](#manual-testing-frontend-ui)
6. [Database Migration (Alembic)](#database-migration-alembic)
7. [Known Limitations & Edge Cases](#known-limitations--edge-cases)

---

## Prerequisites

```bash
# 1. Activate virtualenv
source venv/bin/activate

# 2. Ensure Ollama is running (needed for LLM-enriched plan generation)
ollama serve &
ollama pull llama3.2:latest

# 3. Apply database migration
alembic upgrade head

# 4. Frontend dependencies
cd frontend && npm install && cd ..
```

You need **at least two database connections** registered in Database Guru to test schema diffing. These can be:
- Two SQLite databases with different schemas
- A PostgreSQL + MySQL pair
- Any combination of supported database types

---

## Running Automated Tests

### Run all Phase 20 tests

```bash
# All migration-related test files
./run_tests.sh tests/test_schema_comparator.py tests/test_migration_planner.py tests/test_script_generator.py tests/test_data_migration_assistant.py tests/test_migration_api.py
```

### Run individual test modules

```bash
# Schema Comparator (Phase 20.1) — pure logic, no mocks needed
./run_tests.sh tests/test_schema_comparator.py

# Migration Planner (Phase 20.2) — async tests, some mock LLM
./run_tests.sh tests/test_migration_planner.py

# Script Generator (Phase 20.3) — multi-dialect DDL generation
./run_tests.sh tests/test_script_generator.py

# Data Migration Assistant (Phase 20.4) — INSERT SELECT generation
./run_tests.sh tests/test_data_migration_assistant.py

# API Endpoints — mocked DB session, endpoint logic
./run_tests.sh tests/test_migration_api.py
```

### Run with verbose output (useful for debugging)

```bash
python -m pytest tests/test_schema_comparator.py -v
```

### Run a specific test class or method

```bash
# Single class
python -m pytest tests/test_schema_comparator.py::TestSchemaComparator -v

# Single test
python -m pytest tests/test_script_generator.py::TestScriptGeneratorSQLite::test_sqlite_recreate_includes_unchanged_columns -v
```

---

## Test Coverage Summary

| Test File | Module Under Test | Test Count | What It Covers |
|-----------|-------------------|------------|----------------|
| `test_schema_comparator.py` | `schema_comparator.py` | ~25 | Type normalization, risk classification, table/column/constraint diffs, synonym handling, serialization |
| `test_migration_planner.py` | `migration_planner.py` | ~15 | Topological sort, deterministic step generation, backup triggers, complexity assessment, LLM fallback, serialization |
| `test_script_generator.py` | `script_generator.py` | ~15 | PostgreSQL/MySQL/SQLite DDL generation, up/down/verify scripts, SQLite table recreate (with and without schemas), quoting |
| `test_data_migration_assistant.py` | `data_migration_assistant.py` | ~15 | Column mapping (schema-aware and diff-only), CAST generation, staging table pattern, batched INSERT, MySQL quoting, serialization |
| `test_migration_api.py` | `migration.py` (endpoints) | ~10 | 404/400 error handling, script download, plan/script/data-migration precondition checks |

### Key scenarios tested

**Schema Comparator:**
- Identical schemas produce no diff
- Table added/removed/modified detection
- Column added (nullable vs NOT NULL without default)
- Column removed (breaking, critical risk)
- Type widening (INTEGER → BIGINT = safe) vs narrowing (BIGINT → SMALLINT = breaking)
- Nullability change (nullable → NOT NULL = breaking)
- Default value changes
- PK/FK/index constraint changes
- Type synonym normalization (`CHARACTER VARYING` = `varchar`, `int4` = `integer`, etc.)

**Migration Planner:**
- Empty diff produces pre_check + verify steps only
- Added table → "Create table" DDL step
- Removed table → critical risk, not reversible, DATA LOSS warning
- Backup step auto-generated for critical/high risk diffs
- No backup for low-risk diffs
- Topological sort respects FK dependencies (parent before child)
- LLM failure gracefully falls back to deterministic plan
- No Ollama client → `llm_used=False`

**Script Generator:**
- PostgreSQL: `CREATE TABLE`, `DROP TABLE`, `ADD COLUMN`, `DROP COLUMN`, `ALTER COLUMN TYPE ... USING`, `SET NOT NULL`
- MySQL: `SET FOREIGN_KEY_CHECKS`, backtick quoting, `MODIFY COLUMN`
- SQLite: table recreate pattern (`CREATE __new`, `INSERT INTO SELECT`, `DROP`, `RENAME`)
- SQLite includes unchanged columns when source/target schemas are provided
- SQLite warns about missing columns when schemas are unavailable
- `verify.sql` uses `information_schema` (PG/MySQL) or `sqlite_master` (SQLite)

**Data Migration Assistant:**
- Only `modified` tables get data migration (not `added`/`removed`)
- Same-type columns → direct pass-through mapping
- Type-changed columns → `CAST(col AS new_type)`
- New columns with default → use default value
- New NOT NULL columns without default → warning emitted
- Removed columns → skipped in migration
- INSERT targets staging table (`table__new`), SELECT from original
- Batched INSERT with `LIMIT/OFFSET` (PostgreSQL uses `ctid` ordering)
- Count verification compares source vs staging table

**API Endpoints:**
- `_get_project` / `_get_connection` raise 404 for missing records
- `download_script` raises 400 for invalid filenames, 404 if not generated
- `generate_plan` raises 400 if no diff snapshot exists
- `create_scripts` raises 400 if no diff snapshot exists
- `generate_data_migration` raises 400 if no diff snapshot exists
- `get_plan` / `get_scripts` / `get_data_migration` raise 404 when not yet generated

---

## Manual Testing: Backend API

Start the backend server:

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

All migration endpoints are under the **migration** tag.

### Step 1: Schema Diff (POST `/api/migration/diff`)

```bash
curl -X POST http://localhost:8000/api/migration/diff \
  -H "Content-Type: application/json" \
  -d '{
    "source_connection_id": 1,
    "target_connection_id": 2,
    "save": true,
    "name": "My Test Migration"
  }'
```

**What to verify:**
- Response includes `table_diffs` array with `added`/`removed`/`modified` entries
- Each table diff has `column_diffs` and `constraint_diffs`
- `overall_risk` is one of: `none`, `low`, `medium`, `high`, `critical`
- `diff_summary` is a human-readable string (e.g., "2 tables modified, 1 table added")
- `total_breaking_changes` and `total_safe_changes` are correct counts
- When `save: true`, `project_id` is returned (non-null integer)
- Type synonyms don't create false diffs (e.g., `CHARACTER VARYING` vs `varchar`)

### Step 2: List Projects (GET `/api/migration/projects`)

```bash
curl http://localhost:8000/api/migration/projects
```

**What to verify:**
- Returns array of project summaries
- Each project has `id`, `name`, `status`, `overall_risk`, connection names
- Ordered by `created_at` descending

### Step 3: Get Project Detail (GET `/api/migration/projects/{id}`)

```bash
curl http://localhost:8000/api/migration/projects/1
```

**What to verify:**
- Full project detail including `diff_snapshot`, `migration_plan`, script content
- Connection names are populated via relationship loading

### Step 4: Generate Migration Plan (POST `/api/migration/projects/{id}/plan`)

```bash
curl -X POST http://localhost:8000/api/migration/projects/1/plan
```

**What to verify:**
- `steps` array with `pre_check`, optional `backup`, `ddl` steps, and `verify`
- `execution_order` respects FK dependencies
- `overall_complexity` is `simple`/`moderate`/`complex`/`high-risk`
- `pre_migration_checklist` and `post_migration_checklist` are populated
- `rollback_strategy` mentions down.sql and/or backup
- If Ollama is running: `llm_used: true`, steps may have additional warnings
- If Ollama is not running: plan still succeeds with deterministic values
- Project `status` updates to `"planned"`

### Step 5: Generate Scripts (POST `/api/migration/projects/{id}/scripts`)

```bash
curl -X POST http://localhost:8000/api/migration/projects/1/scripts \
  -H "Content-Type: application/json" \
  -d '{"target_dialect": "postgresql"}'
```

Try with different dialects: `postgresql`, `mysql`, `sqlite`

**What to verify:**
- `up_sql` contains valid DDL for the target dialect
- `down_sql` reverses the up migration
- `verify_sql` has SELECT queries to validate the migration
- PostgreSQL: double-quote identifiers, `USING` clause for type casts
- MySQL: backtick identifiers, `SET FOREIGN_KEY_CHECKS`, `MODIFY COLUMN`
- SQLite: table recreate pattern for type/nullability changes
- `warnings` array lists data-loss risks (DROP TABLE, DROP COLUMN)
- Project `status` updates to `"scripted"`

### Step 6: Download Individual Script (GET `/api/migration/projects/{id}/scripts/{filename}`)

```bash
# Download up.sql
curl http://localhost:8000/api/migration/projects/1/scripts/up.sql

# Download down.sql
curl http://localhost:8000/api/migration/projects/1/scripts/down.sql

# Download verify.sql
curl http://localhost:8000/api/migration/projects/1/scripts/verify.sql

# Invalid filename → 400
curl http://localhost:8000/api/migration/projects/1/scripts/bad.sql
```

**What to verify:**
- Returns plain text SQL with `Content-Disposition: attachment` header
- `bad.sql` returns 400 with helpful error message

### Step 7: Generate Data Migration (POST `/api/migration/projects/{id}/data-migration`)

```bash
curl -X POST "http://localhost:8000/api/migration/projects/1/data-migration?batch_size=5000"
```

**What to verify:**
- `table_migrations` array (only for `modified` tables, not added/removed)
- Each table migration has `column_mappings`, `insert_sql`, `batched_insert_sql`, `count_verify_sql`
- INSERT targets staging table (`table__new`), SELECT from original table
- Type-changed columns have `CAST` in their `transform_expression`
- New columns use default value or NULL
- `batch_size` parameter is reflected in `batched_insert_sql` LIMIT clause
- `batch_size` validation: min 100, max 100000

### Step 8: Delete Project (DELETE `/api/migration/projects/{id}`)

```bash
curl -X DELETE http://localhost:8000/api/migration/projects/1
```

**What to verify:**
- Returns 204 No Content
- Subsequent GET returns 404

---

## Manual Testing: Frontend UI

Start both backend and frontend:

```bash
# Terminal 1
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and navigate to the **Migration** tab in the header.

### Compare Tab

1. Select a **source** and **target** database connection from the dropdowns
2. Click **Compare Schemas**
3. Verify the diff visualization shows:
   - Tables grouped by change type (added/removed/modified)
   - Column-level changes with risk badges (low/medium/high/critical)
   - Overall risk assessment and summary text
4. Optionally check **Save as project** and provide a name
5. Verify the project appears in the Projects tab after saving

### Projects Tab

1. Verify the project list loads and shows name, status, risk level, dates
2. Click a project to select it — this enables the Plan/Scripts/Data tabs
3. Try deleting a project and verify it disappears from the list

### Plan Tab

1. With a project selected, click **Generate Plan**
2. Verify the plan shows:
   - Ordered steps with step numbers, actions, descriptions
   - Risk badges per step
   - Warnings (e.g., DATA LOSS for table drops)
   - Pre/post migration checklists
   - Overall complexity and downtime estimate
   - Rollback strategy

### Scripts Tab

1. Select a target dialect (PostgreSQL / MySQL / SQLite)
2. Click **Generate Scripts**
3. Verify three script panels appear: `up.sql`, `down.sql`, `verify.sql`
4. Verify syntax highlighting and content correctness
5. Click download buttons to save individual `.sql` files

### Data Tab

1. Click **Generate Data Migration** (optionally adjust batch size)
2. Verify table migration cards appear for modified tables
3. Check INSERT SQL shows staging table pattern (`table__new`)
4. Verify batched SQL includes LIMIT/OFFSET
5. Verify count verification SQL compares source vs staging

---

## Database Migration (Alembic)

The branch includes migration `b7e3a1d2f456` which:
- Creates the `migration_projects` table with all necessary columns
- Adds `model_migration_planner` and `timeout_migration_planner` to `system_settings`

### Apply migration

```bash
alembic upgrade head
```

### Verify migration applied

```bash
alembic current
# Should show: b7e3a1d2f456

# Check the table exists
python -c "
import sqlite3
conn = sqlite3.connect('database_guru.db')
cursor = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='migration_projects'\")
print('Table exists:', cursor.fetchone() is not None)
cursor = conn.execute('PRAGMA table_info(migration_projects)')
for col in cursor.fetchall():
    print(f'  {col[1]}: {col[2]}')
conn.close()
"
```

### Rollback migration

```bash
alembic downgrade f451a46c49e1
```

Verify `migration_projects` table is dropped and `system_settings` columns are removed.

---

## Known Limitations & Edge Cases

### Functional limitations

| Limitation | Detail |
|-----------|--------|
| **No DDL execution** | Scripts are generated but never executed against target databases. Users must copy/download and run manually. |
| **SQLite ALTER COLUMN** | SQLite doesn't support `ALTER COLUMN`. The toolkit generates a table recreate pattern (`CREATE __new → INSERT → DROP → RENAME`). Full source/target schemas must be available for unchanged columns to be preserved. |
| **Data migration is read-only** | INSERT INTO SELECT queries are generated but not executed. The staging table (`table__new`) must be created separately (by the `up.sql` script). |
| **LLM enrichment is optional** | If Ollama is unavailable, the planner and scripts still work with deterministic logic only. |
| **Self-referencing tables** | Data migration uses a staging table pattern to avoid `INSERT INTO X SELECT FROM X` issues, but self-referencing FKs within a table may need manual ordering. |

### Edge cases to watch for

1. **Deleted connections**: If a source or target connection is soft-deleted (`is_deleted=True`), the diff endpoint will return 404. Existing projects with deleted connections will show `null` for connection names.

2. **Schema drift**: If the database schema changes between diff and script generation, the scripts may be stale. Re-running diff + plan + scripts is recommended.

3. **Large schemas**: Schema diffing with hundreds of tables may be slow due to SchemaCache fetching. The diff itself is O(tables × columns) and should be fast.

4. **Circular FK dependencies**: The topological sort handles cycles by appending remaining tables at the end with a warning log. Check logs for "Circular FK dependencies detected".

5. **No full schema for SQLite recreate**: If source/target schemas aren't available when generating scripts, the SQLite recreate will only include columns from the diff (a warning is emitted). This could silently drop unchanged columns.

6. **`batch_size` bounds**: The API validates `batch_size` between 100 and 100,000. Values outside this range return 422 Validation Error.

### Pre-existing test failures

These tests are unrelated to Phase 20 and may fail in the full test suite:
- `test_mappings_api`
- `test_mapping_cache`
- `test_query_endpoints`
- `test_pooling_performance`
- `test_parallel_multi_db`
