Phase 18: Edit Mode & DML Operations — Implementation Plan                                                                           
                                                        
 Context

 Phase 18 adds inline data editing to Database Guru. Users can modify query results directly — editing cells, adding rows, deleting
 rows — with automatic DML generation, preview, and safe execution against their databases. This is the highest-priority feature
 post-Phase 21 (Auth), which provided the ownership and audit infrastructure this feature depends on.

 Source plan: docs/planning/EDIT_MODE_DML_PLAN.md

 ---
 Key Design Corrections from Original Plan

 1. Parameterized queries for execution — The plan's DMLGenerator uses string interpolation (_format_value()), which is
 SQL-injection-vulnerable. We'll generate parameterized SQL (:param placeholders) for execution and display SQL (with literals) for
 preview only.
 2. Execute against USER database, not metadata DB — The plan's DMLExecutor takes a metadata AsyncSession. DML must run against the
 user's database via UserDatabaseConnector.get_user_db_session(connection). Audit logs go to the metadata DB separately.
 3. Client-side change tracking — No server-side stateful ChangeTracker. The frontend tracks changes in React state and sends the
 finalized change list to the backend for generation/execution.
 4. Reuse existing AuditLog — Instead of a new DMLAuditLog model, use log_action() from src/auth/audit.py with action="dml_execute"
 and DML-specific data in the details JSON field.
 5. SQL-only — NoSQL databases are excluded from edit mode. UI disables the toggle for NoSQL connections.

 ---
 Implementation Steps

 Step 1: Database Model + Migration + Settings

 Create/modify:
 - src/database/models.py — Add ConnectionWritePermission model
 - alembic/versions/<hash>_add_connection_write_permissions.py — Migration
 - src/config/settings.py — Add DML_MAX_ROWS_PER_OPERATION: int = 100

 ConnectionWritePermission fields:
 - connection_id (FK to database_connections.id, unique, CASCADE delete)
 - allow_insert, allow_update, allow_delete (Boolean, default False)
 - require_where_clause (Boolean, default True)
 - max_rows_per_operation (Integer, default 100)
 - allowed_tables (JSON, nullable — null = all tables)
 - created_at, updated_at (DateTime with UTC default)

 ---
 Step 2: DML Module — Models & Generator

 Create:
 - src/dml/__init__.py
 - src/dml/models.py — Pydantic schemas: ChangeType enum, CellChangeSchema, RowChangeSchema, DMLPreviewRequest, DMLExecuteRequest,
 DMLStatement, ExecutionResult
 - src/dml/dml_generator.py — DMLGenerator class

 DMLGenerator produces two outputs per statement:
 - display_sql — Human-readable with literal values (for preview panel)
 - parameterized_sql + params dict — For safe execution via text().bindparams()

 Dialect-aware quoting: PostgreSQL/SQLite ("), MySQL (`), MSSQL ([]), Oracle (none/")

 Ordering: DELETEs first, UPDATEs second, INSERTs last (FK constraint safety)

 Reuse: _quote_identifier() per dialect, identifier validation regex

 ---
 Step 3: DML Validator

 Create: src/dml/dml_validator.py

 Validation checks:
 1. Global ALLOW_WRITE_OPERATIONS setting is True
 2. ConnectionWritePermission record exists with matching flags (allow_insert/update/delete)
 3. Table names in allowed_tables whitelist (if set)
 4. Non-empty primary keys for UPDATE/DELETE (if require_where_clause)
 5. Row count per operation type ≤ max_rows_per_operation
 6. Table/column names pass safe-identifier regex
 7. Connection ownership check (user owns connection or it's unowned)

 ---
 Step 4: DML Executor

 Create: src/dml/dml_executor.py

 Two-session architecture:
 - User DB session via UserDatabaseConnector.get_user_db_session(connection) — executes DML
 - Metadata DB session via get_db dependency — writes audit logs via log_action()

 Flow:
 1. Open user DB session
 2. Execute each parameterized statement via session.execute(text(sql).bindparams(**params))
 3. On any failure → rollback user DB, log failure audit
 4. On success → commit user DB, log each change audit
 5. Handle async vs sync sessions (like SQLExecutor does for DuckDB/MSSQL/Oracle)

 Reuse: log_action() from src/auth/audit.py, UserDatabaseConnector from src/core/user_db_connector.py

 ---
 Step 5: API Endpoints

 Create: src/api/endpoints/dml.py
 Modify: src/main.py — Add dml to imports and app.include_router(dml.router, prefix="/api")

 ┌──────────────────────────────────────────────────┬────────┬───────────────────┬───────────────────────────────────────────────┐
 │                     Endpoint                     │ Method │       Auth        │                    Purpose                    │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/preview                                 │ POST   │ get_optional_user │ Generate display SQL from changes             │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/execute                                 │ POST   │ get_current_user  │ Validate + execute DML (always requires auth) │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/permissions/{connection_id}             │ GET    │ get_optional_user │ Get write permission config                   │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/permissions/{connection_id}             │ PUT    │ get_current_user  │ Update write permissions                      │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/table-info/{connection_id}/{table_name} │ GET    │ get_optional_user │ Get PK columns + column types                 │
 └──────────────────────────────────────────────────┴────────┴───────────────────┴───────────────────────────────────────────────┘

 /dml/table-info uses SchemaInspector.get_primary_keys() (line 452 of schema_inspector.py) and column metadata — needed by frontend
 to know which columns are PKs and what types to use in AddRowForm.

 No separate audit endpoint needed — existing /api/audit/logs serves this.

 ---
 Step 6: Frontend — Types, API Client, Hooks

 Create:
 - frontend/src/types/dml.ts — ChangeType, CellChange, RowChange, WritePermission, TableInfo, response types
 - frontend/src/services/dmlApi.ts — API client methods (preview, execute, getPermissions, updatePermissions, getTableInfo)
 - frontend/src/hooks/useChangeTracker.ts — Client-side change tracking (Map<string, RowChange>, methods: trackUpdate, trackInsert,
 trackDelete, discardChange, discardAll, getChanges, getSummary)
 - frontend/src/hooks/useEditMode.ts — Edit mode state, permission fetch, isEditMode, canEdit, toggleEditMode
 - frontend/src/hooks/useDMLExecution.ts — @tanstack/react-query mutations for preview/execute

 ---
 Step 7: Frontend — Editable Table Components

 Create:
 - frontend/src/components/edit/EditModeToggle.tsx — Lock/Pencil toggle, disabled for NoSQL
 - frontend/src/components/edit/EditableCell.tsx — Click-to-edit cell with type-aware input, visual indicator for modified cells
 - frontend/src/components/edit/EditableRow.tsx — Row with checkbox, delete button, color coding (amber=modified, green=new,
 red=deleted)
 - frontend/src/components/edit/EditableQueryResults.tsx — Replaces QueryResults when edit mode is on, includes Add Row button

 Styling: Glass-morphism patterns, ring-2 ring-amber-500/50 for modified cells, Tailwind color coding

 ---
 Step 8: Frontend — Modals & Preview

 Create:
 - frontend/src/components/edit/AddRowForm.tsx — Modal with schema-aware form fields, auto-increment PKs disabled
 - frontend/src/components/edit/DeleteConfirmation.tsx — Shows rows to delete + generated SQL
 - frontend/src/components/edit/DMLPreviewPanel.tsx — Full SQL preview, Copy/Download/Execute buttons
 - frontend/src/components/edit/ChangesSummaryBar.tsx — Bottom bar with change counts + Preview/Discard/Save buttons

 ---
 Step 9: Wire Into Existing UI

 Modify:
 - frontend/src/components/MultiDatabaseResults.tsx — Add edit mode toggle, conditionally render EditableQueryResults
 - frontend/src/components/QueryResults.tsx — May need minor props additions

 Table name detection: Parse FROM clause from the SQL. Edit mode only enabled for single-table SELECT queries (no JOINs/subqueries).

 ---
 Step 10: Tests

 Create:
 - tests/dml/__init__.py
 - tests/dml/test_dml_generator.py — All dialects, parameterized output, NULL/bool/datetime handling
 - tests/dml/test_dml_validator.py — Each validation rule
 - tests/dml/test_dml_executor.py — Mocked user DB sessions, rollback on error, audit logging
 - tests/dml/test_dml_endpoints.py — Integration tests: auth, permissions, 403/401 cases

 ---
 Step 11 (Deferred): Natural Language DML

 Can be added after core edit mode is working. Follows existing query generation pipeline pattern with DML-restricted system prompt.

 ---
 Critical Files Reference

 ┌──────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
 │                       File                       │                         Why                          │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/core/user_db_connector.py                    │ get_user_db_session() — execute DML against user DBs │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/core/executor.py                             │ Pattern for async/sync session handling              │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/auth/audit.py                                │ log_action() — reuse for DML audit                   │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/auth/dependencies.py                         │ get_current_user, get_optional_user                  │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/core/schema_inspector.py:452                 │ get_primary_keys() for table-info endpoint           │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/main.py:15,186-208                           │ Router imports and registration                      │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/database/models.py                           │ Add ConnectionWritePermission                        │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/config/settings.py                           │ Add DML settings                                     │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ frontend/src/components/QueryResults.tsx         │ Component to extend/wrap                             │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ frontend/src/components/MultiDatabaseResults.tsx │ Integration point for edit toggle                    │
 └──────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

 Verification

 1. Backend unit tests: ./run_tests.sh tests/dml/
 2. Manual API testing: Swagger UI at /api/docs — test preview, permissions, execute endpoints
 3. Frontend: cd frontend && npm run dev — toggle edit mode on query results, edit cells, add/delete rows, preview SQL, execute
 4. Security: Verify unauthenticated users cannot execute DML, permissions are enforced, audit logs are created

 Phase 18: Edit Mode & DML Operations — Implementation Plan                                                                           
                                                        
 Context

 Phase 18 adds inline data editing to Database Guru. Users can modify query results directly — editing cells, adding rows, deleting
 rows — with automatic DML generation, preview, and safe execution against their databases. This is the highest-priority feature
 post-Phase 21 (Auth), which provided the ownership and audit infrastructure this feature depends on.

 Source plan: docs/planning/EDIT_MODE_DML_PLAN.md

 ---
 Key Design Corrections from Original Plan

 1. Parameterized queries for execution — The plan's DMLGenerator uses string interpolation (_format_value()), which is
 SQL-injection-vulnerable. We'll generate parameterized SQL (:param placeholders) for execution and display SQL (with literals) for
 preview only.
 2. Execute against USER database, not metadata DB — The plan's DMLExecutor takes a metadata AsyncSession. DML must run against the
 user's database via UserDatabaseConnector.get_user_db_session(connection). Audit logs go to the metadata DB separately.
 3. Client-side change tracking — No server-side stateful ChangeTracker. The frontend tracks changes in React state and sends the
 finalized change list to the backend for generation/execution.
 4. Reuse existing AuditLog — Instead of a new DMLAuditLog model, use log_action() from src/auth/audit.py with action="dml_execute"
 and DML-specific data in the details JSON field.
 5. SQL-only — NoSQL databases are excluded from edit mode. UI disables the toggle for NoSQL connections.

 ---
 Implementation Steps

 Step 1: Database Model + Migration + Settings

 Create/modify:
 - src/database/models.py — Add ConnectionWritePermission model
 - alembic/versions/<hash>_add_connection_write_permissions.py — Migration
 - src/config/settings.py — Add DML_MAX_ROWS_PER_OPERATION: int = 100

 ConnectionWritePermission fields:
 - connection_id (FK to database_connections.id, unique, CASCADE delete)
 - allow_insert, allow_update, allow_delete (Boolean, default False)
 - require_where_clause (Boolean, default True)
 - max_rows_per_operation (Integer, default 100)
 - allowed_tables (JSON, nullable — null = all tables)
 - created_at, updated_at (DateTime with UTC default)

 ---
 Step 2: DML Module — Models & Generator

 Create:
 - src/dml/__init__.py
 - src/dml/models.py — Pydantic schemas: ChangeType enum, CellChangeSchema, RowChangeSchema, DMLPreviewRequest, DMLExecuteRequest,
 DMLStatement, ExecutionResult
 - src/dml/dml_generator.py — DMLGenerator class

 DMLGenerator produces two outputs per statement:
 - display_sql — Human-readable with literal values (for preview panel)
 - parameterized_sql + params dict — For safe execution via text().bindparams()

 Dialect-aware quoting: PostgreSQL/SQLite ("), MySQL (`), MSSQL ([]), Oracle (none/")

 Ordering: DELETEs first, UPDATEs second, INSERTs last (FK constraint safety)

 Reuse: _quote_identifier() per dialect, identifier validation regex

 ---
 Step 3: DML Validator

 Create: src/dml/dml_validator.py

 Validation checks:
 1. Global ALLOW_WRITE_OPERATIONS setting is True
 2. ConnectionWritePermission record exists with matching flags (allow_insert/update/delete)
 3. Table names in allowed_tables whitelist (if set)
 4. Non-empty primary keys for UPDATE/DELETE (if require_where_clause)
 5. Row count per operation type ≤ max_rows_per_operation
 6. Table/column names pass safe-identifier regex
 7. Connection ownership check (user owns connection or it's unowned)

 ---
 Step 4: DML Executor

 Create: src/dml/dml_executor.py

 Two-session architecture:
 - User DB session via UserDatabaseConnector.get_user_db_session(connection) — executes DML
 - Metadata DB session via get_db dependency — writes audit logs via log_action()

 Flow:
 1. Open user DB session
 2. Execute each parameterized statement via session.execute(text(sql).bindparams(**params))
 3. On any failure → rollback user DB, log failure audit
 4. On success → commit user DB, log each change audit
 5. Handle async vs sync sessions (like SQLExecutor does for DuckDB/MSSQL/Oracle)

 Reuse: log_action() from src/auth/audit.py, UserDatabaseConnector from src/core/user_db_connector.py

 ---
 Step 5: API Endpoints

 Create: src/api/endpoints/dml.py
 Modify: src/main.py — Add dml to imports and app.include_router(dml.router, prefix="/api")

 ┌──────────────────────────────────────────────────┬────────┬───────────────────┬───────────────────────────────────────────────┐
 │                     Endpoint                     │ Method │       Auth        │                    Purpose                    │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/preview                                 │ POST   │ get_optional_user │ Generate display SQL from changes             │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/execute                                 │ POST   │ get_current_user  │ Validate + execute DML (always requires auth) │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/permissions/{connection_id}             │ GET    │ get_optional_user │ Get write permission config                   │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/permissions/{connection_id}             │ PUT    │ get_current_user  │ Update write permissions                      │
 ├──────────────────────────────────────────────────┼────────┼───────────────────┼───────────────────────────────────────────────┤
 │ /api/dml/table-info/{connection_id}/{table_name} │ GET    │ get_optional_user │ Get PK columns + column types                 │
 └──────────────────────────────────────────────────┴────────┴───────────────────┴───────────────────────────────────────────────┘

 /dml/table-info uses SchemaInspector.get_primary_keys() (line 452 of schema_inspector.py) and column metadata — needed by frontend
 to know which columns are PKs and what types to use in AddRowForm.

 No separate audit endpoint needed — existing /api/audit/logs serves this.

 ---
 Step 6: Frontend — Types, API Client, Hooks

 Create:
 - frontend/src/types/dml.ts — ChangeType, CellChange, RowChange, WritePermission, TableInfo, response types
 - frontend/src/services/dmlApi.ts — API client methods (preview, execute, getPermissions, updatePermissions, getTableInfo)
 - frontend/src/hooks/useChangeTracker.ts — Client-side change tracking (Map<string, RowChange>, methods: trackUpdate, trackInsert,
 trackDelete, discardChange, discardAll, getChanges, getSummary)
 - frontend/src/hooks/useEditMode.ts — Edit mode state, permission fetch, isEditMode, canEdit, toggleEditMode
 - frontend/src/hooks/useDMLExecution.ts — @tanstack/react-query mutations for preview/execute

 ---
 Step 7: Frontend — Editable Table Components

 Create:
 - frontend/src/components/edit/EditModeToggle.tsx — Lock/Pencil toggle, disabled for NoSQL
 - frontend/src/components/edit/EditableCell.tsx — Click-to-edit cell with type-aware input, visual indicator for modified cells
 - frontend/src/components/edit/EditableRow.tsx — Row with checkbox, delete button, color coding (amber=modified, green=new,
 red=deleted)
 - frontend/src/components/edit/EditableQueryResults.tsx — Replaces QueryResults when edit mode is on, includes Add Row button

 Styling: Glass-morphism patterns, ring-2 ring-amber-500/50 for modified cells, Tailwind color coding

 ---
 Step 8: Frontend — Modals & Preview

 Create:
 - frontend/src/components/edit/AddRowForm.tsx — Modal with schema-aware form fields, auto-increment PKs disabled
 - frontend/src/components/edit/DeleteConfirmation.tsx — Shows rows to delete + generated SQL
 - frontend/src/components/edit/DMLPreviewPanel.tsx — Full SQL preview, Copy/Download/Execute buttons
 - frontend/src/components/edit/ChangesSummaryBar.tsx — Bottom bar with change counts + Preview/Discard/Save buttons

 ---
 Step 9: Wire Into Existing UI

 Modify:
 - frontend/src/components/MultiDatabaseResults.tsx — Add edit mode toggle, conditionally render EditableQueryResults
 - frontend/src/components/QueryResults.tsx — May need minor props additions

 Table name detection: Parse FROM clause from the SQL. Edit mode only enabled for single-table SELECT queries (no JOINs/subqueries).

 ---
 Step 10: Tests

 Create:
 - tests/dml/__init__.py
 - tests/dml/test_dml_generator.py — All dialects, parameterized output, NULL/bool/datetime handling
 - tests/dml/test_dml_validator.py — Each validation rule
 - tests/dml/test_dml_executor.py — Mocked user DB sessions, rollback on error, audit logging
 - tests/dml/test_dml_endpoints.py — Integration tests: auth, permissions, 403/401 cases

 ---
 Step 11 (Deferred): Natural Language DML

 Can be added after core edit mode is working. Follows existing query generation pipeline pattern with DML-restricted system prompt.

 ---
 Critical Files Reference

 ┌──────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
 │                       File                       │                         Why                          │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/core/user_db_connector.py                    │ get_user_db_session() — execute DML against user DBs │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/core/executor.py                             │ Pattern for async/sync session handling              │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/auth/audit.py                                │ log_action() — reuse for DML audit                   │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/auth/dependencies.py                         │ get_current_user, get_optional_user                  │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/core/schema_inspector.py:452                 │ get_primary_keys() for table-info endpoint           │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/main.py:15,186-208                           │ Router imports and registration                      │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/database/models.py                           │ Add ConnectionWritePermission                        │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ src/config/settings.py                           │ Add DML settings                                     │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ frontend/src/components/QueryResults.tsx         │ Component to extend/wrap                             │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
 │ frontend/src/components/MultiDatabaseResults.tsx │ Integration point for edit toggle                    │
 └──────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

 Verification

 1. Backend unit tests: ./run_tests.sh tests/dml/
 2. Manual API testing: Swagger UI at /api/docs — test preview, permissions, execute endpoints
 3. Frontend: cd frontend && npm run dev — toggle edit mode on query results, edit cells, add/delete rows, preview SQL, execute
 4. Security: Verify unauthenticated users cannot execute DML, permissions are enforced, audit logs are created