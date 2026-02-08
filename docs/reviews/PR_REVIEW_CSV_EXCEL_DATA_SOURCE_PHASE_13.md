# PR Review: CSV/Excel Data Source Support (Phase 13)

**Branch:** `csv-excel-data-source-support`
**Commits:** 11 (3b914f3..7a9b2da)
**Files changed:** ~51 (excluding node_modules cleanup)
**Lines:** +7,308 / -158

---

## Overview

This PR adds the ability to upload CSV and Excel files and query them as first-class data sources alongside traditional database connections. Files are processed via DuckDB's `read_csv_auto()`, integrated into the existing multi-database query pipeline, and exposed through both REST API endpoints and new frontend UI components.

---

## Architecture

The implementation follows a clean layered approach:

```
Upload API  -->  FileSourceHandler (validation, storage, schema inference)
                       |
                 FileSource model (SQLAlchemy, metadata DB)
                       |
              FileSourceDuckDBSession (singleton, in-memory DuckDB)
                       |
              MultiDatabaseHandler (combined schema, LLM prompt)
```

**Good decisions:**
- DuckDB singleton with lazy table loading avoids unnecessary memory usage
- Excel files converted to temp CSV (DuckDB 1.1.x lacks `read_excel()`) with proper cleanup
- Shared `file_utils.py` for path validation and sheet name sanitization used by both handler and session
- Background cleanup task for expired files with proper cancellation on shutdown

---

## Security Review

### Strengths

1. **Path traversal prevention** (`file_utils.py:13-49`): `validate_file_path()` resolves symlinks, canonicalizes paths, and validates the result is within the upload directory. Used consistently in both `FileSourceHandler` and `FileSourceDuckDBSession`.

2. **Sheet name sanitization** (`file_utils.py:52-79`): Strips SQL-injection characters, removes comment sequences (`--`), limits length. Applied before any DuckDB queries.

3. **File content validation** (`file_source_handler.py:296-330`): Magic byte checks for XLSX/XLS, UTF-8 text verification for CSV. Prevents disguised file uploads.

4. **Filename sanitization** (`file_source_handler.py:688-716`): Strips path components, null bytes, control characters, and traversal attempts.

5. **Chunked size validation** (`file_source_handler.py:282-290`): Reads in 1MB chunks during validation to avoid loading 100MB files into memory just for a size check.

### Concerns

1. **SQL string interpolation in DuckDB queries** (`file_source_handler.py:427-430`, `file_source_session.py:196-208`): File paths are escaped with `replace("'", "''")` but not parameterized. While the paths come from `validate_file_path()` (which resolves and constrains them), parameterized queries would be more robust against edge cases. DuckDB's Python API supports `?` placeholders for some operations.

2. **`save_file` reads entire file into memory** (`file_source_handler.py:351`): `content = await file.read()` loads the whole file for hashing. For 100MB files, this is a significant allocation. Streaming hash computation with chunked reads would be better for production.

3. **DuckDB `LIMIT` injection** (`file_source_handler.py:582`): `f"{read_query} LIMIT {limit}"` — the `limit` parameter comes from the API with `Query(20, ge=1, le=100)` validation, so it's safe, but the int->string injection pattern is worth noting.

4. **Error messages expose internal paths** (`file_source_handler.py:259`, `file_utils.py:43`): Validation errors like "File path must be within upload directory: /full/path" leak server filesystem structure. Consider generic error messages for production.

---

## Code Quality

### Backend

**`FileSourceHandler` (835 lines)** — Well-structured with clear method responsibilities. The `_duckdb_read_context` context manager (line 408) is a good abstraction that centralizes connection management, path validation, Excel conversion, and temp file cleanup.

**`FileSourceDuckDBSession` (499 lines)** — Solid singleton pattern with:
- Double-checked locking for initialization (lines 71-93)
- Async lock for table load operations
- Cursor-based execution for thread safety
- Clean failure cleanup (drops partial tables, removes from loaded set)
- Proper session reset for testing

**One design note:** Class-level mutable state (`_loaded_tables: Set`, `_table_metadata: Dict`) is shared across all instances. This works fine for the singleton use case but could surprise future developers. A comment or `__init_subclass__` guard would clarify intent.

**`file_utils.py` (79 lines)** — Minimal, focused utility module. Extracting shared validation here prevents duplication between handler and session.

### API Layer (`files.py`, 376 lines)

- Clean endpoint structure: upload, list, get, delete, schema, preview, refresh, excel-sheets
- Proper HTTP status codes (400, 404, 204)
- `_file_source_to_response()` helper avoids repetition
- Error handling catches `ValueError` separately from generic exceptions

### Frontend

- **`DataSourcesPanel.tsx` (524 lines)**: Tabbed UI for databases + files. Uses portal for modals. Handles session-scoped file association.
- **`FileUploadModal.tsx` (331 lines)**: Drag-and-drop via `react-dropzone`, progress indicator, Excel sheet selection.
- **`FilePreviewPanel.tsx` (269 lines)**: Sortable column headers, row data display with loading states.
- **Type definitions** (`api.ts`): Comprehensive `FileSource`, `FileSchemaResponse`, `FilePreviewResponse` interfaces.

**Frontend concern:** `DataSourcesPanel.tsx:276-284` uses `fetch()` directly for connection operations while using `filesAPI` for file operations. The pattern is inconsistent — all API calls should go through the centralized `api.ts` service.

### Database Model (`FileSource`)

Well-indexed with targeted indexes for common access patterns:
- `idx_file_user_session` — ownership queries
- `idx_file_hash` — deduplication
- `idx_file_status` — status filtering
- `idx_file_global` — global file listing

`chat_session_id` has `ondelete="SET NULL"` — files survive session deletion, which is the right behavior for global files.

### Integration with Existing System

**`multi_db_handler.py` (+303 lines):**
- `build_combined_schema()` now accepts optional `file_sources` parameter — backward compatible
- `format_schema_for_llm()` includes file source tables with DuckDB-specific notes
- New `execute_file_query()` method routes file queries through `FileSourceDuckDBSession`

**`ChatSession` model** gains `active_file_source_ids` JSON column — mirrors the existing `active_connection_ids` pattern.

**`main.py`**: Background `_file_expiration_task` runs hourly, with proper `CancelledError` handling on shutdown and DuckDB session reset.

---

## Test Coverage

**`test_file_sources.py` (545 lines)** covers:
- File validation (CSV success, missing filename, invalid extension, oversized, empty)
- Filename sanitization (path components, traversal, special chars, empty, dot files)
- Table name generation (basic, special chars, length limits)
- Schema inference (column detection, type inference)
- File preview (basic, limit/truncation)
- DuckDB session (singleton, table loading, state reset)
- Content validation (CSV text, binary rejection, XLSX magic bytes)
- Integration (directory creation, hash deduplication)
- Path validation security (valid paths, traversal blocked, relative traversal, empty, nonexistent)
- Sheet name sanitization (valid passthrough, SQL injection removal, empty default, length limit)

**Missing test coverage:**
- No API endpoint tests (e.g., `TestClient` integration tests for upload, list, delete)
- No tests for Excel file processing (`.xlsx`/`.xls` end-to-end via `excel_to_temp_csv`)
- No tests for `FileSourceDuckDBSession.execute_query()` with actual SQL
- No tests for the `multi_db_handler` file source integration
- No tests for the chat session file source association flow
- No tests for the expired file cleanup task

---

## Issues Found

### Bugs

1. **`_get_lock()` race condition** (`file_source_session.py:46-49`): The lock creation itself is not atomic. Two coroutines could both see `cls._lock is None` and create separate locks. In practice this is unlikely since Python's GIL and the event loop serialize coroutine execution, but `reset_session()` sets `cls._lock = None` (line 456) which re-opens the window. Consider creating the lock eagerly or using a `threading.Lock` to guard creation.

2. **`list_file_sources` filter logic** (`file_source_handler.py:820-821`): `FileSource.is_global == True` triggers a SQLAlchemy warning (`SAWarning: ... use is_() instead`). Should be `FileSource.is_global.is_(True)` for consistency with line 807.

3. **Uploaded test file committed** (`uploads/global/cc6876bdeb14_test.xlsx`): A test file was committed to the repo. The `uploads/` directory is in `.gitignore` but this file predates the gitignore entry.

### Nitpicks

1. **`ChatSessionSelector.tsx:52`**: `session.file_sources?.length > 0` — optional chaining with `>` comparison will return `false` if `file_sources` is undefined (comparing `undefined > 0`), but wrapping in extra parentheses `(session.file_sources?.length > 0)` adds unnecessary noise.

2. **`DataSourcesPanel.tsx:262`**: `setSessionFileIds((response as any).active_file_source_ids || [])` — the `as any` cast bypasses type safety. Define a proper response type.

3. **Typo in commit message**: "compabality wiget" should be "compatibility widget" (commit 7a9b2da).

---

## Summary

This is a well-architected feature addition that integrates cleanly with the existing multi-database system. The security posture is strong with path validation, content verification, and input sanitization at multiple layers. The DuckDB session management is thread-safe with proper cleanup semantics.

**Key strengths:** Clean separation of concerns, consistent security patterns, backward-compatible API changes, comprehensive unit tests for core validation logic.

**Key areas for improvement:** Add API endpoint tests and Excel integration tests, fix the `is_global == True` SQLAlchemy warning, remove the committed test file, and consider streaming hash computation for large file uploads.

| Category | Rating |
|----------|--------|
| Architecture | Strong |
| Security | Strong (minor concerns noted) |
| Code Quality | Good |
| Test Coverage | Moderate (unit good, integration gaps) |
| Frontend | Good (minor inconsistencies) |
All 36 tests pass. Here's a summary of the fixes applied:                                                                                           
  ┌─────┬───────────────────────────────┬────────────────────────────────────────────────────────────────────────┬───────────────────────────────────┐
  │  #  │             Issue             │                                  Fix                                   │              File(s)              │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 1   │ is_global == True SQLAlchemy  │ Changed to .is_(True)                                                  │ file_source_handler.py:821        │
  │     │ warning                       │                                                                        │                                   │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 2   │ save_file loads entire file   │ Streaming chunked read + hash with temp file rename                    │ file_source_handler.py:332-380    │
  │     │ into memory                   │                                                                        │                                   │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 3   │ _get_lock() race condition    │ Added threading.Lock guard for double-checked lock creation            │ file_source_session.py:42-56      │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 4   │ Error messages leak server    │ Generic messages: "outside the allowed upload directory", "does not    │ file_utils.py:43,47               │
  │     │ paths                         │ exist or has been removed"                                             │                                   │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 5   │ Frontend as any cast          │ Added proper return type to getSessionFiles() in api.ts                │ api.ts:558,                       │
  │     │                               │                                                                        │ DataSourcesPanel.tsx:83           │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 6   │ Frontend raw fetch() calls    │ Added createConnection, updateConnection, deleteConnection to          │ api.ts:291-306,                   │
  │     │                               │ connectionsAPI and replaced all raw fetch()                            │ DataSourcesPanel.tsx              │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 7   │ Test mock incompatible with   │ Updated dedup test mock to support size parameter                      │ test_file_sources.py:448-470      │
  │     │ chunked reads                 │                                                                        │                                   │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────┼───────────────────────────────────┤
  │ 8   │ Test assertions for new error │ Updated match= patterns                                                │ test_file_sources.py:495,501      │
  │     │  messages                     │                                                                        │                                   │
  └─────┴───────────────────────────────┴────────────────────────────────────────────────────────────────────────┴───────────────────────────────────┘
  Skipped: committed test file (uploads/global/cc6876bdeb14_test.xlsx) per your request.
