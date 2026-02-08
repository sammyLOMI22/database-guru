PR Review: CSV & Excel Data Source Support (Phase 13)
                                                                                                                                                      
  Overview                                                                         

  This PR adds CSV/Excel file upload support, allowing files to be queried as SQL tables via DuckDB alongside traditional database connections. It
  also introduces soft-delete for database connections and file sources. ~5,400 lines added across 35 files (excluding node_modules/docs).

  ---
  Positives

  1. Clean architecture - The separation into FileSourceHandler (upload/validation/schema), FileSourceDuckDBSession (query execution singleton), and
  file_utils.py (shared security) is well-structured.
  2. Security is well-considered - Path traversal prevention via validate_file_path(), sheet name sanitization, magic byte validation, and file
  content checks are all solid.
  3. Good refactoring in chat.py - The repeated connection-lookup pattern (4x) was correctly extracted into _build_connection_infos() and
  _get_session_file_sources(). Message counting was upgraded from len(scalars().all()) to select(func.count()).
  4. Soft-delete design - Preserving records so chat sessions can show "removed" instead of silently losing references is a good UX decision.
  Idempotent delete (return 204 if already deleted) is correct.
  5. Thorough test coverage - 647 lines of tests covering validation, sanitization, schema inference, preview, DuckDB session, cleanup, path
  traversal, and sheet name injection.
  6. Background cleanup - Hourly expired file cleanup task with proper cancellation on shutdown.

  ---
  Issues

  High Priority

  1. SQL injection via limit parameter in _get_preview_sync
  src/core/file_source_handler.py:483 — f"{read_query} LIMIT {limit}". While limit comes from a validated FastAPI Query(20, ge=1, le=100) at the API
  layer, _get_preview_sync is a public method on a public class that can be called with any int. Use a parameterized query or explicitly cast/validate
   here defensively.

  2. datetime.utcnow() still used in models.py
  src/database/models.py:35,74,75,94,98,141,167,168,169,192,240,241,288,378 — The FileSource model correctly uses datetime.now(timezone.utc) in
  handler code, but the model column defaults still use datetime.utcnow (deprecated since Python 3.12). Since chat.py was already migrated to
  datetime.now(timezone.utc), models.py should follow suit for consistency. The Pylance diagnostics also flag this.

  3. upload_file endpoint leaks internal errors
  src/api/endpoints/files.py:134 — ValueError exceptions from process_upload are re-raised as 400s with str(e). If ValueError is raised from deeper in
   the stack (e.g., DuckDB, openpyxl), the message could leak internal paths or implementation details. Consider sanitizing the error message.

  4. _file_expiration_task error handling swallows all exceptions silently
  src/main.py:37-40 — On error, it logs but continues the loop. If db_manager.get_async_session() itself throws (e.g., DB is down), this will spin in
  a tight log-and-retry loop with only a 1-second gap before hitting the sleep again. Consider adding a backoff or at minimum an await
  asyncio.sleep(60) in the except block.

  5. get_session() double-check locking uses _init_lock created on-demand via hasattr
  src/core/file_source_session.py:83-84 — if not hasattr(cls, '_init_lock') is itself a race condition. Two threads could both see hasattr as False.
  Use a class-level threading.Lock() (like _lock_guard already is) instead.

  Medium Priority

  6. Unused imports flagged by Pylance
  - files.py:8 — List (use list lowercase)
  - files.py:12 — select imported but unused
  - chat.py:6 — update imported but unused

  7. FileSourceDuckDBSession._loaded_tables and _table_metadata are mutable class-level attributes
  src/core/file_source_session.py:43-45 — _loaded_tables: Set[str] = set() and _table_metadata: Dict = {} are shared across all instances/subclasses.
  This is intentional for singleton behavior, but if anyone ever subclasses this or runs tests in parallel, state will leak. Consider documenting this
   explicitly or using a more defensive pattern.

  8. _execute_single_file_query_task — file_source object in return dict
  src/core/multi_db_handler.py:696-757 — The result dict includes "file_source": file_source (a SQLAlchemy model instance). This works internally but
  is fragile — if the result dict is ever serialized (e.g., cached), this will fail. The connection field in existing DB results has the same pattern,
   so this is consistent but worth a comment.

  9. ConnectionInfo.is_deleted uses getattr(conn, 'is_deleted', False) or False
  src/api/endpoints/chat.py:879 — The getattr fallback suggests uncertainty about whether the column exists. Since the migration adds it, a bare
  conn.is_deleted or False would suffice (handles None from nullable column).

  10. excel_to_temp_csv reads entire workbook into memory
  src/core/file_source_handler.py:47-100 — For large Excel files (up to 100MB allowed), read_only=True helps but openpyxl can still use significant
  memory. The CSV streaming approach for the save path is good, but Excel conversion doesn't have a size guard beyond the upload limit. This is
  acceptable for now but worth noting for large file support.

  11. Test file has many unused imports/variables
  tests/test_file_sources.py — Multiple unused imports (io, os, datetime, get_file_source_by_id, list_file_sources) and unused local variables (pos,
  size, p, count). Clean these up.

  Low Priority / Nits

  12. list_files endpoint shadows status builtin
  src/api/endpoints/files.py:155 — Parameter status: Optional[str] = Query(None, ...) shadows the fastapi.status import and the Python builtin. Rename
   to processing_status for clarity.

  13. Binary test file committed
  uploads/global/cc6876bdeb14_test.xlsx — A test Excel file appears in the diff (git status shows it as deleted on the branch). Make sure test
  fixtures aren't committed to the uploads directory; use the test fixtures in the test code instead.

  14. No rate limiting on file upload endpoint
  The upload endpoint accepts 100MB files with no per-user rate limiting. This could be abused for disk exhaustion. Consider adding upload rate
  limiting or at least documenting the risk.

  15. node_modules cleanup
  The diffstat shows node_modules removal — good that .gitignore was updated, but the diff is huge. A git filter-branch or BFG cleanup would shrink
  repo history if this matters.

  16. Cross-source query guidance in LLM prompt is optimistic
  src/core/multi_db_handler.py:370-376 — The guidance says "Generate SEPARATE queries for databases vs files" but there's no enforcement. If the LLM
  generates a single query spanning both engines, it will fail silently. Consider adding detection/routing logic or at minimum a warning.

  ---
  Summary

  This is a solid feature implementation with good security practices, clean separation of concerns, and thorough testing. The main areas to address
  before merge are the SQL injection surface in _get_preview_sync, the deprecated datetime.utcnow() in models, and the init lock race condition in
  FileSourceDuckDBSession. The unused imports should be cleaned up as well since Pylance is already flagging them.
  All clean. Here's a summary of what was fixed:                                                                                                      
  #: 1                                                                                                                                                
  Issue: SQL injection surface in _get_preview_sync                                                                                                   
  File: file_source_handler.py
  Fix: Added limit = max(1, min(int(limit), 10000)) clamp at top of method                                                                            
  ────────────────────────────────────────                                                                                                            
  #: 2                                                                                                                                                
  Issue: Deprecated datetime.utcnow (15 occurrences)                                                                                                  
  File: models.py                                                                                                                                     
  Fix: Replaced all with lambda: datetime.now(timezone.utc), added timezone import
  ────────────────────────────────────────
  #: 3
  Issue: Internal error leakage in upload endpoint
  File: files.py + file_source_handler.py
  Fix: Introduced FileValidationError subclass; endpoint now catches only that (safe messages), all other exceptions fall through to the generic 500
    handler
  ────────────────────────────────────────
  #: 4
  Issue: Expiration task tight-loop on error
  File: main.py
  Fix: Added await asyncio.sleep(60) backoff in the except block
  ────────────────────────────────────────
  #: 5
  Issue: _init_lock race condition
  File: file_source_session.py
  Fix: Replaced hasattr-based lazy lock with the existing class-level _lock_guard
  All 94 tests pass, all imports clean, zero Pylance diagnostics on changed files.