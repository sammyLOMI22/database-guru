# PR Review Tracker: CSV/Excel Data Source Support (Phase 13)

**Last updated:** 2026-02-08

---

## Blockers (Must Fix Before Merge)

| # | Issue | Source | Status | Fix |
|---|-------|--------|--------|-----|
| 1 | **Path traversal via `session_id`** — `session_id` from form data used directly in `mkdir(parents=True)` without UUID validation (`file_source_handler.py:365`) | Review #5 | **FIXED** | Added `uuid.UUID()` validation; raises `FileValidationError` on invalid format |
| 2 | **No read-only enforcement on DuckDB queries** — `_execute_sync` runs raw LLM-generated SQL with no DDL/DML rejection (`file_source_session.py:279`). DuckDB supports `COPY TO`, `DROP TABLE`, `ATTACH`. | Review #5 + Jules #3 | **FIXED** | Added `_DANGEROUS_SQL` regex guard rejecting INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/COPY TO/ATTACH/DETACH/EXPORT/IMPORT |
| 3 | **`delete_file` loads ALL chat sessions** — `select(ChatSession)` with no filter iterates every session in Python (`files.py:230`) | Review #5 | **FIXED** | Filtered query to only load sessions whose `active_file_source_ids` JSON contains the target file ID |
| 4 | **Committed test file** — `uploads/global/cc6876bdeb14_test.xlsx` tracked in git | Review #5 | **FIXED** | `git rm --cached` to remove from tracking |
| 5 | **Cache key collision** — `multi_db_query.py:363` computes cache key from question + connection IDs but excludes `file_source_ids`. Different files, same question = wrong cached results. | Audit Report | **FIXED** | Added `file_source_ids` to cache key hash, bumped version to `v3` |

## Should Fix (Pre-Merge)

| # | Issue | Source | Status | Fix |
|---|-------|--------|--------|-----|
| 6 | **`setInterval` memory leak** — `FileUploadModal.tsx:93-116` only clears the interval on success; if upload throws, interval runs forever. Needs `finally` block. | Review #5 | **FIXED** | Moved `clearInterval` to `finally` block |
| 7 | **Connection validation accepts soft-deleted connections** — `chat.py:104-116` validates connection IDs but doesn't filter `is_deleted=True`, allowing deleted connections to be associated with sessions. | Review #5 | **FIXED** | Added `is_deleted.isnot(True)` filter in both create and update session validation |
| 8 | **`get_excel_sheets` has no file size check** — `file_source_handler.py:537` does `content = await file.read()` with no size limit, enabling OOM via large uploads. The `/upload` endpoint validates size, but this one doesn't. | Review #5 | **FIXED** | Added size validation before `file.read()` using `FILE_MAX_SIZE_MB` from settings |
| 9 | **SQLValidator `is_read_only` misses CTE queries** — regex only matches `SELECT`, not `WITH`. Valid read-only CTEs may be rejected. (`sql_generator.py:45`) | Jules #3 + Audit | **FIXED** | Updated `READ_ONLY_PATTERN` to `^\s*(SELECT\|WITH)\s+` |
| 10 | **Unused `python-magic` dependency** — listed in `requirements.txt` but never imported. | Review #5 | **FIXED** | Removed from `requirements.txt` |
| 11 | **Dead frontend props** — `DataSourcesPanel.tsx` has `selectedFileIds` and `onDataSourcesChange` declared but never used. | Review #5 | **FIXED** | Removed from Props interface and destructuring |
| 12 | **`console.log('DEBUG: ...')`** left in `EnhancedChatInterface.tsx:170-172` | Review #5 | **FIXED** | Removed 3 debug statements |

## Nice to Have (Post-Merge OK)

| # | Issue | Source | Status |
|---|-------|--------|--------|
| 13 | No self-correction for file queries — `MultiDatabaseHandler` uses basic `generate_sql` for DuckDB instead of `SelfCorrectingSQLAgent` | Jules #3 | OPEN |
| 14 | CTE lineage gap — `SQLLineageParser` can't parse `WITH` clauses, treats CTE names as source tables | Jules #3 | OPEN |
| 15 | DRY violations — DuckDB `read_csv_auto` construction duplicated between `FileSourceHandler` and `FileSourceDuckDBSession` | Jules #3 | OPEN |
| 16 | Synchronous `excel_to_temp_csv` in async context — could block event loop for large Excel files | Audit Report | OPEN |
| 17 | Simulated upload progress — uses `setInterval` timer instead of actual `onUploadProgress` from Axios | Audit Report | OPEN |
| 18 | N+1 queries in `list_chat_sessions` — 3 extra DB queries per session | Review #5 | OPEN |
| 19 | CSV parsed 3x during schema inference — `read_csv_auto()` called 3 times for LIMIT 0, COUNT, LIMIT 5 | Review #5 | OPEN |
| 20 | File deduplication collision — same hash+filename silently overwrites via `os.replace`; deleting one kills the other | Review #5 | OPEN |
| 21 | Missing test coverage — no tests for `process_upload()`, `execute_query()`, API endpoints in `files.py`, `excel_to_temp_csv()` | Review #5 | OPEN |
| 22 | Frontend accessibility — `FileUploadModal` lacks `role="dialog"`, `aria-modal`, focus trap, Escape key | Review #5 | OPEN |

## Already Fixed (Prior to This Round)

| Issue | Status |
|-------|--------|
| `_get_session_file_sources` commits during reads | Fixed (defensive cleanup only) |
| Duplicate `addFileToSession` API calls | Fixed (single call pattern) |
| Double-commit in delete pipeline | Fixed |
| DuckDB memory_limit injection | Safe (value from settings, not user input) |

---

**Result:** All 5 blockers and 7 should-fix items resolved. 1330 tests pass, 0 regressions. Ready to merge.
