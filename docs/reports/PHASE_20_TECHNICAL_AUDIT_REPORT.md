# Phase 20 Technical Audit Report: Database Migration Toolkit

## 1. The Wins (What works exceptionally well?)
- **DevOps Engineer**: The multi-stage `Dockerfile` and `docker-compose.yml` are excellent. They implement strict security practices like dropping setuid/setgid binaries, creating a non-root `appuser`, and using `no-new-privileges:true`. The `entrypoint.sh` script elegantly handles Alembic migrations.
- **Senior Engineer**: The fallback mechanism in `migration_planner.py` for LLM failures (`try/except` falling back to deterministic planning) is highly resilient. DRY principles are generally maintained well, relying heavily on a shared `SchemaDiff` model across various services.
- **Data Architect**: `schema_comparator.py` showcases fantastic handling of SQL type normalization, resolving synonyms (e.g., `int4` -> `integer`), and accurately classifying the risk of type narrowing (e.g., going from `bigint` to `smallint` as breaking). The `SchemaDiff` effectively provides lineage traceability between source and target schemas.
- **Data Analyst**: The deterministic approach to SQLite's `ALTER COLUMN` workaround (`CREATE __new` -> `INSERT INTO SELECT` -> `DROP` -> `RENAME`) is highly data-integrity conscious. 

## 2. Issues & Bugs (Functional errors or logic gaps)
* **Senior Engineer Focus**: 
  - **SQL Formatting Bug in Batched Insert SQL**: In `data_migration_assistant.py` (lines 269 and 276), the string interpolation uses the literal `{offset}` using double braces `{{offset}}`. If a user downloads this generated `.sql` file, it will contain the literal syntax `OFFSET {offset}` which is invalid SQL unless parsed by Python later.
  - **Missing FastAPI Exception Handlers for DB Commits**: In `src/api/endpoints/migration.py`, if `db.commit()` fails due to DB constraints or connection loss, an internal server error is thrown without explicitly rolling back safely in the exception block.

## 3. Security Concerns
- **Prompt Injection Resilience**: The LLM integration in `migration_planner.py` derives its context from system-generated diff summaries rather than raw user inputs, effectively mitigating most direct prompt injection vectors. 
- **Insecure Local API Exposures**: The API router currently lacks explicit authorization or ownership checks on the `connection_id`. Any user who can hit the endpoint might be able to run diffs against any connections if they guess the ID, though this depends on broader app config.

## 4. Current Thoughts on New Functionality
- **Project Manager**: The feature is cohesive and addresses a major pain point (database schema drift & data migration). Technical debt is managed nicely by not making the LLM a hard dependency (it remains optional).
- **Edge Cases**: 
  - SQLite table recreates will quietly drop unchanged columns if the authoritative schema definitions aren't available, logging a warning but still functioning.
  - "Self-referencing" Foreign Keys could break the `DataMigrationAssistant`'s table-level topological sort during `INSERT INTO SELECT` operations.

## 5. Future Direction (Next steps)
- **Automated Execution**: Allow the Database Guru to actually *execute* the generated migration scripts against target connections, rather than just generating them as text files.
- **Data Integrity Tests**: Expand `verify.sql` to include checksum-based data validation (hashing column concatenations) instead of simple row counts.
- **Interactive Script Editing**: Provide a frontend code editor to allow users to tweak LLM-generated LLM scripts before downloading them.

---

## 6. Post-Release Additions (2026-02-21)

### SQL Server (MSSQL) and Oracle dialect support

Both dialects were added to the migration toolkit after the initial Phase 20 release. Changes are purely additive — no existing dialect behaviour was modified.

**Files changed:**
- `requirements.txt`: `pymssql==2.3.1`, `oracledb==2.3.0`
- `src/llm/dialect_registry.py`: `DatabaseDialect.MSSQL`, `DatabaseDialect.ORACLE` enum values, `DialectRules`, LLM prompt context, `get_dialect_for_database_type()` mapping
- `src/core/user_db_connector.py`: Connection URL builders; both added to the sync session path alongside DuckDB
- `src/core/connection_pool_manager.py`: Both added to the sync engine creation path
- `src/migration/schema_comparator.py`: 14 MSSQL type synonyms (`nvarchar`, `bit`, `datetime2`, `uniqueidentifier`, etc.) and 12 Oracle type synonyms (`varchar2`, `clob`, `number`, `blob`, etc.)
- `src/migration/script_generator.py`: Full DDL generation for both dialects (see testing guide for specifics)
- `frontend/src/components/DatabaseConnectionModal.tsx`: `mssql` and `oracle` selectable types with correct default ports (1433, 1521)

**Architecture note — Oracle scripts require SQL*Plus-style block terminators:**
Oracle's `BEGIN/EXCEPTION/END` blocks generated for `DROP TABLE` and `DROP INDEX` operations use `/` terminators. These are valid for SQL*Plus, SQLcl, and most Oracle GUI tools. Users running scripts via JDBC or other drivers that don't support block terminators will need to strip the `/` lines or execute the `EXECUTE IMMEDIATE` statements individually.
