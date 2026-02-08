---                                                                                                                                                                  
  PR Review: CSV/Excel Data Source Support (Phase 13)
                                                                                                                                                                       
  Summary                                

  This PR adds support for CSV and Excel files as queryable data sources via DuckDB. Files can be uploaded, schema-inferred, and queried alongside traditional database
   connections using natural language. It spans backend (new models, handlers, API endpoints, DuckDB session management), frontend (upload modal, data sources panel,
  preview), and database migration.

  ---
  Severity Legend

  - P0 (Critical) - Must fix before merge
  - P1 (Important) - Should fix before merge
  - P2 (Minor) - Nice to have, can follow up

  ---
  P0 - Critical Issues

  1. Test file committed to repo uploads/global/cc6876bdeb14_test.xlsx

  A binary test file is tracked in git. The uploads/ directory should be in .gitignore. This will bloat the repo for all contributors.

  2. SQL injection via file path interpolation (file_source_handler.py:405-407, file_source_session.py:174-177)

  File paths are interpolated directly into SQL strings:
  read_query = f"SELECT * FROM read_csv_auto('{validated_path}', header=true)"
  While validate_file_path ensures the path is within the upload directory, a filename containing a single quote (') would break the query or allow injection. DuckDB's
   read_csv_auto takes a string parameter - if the validated path contains ', the SQL is malformed. The _sanitize_filename method does not strip single quotes.

  Fix: Either escape single quotes in the validated path (validated_path.replace("'", "''")) or use DuckDB's parameterized query support.

  3. update_chat_session doesn't handle file_source_ids updates (chat.py:373-476)

  The ChatSessionUpdate model accepts file_source_ids, but the PATCH handler never reads or applies update_data.file_source_ids. It also omits active_file_source_ids
  and file_sources from the response. This means the frontend cannot update which files are associated with a session via the PATCH endpoint.

  ---
  P1 - Important Issues

  4. Class-level mutable state on FileSourceDuckDBSession (file_source_session.py:39-43)

  class FileSourceDuckDBSession:
      _instance: Optional[duckdb.DuckDBPyConnection] = None
      _loaded_tables: Set[str] = set()
      _lock: asyncio.Lock = asyncio.Lock()
      _table_metadata: Dict[str, Dict[str, Any]] = {}

  The asyncio.Lock() is created at class definition time, which means it's bound to whatever event loop exists then (or none). If the application creates a new event
  loop at startup (common with uvicorn), this lock will be on the wrong loop in Python 3.10+, potentially causing RuntimeError: Task attached to a different loop.
  Consider lazily creating the lock.

  5. Full file read into memory during validation (file_source_handler.py:261-263)

  content = await file.read()
  file_size = len(content)

  For a 100MB file (the configured max), this reads the entire file into memory just to check the size, then reads it again in save_file. For large files, consider
  streaming or using file.spool_max_size / chunked reads.

  6. Settings() instantiated per-request (files.py:95-96, files.py:195, files.py:273, files.py:319, files.py:360)

  Every endpoint creates a new Settings() instance:
  settings = Settings()
  handler = FileSourceHandler(settings)

  This reparses environment variables and .env on every request. Use FastAPI's dependency injection (Depends(get_settings)) to share a cached instance.

  7. Singleton DuckDB connection is not thread-safe (file_source_session.py:53-77)

  get_session() has no locking around the if cls._instance is None check. Two concurrent callers could create two connections, with one silently dropped. While
  ensure_table_loaded uses the async lock, get_session itself doesn't.

  8. No uploads/ in .gitignore

  The .gitignore update only added **/node_modules/. The uploads/ directory containing user-uploaded files is not gitignored, which is why the test xlsx file got
  committed.

  9. asyncio.get_event_loop() deprecation (file_source_handler.py:374, file_source_session.py:111, etc.)

  Multiple places use asyncio.get_event_loop() which is deprecated in Python 3.10+ when no running loop exists. Use asyncio.get_running_loop() instead, since these are
   all called from async contexts.

  ---
  P2 - Minor Issues

  10. DuckDB connection never cleaned up on app shutdown

  FileSourceDuckDBSession creates a singleton connection but there's no shutdown hook to close it. Add a FastAPI shutdown event handler calling reset_session().

  11. Message count query is inefficient (chat.py:249-252)

  msg_count_result = await db.execute(
      select(ChatMessage).where(ChatMessage.chat_session_id == session.id)
  )
  message_count = len(msg_count_result.scalars().all())

  This loads all messages into memory just to count them. Use select(func.count()).where(...) instead. This is repeated in multiple endpoints.

  12. _validate_content for CSV is too permissive (file_source_handler.py:297-303)

  return any(c.isprintable() or c in '\n\r\t,' for c in sample)

  This returns True for essentially any text file. A JSON file, Python script, or HTML file would all pass. Consider checking for comma/tab delimiters or at minimum
  that the file parses as CSV.

  13. list_file_sources uses == True comparison (file_source_handler.py:748, 758)

  query = select(FileSource).where(FileSource.is_active == True)

  Use FileSource.is_active.is_(True) for proper SQLAlchemy boolean comparison (avoids linting warnings and is more explicit).

  14. Duplicate code in _infer_schema_sync and _get_preview_sync

  Both methods in FileSourceHandler have nearly identical DuckDB connection setup, Excel conversion, and cleanup logic. This could be refactored into a shared helper.

  15. No rate limiting on file upload endpoint

  The /files/upload endpoint accepts files up to 100MB with no rate limiting beyond what the global middleware provides. Consider adding per-IP upload limits.

  16. datetime.utcnow() is deprecated (file_source_handler.py:183, model definitions)

  datetime.utcnow() is deprecated since Python 3.12. Use datetime.now(timezone.utc) instead. This is pre-existing in the codebase but is extended by this PR.

  ---
  Positive Observations

  - Security-conscious design: Path traversal prevention via validate_file_path, content validation with magic bytes, filename sanitization, and sheet name SQL
  injection prevention are all well implemented. Extracting these to file_utils.py for shared use is good.
  - Clean DRY refactoring: Moving _sanitize_sheet_name and _validate_file_path from duplicated private methods to shared file_utils.py is solid.
  - Graceful error handling: The upload flow correctly marks file sources as error status and cleans up partial files on failure.
  - Lazy table loading: The DuckDB session's lazy loading pattern avoids memory waste for unqueried files.
  - Good test coverage: Tests cover validation, sanitization, path traversal, schema inference, and content validation.
  - Well-structured migration: The Alembic migration is clean with proper upgrade/downgrade, and the downgrade warning about physical files is helpful.
  - Cross-source query integration: The integration into the existing multi-db query pipeline is clean, with file sources participating as first-class data sources in
  schema building and parallel execution.
