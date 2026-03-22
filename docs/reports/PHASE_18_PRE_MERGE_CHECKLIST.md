# Phase 18 / 21 Pre-Merge Checklist

## Status
- Automated verification: `112` passing tests
  - Backend: `96`
  - Frontend: `16`
- Remaining manual check: browser confirmation that the table stays visually in sync after save for edit/add/delete flows

## Automated
- [x] Targeted backend tests pass
  - `tests/dml/test_dml_generator.py`
  - `tests/dml/test_dml_validator.py`
  - `tests/dml/test_dml_executor.py`
  - `tests/test_auth.py`
  - `tests/test_rate_limit_user.py`
- [x] Additional backend coverage pass
  - `tests/dml/test_dml_api.py`
  - Added `INSERT` / `DELETE` executor coverage
  - Added cross-user ownership coverage
  - Added empty primary-key guard coverage
- [x] Touched frontend tests pass
  - `frontend/tests/Header.test.tsx`
  - `frontend/tests/MultiDatabaseResults.test.tsx`
- [ ] Optional: run the broader frontend suite
- [ ] Optional: run the broader backend suite

## Migrations / Startup
- [ ] `alembic upgrade head` succeeds on a clean database
- [x] Existing local database is already at Alembic head
- [x] Backend starts with `ALLOW_WRITE_OPERATIONS=true`
- [ ] Frontend starts and loads successfully
- [x] New schema objects verified at startup
  - `users`
  - `audit_logs`
  - `connection_write_permissions`
  - `owner_id` columns on owned resources

## Authentication / Ownership
- [x] Register works
- [x] Login works
- [x] `/api/auth/me` works with a valid token
- [x] Invalid / missing token paths return expected `401`
- [x] User B cannot access User A owned resources
- [x] Owner access paths are allowed
- [x] Unowned resource access path is covered in automated tests

## DML Permissions
- [x] Default permissions return `write_enabled=false`
- [x] Owner can enable write permissions
- [x] Non-owner cannot update / use protected permissions paths
- [x] `allowed_tables` path covered by automated validation tests
- [x] `max_rows_per_operation` path covered by automated validation tests
- [x] Insert-only / update-only / delete-only enforcement covered by automated tests

## Edit Mode API
- [x] `/api/dml/table-info/{connection_id}/{table_name}` returns PK and column metadata
- [x] `/api/dml/preview` works for `UPDATE`
- [x] `/api/dml/preview` works for `INSERT`
- [x] `/api/dml/preview` works for `DELETE`
- [x] Mixed preview ordering is `DELETE -> UPDATE -> INSERT`
- [x] Invalid table names are rejected

## Edit Mode Execution
- [x] `UPDATE` executes and persists
- [x] `INSERT` executes and persists
- [x] `DELETE` executes and persists
- [ ] Successful save keeps the UI table in sync
- [x] Failed batch rolls back completely
- [x] Global write disable rejects execution
- [x] Missing permission record rejects execution
- [x] Empty primary-key guard blocks invalid `UPDATE` / `DELETE`

## Audit / Rate Limit
- [x] Audit logs contain `register`, `login`, `create`, and `dml_execute` in verification runs
- [x] `/api/audit/logs/me` returns only current-user entries in the smoke test
- [ ] Admin-only audit endpoint is protected
- [x] Authenticated rate limiting is keyed per user in code and targeted tests
- [x] Unauthenticated rate limiting falls back to IP in targeted tests

## Compatibility
- [x] Edit mode is disabled for NoSQL connections in code/tests
- [x] Edit mode is disabled for JOIN queries in code
- [x] Edit mode is disabled for subqueries / unsupported SQL shapes in code
- [x] Smoke test on SQLite
- [ ] Smoke test on one production-like async SQL backend, ideally PostgreSQL

## Notes
- Automated coverage now includes API `INSERT` / `DELETE`, executor `INSERT` / `DELETE`, cross-user ownership, permissions paths, preview coverage for all DML types, and empty-PK generator guards.
- Frontend regression in `MultiDatabaseResults` tests is fixed by mocking `EditModeWrapper`; `16/16` touched frontend tests pass.
- Clean-database migration remains a baseline repository issue rather than a new Phase 18 regression.
- Remaining pre-merge gap is primarily browser-level confirmation that optimistic UI updates in `EditModeWrapper` match actual save behavior for edit/add/delete.
