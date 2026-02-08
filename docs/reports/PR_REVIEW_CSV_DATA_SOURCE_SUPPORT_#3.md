PR Review: CSV/Excel Data Source Support (Phase 13)                                                                                                                  
                                                                                                                                                                     
  Summary

  This PR adds the ability to upload CSV and Excel files as queryable data sources alongside traditional database connections. Files are stored on disk,
  schema-inferred via DuckDB, and queried in parallel with database connections through the existing multi-DB query pipeline. The feature spans backend (new endpoints,
   models, DuckDB session management), frontend (upload UI, preview panel, session integration), and includes a migration and test suite.

  ---
  Overall Assessment: Solid feature implementation with some issues to address

  The architecture is well thought out -- using DuckDB as the query engine for file sources, lazy-loading tables, and integrating into the existing multi-DB parallel
  execution pipeline. The security posture is good with path traversal validation, filename sanitization, file content validation, and SQL injection protection for
  sheet names.

  ---
  Critical Issues

  1. SQL Injection via file path interpolation in DuckDB queries

  Files: src/core/file_source_handler.py, src/core/file_source_session.py

  File paths are interpolated into SQL strings using f-strings:
  read_query = f"SELECT * FROM read_csv_auto('{validated_path}', header=true)"
  and:
  session.execute(f"""
      CREATE OR REPLACE TABLE "{table_name}" AS
      SELECT * FROM read_csv_auto('{validated_path}', header=true, all_varchar=false)
  """)

  While _validate_file_path confirms the path is within the upload directory, a filename containing a single quote (e.g., it's_data.csv) would break the SQL or enable
  injection. The _sanitize_filename method doesn't strip single quotes. Consider escaping single quotes in the path (validated_path.replace("'", "''")) or using
  DuckDB's parameterized query support.

  2. asyncio.Lock shared across event loops

  File: src/core/file_source_session.py

  The uncommitted changes fix the class-level asyncio.Lock() instantiation (good), but the lazy _get_lock() approach still has a subtle issue: if _lock is None and two
   coroutines call _get_lock() concurrently before the lock is set, two different locks could be created. This is a narrow race window but worth protecting against.
  Consider initializing the lock in an @app.on_event("startup") handler.

  3. DuckDB connection is not thread-safe

  File: src/core/file_source_session.py

  The singleton DuckDB connection is used from run_in_executor (which runs in a thread pool), but DuckDB connections are not thread-safe. Multiple concurrent queries
  via _execute_sync could corrupt state. Consider either:
  - Creating a new DuckDB connection per query (cheap for in-memory)
  - Using DuckDB's .cursor() method per thread
  - Serializing all DuckDB access through a single-threaded executor

  ---
  High-Priority Issues

  4. Settings() instantiated per-request in several places

  Files: src/api/endpoints/files.py (partially fixed in uncommitted), src/core/file_source_handler.py, src/core/multi_db_handler.py

  The committed code creates Settings() on every request (handler = FileSourceHandler(settings) where settings = Settings()). The uncommitted changes partially fix
  this by using Depends(get_settings) in some endpoints but not all. The refresh_file_schema and get_excel_sheets endpoints still create Settings() inline.

  5. Duplicate utility functions

  Files: src/core/file_utils.py, src/core/file_source_handler.py, src/core/file_source_session.py

  The uncommitted changes create file_utils.py with shared validate_file_path and sanitize_sheet_name, but the committed code in file_source_handler.py and
  file_source_session.py each has its own copy of _validate_file_path and _sanitize_sheet_name. The uncommitted changes appear to be cleaning this up, but the
  transition is incomplete -- ensure all copies are removed and only file_utils.py is used.

  6. _loaded_tables and _table_metadata are mutable class-level variables

  File: src/core/file_source_session.py:40-42

  _loaded_tables: Set[str] = set()
  _table_metadata: Dict[str, Dict[str, Any]] = {}

  These are shared across all instances (intentionally, for the singleton pattern), but they're mutable class attributes initialized at class definition time. This
  works in CPython due to the GIL, but is fragile. Combined with the thread-pool executor usage, concurrent modifications could be problematic.

  7. Entire file read into memory for validation

  File: src/core/file_source_handler.py:466-469

  await file.seek(0)
  content = await file.read()
  file_size = len(content)

  For a 100MB file (the configured max), this reads the entire file into memory just to check its size. This happens again in save_file. Consider streaming the file or
   using file.file.seek(0, 2) to get size without reading content.

  ---
  Medium-Priority Issues

  8. datetime.utcnow() is deprecated

  Files: src/core/file_source_handler.py, src/database/models.py

  datetime.utcnow() is deprecated since Python 3.12. The uncommitted changes import timezone but don't fully migrate. Use datetime.now(timezone.utc) instead.

  9. No authorization/ownership checks on file operations

  File: src/api/endpoints/files.py

  Any user can delete, preview, or modify any file source regardless of user_id. The user_id field exists on the model but is never checked in the endpoints. For
  example, delete_file doesn't verify the requesting user owns the file.

  10. No pagination on list_files endpoint

  File: src/api/endpoints/files.py:131-155

  The list endpoint returns all files without limit/offset. With many uploaded files this could return large payloads.

  11. list_file_sources filter logic has a subtle issue

  File: src/core/file_source_handler.py (the list_file_sources function)

  if session_id:
      if include_global:
          filters.append(or_(
              FileSource.chat_session_id == session_id,
              FileSource.is_global == True,
          ))
      else:
          filters.append(FileSource.chat_session_id == session_id)
  elif include_global:
      filters.append(FileSource.is_global == True)

  When session_id is None and include_global is True (the default), only global files are returned. But when neither session_id nor include_global is set, no ownership
   filter is applied, returning all active files. This may unintentionally expose files from other sessions.

  12. connection_id field overloaded for file sources in DatabaseQueryResult

  File: src/api/endpoints/multi_db_query.py:998

  connection_id=file_source.id if file_source else 0,

  File source IDs are passed as connection_id in DatabaseQueryResult. This conflates two different ID spaces and could confuse consumers. Consider adding a
  file_source_id field or a source_type discriminator.

  13. Excel sheet endpoint reads entire file into memory twice

  File: src/api/endpoints/files.py (get_excel_sheets endpoint)

  The file content is read by FastAPI, then read again in get_excel_sheets, then read a third time in _get_sheets_sync. For large Excel files this is wasteful.

  ---
  Low-Priority / Nits

  14. asyncio.get_event_loop() is deprecated

  Files: src/core/file_source_handler.py, src/core/file_source_session.py

  Use asyncio.get_running_loop() instead. get_event_loop() is deprecated in Python 3.10+ for cases where a loop may not be running.

  15. Unused import in committed code

  File: src/core/file_source_handler.py

  The committed code imports re in file_source_session.py but the uncommitted changes import from file_utils instead. Clean up after the refactor.

  16. Frontend type assertion (response as any)

  File: frontend/src/components/DataSourcesPanel.tsx:226

  setSessionFileIds((response as any).active_file_source_ids || []);

  This casts away type safety. Define the response type properly.

  17. Test file test_file_sources.py has no API endpoint tests

  The test suite covers handler, validation, and DuckDB session unit tests but has no HTTP-level tests for the /api/files/* endpoints.

  18. node_modules cleanup

  The diff includes removing frontend/node_modules from git tracking (good), but the diff itself is massive because of it. Ensure .gitignore is correct before merging.

  ---
  What's Working Well

  - Security: Path traversal protection, filename sanitization, file content magic byte validation, sheet name SQL injection prevention -- all solid patterns
  - Architecture: Clean integration into the existing multi-DB pipeline without disrupting it. The file_sources parallel to databases in the combined schema is
  well-designed
  - DuckDB lazy loading: Tables loaded on first access and cached is a good memory optimization
  - Migration: Clean up/down migration with proper foreign keys and indexes
  - Frontend: File upload UI with drag-and-drop, preview panel, session integration, and proper state management
  - Tests: Good coverage of validation, sanitization, schema inference, and edge cases
  - Error handling: Proper cleanup of partial files on upload failure, graceful handling of DuckDB errors

  ---
  Uncommitted Changes Assessment

  The working tree has sensible improvements over the committed code:
  - Extracting shared utilities into file_utils.py (deduplication)
  - Using Depends(get_settings) instead of Settings() per request
  - Fixing the asyncio.Lock() class-level initialization
  - DuckDB WITH query support in the executor
  - Refactoring _extract_json_object to use the shared llm_utils version

  These should be committed as they address real issues. The file_utils.py extraction needs to fully remove the duplicate functions from the original files.

  PLAN:
  Yes -- I'd recommend fixing the critical and high-priority ones before merging. Here's my take on what to prioritize:                               
                                                                                                                                        
  Must fix (could cause bugs or security issues):                                                                                                     
  1. SQL injection via file path single quotes -- a filename like it's_data.csv would break queries
  2. DuckDB thread safety -- concurrent queries via run_in_executor will hit a single non-thread-safe connection                                      
  3. Duplicate utility functions -- the uncommitted file_utils.py refactor is half-done; needs to be completed                                      
  4. asyncio.get_event_loop() -> get_running_loop() -- the deprecated version can behave unexpectedly

  Should fix (code quality, easy wins):
  5. Settings() per-request -- the uncommitted changes partially fix this; finish it
  6. datetime.utcnow() deprecation -- straightforward replacement
  7. Double file read in validation -- reads entire 100MB file into memory twice

  Can defer (won't cause issues for merge):
  - Auth/ownership checks, pagination, connection_id overloading, frontend as any cast, API endpoint tests -- these are real but can be follow-up work

  Want me to go ahead and fix items 1-7?
