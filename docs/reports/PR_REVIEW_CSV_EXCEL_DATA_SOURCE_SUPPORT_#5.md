PR Review: CSV/Excel Data Source Support (csv-excel-data-source-support)

  13 commits | ~40 files changed | ~5,700 lines added

  This is a substantial feature branch (Phase 13) adding CSV/Excel file upload, DuckDB-based querying, soft-delete for connections/files, and full
  frontend integration.

  ---
  Verdict: Do NOT merge yet. Fix the blockers below first.

  The architecture is solid and the feature is well-scoped, but there are a handful of issues that should be resolved before merge. I'll categorize
  them as Blockers (must fix), Should Fix (strongly recommended), and Nice to Have (post-merge is fine).

  ---
  BLOCKERS (Must Fix Before Merge)

  1. Committed test file in uploads/

  A binary file uploads/global/cc6876bdeb14_test.xlsx is checked into git. The .gitignore has uploads/ but this was committed before that rule was
  added. Remove it from tracking.

  git rm --cached uploads/global/cc6876bdeb14_test.xlsx

  2. Path traversal via session_id in file storage

  file_source_handler.py:365 -- The session_id from Form(None) in the upload endpoint is used directly in mkdir(parents=True):
  storage_dir = self.upload_dir / 'sessions' / session_id
  storage_dir.mkdir(parents=True, exist_ok=True)
  A crafted session_id like ../../etc/something creates directories outside the upload area. The session_id must be validated as a UUID format before
  use in paths. The chat_session_id field on the upload form is never validated against actual sessions either (files.py:105).

  3. No read-only enforcement on DuckDB queries

  file_source_session.py:279 -- _execute_sync runs raw LLM-generated SQL without any restriction. DuckDB supports COPY TO (file writes), DROP TABLE,
  and ATTACH (external databases). At minimum, reject DDL/DML keywords before execution, or set DuckDB to read-only mode.

  4. _get_session_file_sources commits during read operations

  chat.py:898-901 -- This helper is called from GET endpoints (list_chat_sessions, get_chat_session) but performs a db.commit() to clean up stale file
   IDs. This causes:
  - Side effects on read operations (surprising behavior)
  - Potential race conditions with concurrent reads
  - Conflicts with outer transactions

  Move the stale-ID cleanup to a separate explicit write operation rather than hiding it in a GET path.

  5. delete_file loads ALL chat sessions into memory

  files.py:230-236 -- Performs select(ChatSession) with no filter, iterating every session in Python. Replace with a targeted SQL update or at least
  filter sessions that reference the file ID.

  ---
  SHOULD FIX (Pre-merge strongly recommended)

  6. setInterval memory leak in FileUploadModal.tsx

  Lines 93-116 -- The progressInterval created during upload is only cleared in the success path. If uploadFile throws, the interval runs forever.
  Move clearInterval(progressInterval) to a finally block.

  7. Duplicate addFileToSession API calls

  The upload endpoint already receives chat_session_id and associates the file with the session server-side. Then
  DataSourcesPanel.handleFileUploadSuccess calls onFileSelect which triggers filesAPI.addFileToSession again in EnhancedChatInterface. This
  double-adds the file.

  8. Connection validation doesn't filter soft-deleted connections

  chat.py:104-116 -- When creating/updating a chat session, connection IDs are validated but soft-deleted connections (is_deleted=True) pass
  validation. A user can associate a deleted connection with a session.

  9. Unused python-magic dependency

  requirements.txt -- python-magic==0.4.27 is listed but never imported. Content validation uses manual magic byte checking. Remove it.

  10. Dead frontend props

  DataSourcesPanel.tsx -- selectedFileIds (declared but never destructured) and onDataSourcesChange (destructured but never called) are dead code
  suggesting incomplete wiring.

  11. Double-commit in delete pipeline

  file_source_handler.py:700 -- cleanup_file calls db.commit() internally, and then delete_file in files.py:235 commits again for session cleanup. If
  the second commit fails, the file is soft-deleted but session references aren't cleaned. Use a single transaction.

  12. get_excel_sheets endpoint has no file size check

  file_source_handler.py:537-539 -- content = await file.read() loads the entire file into memory without validation. The /upload endpoint validates
  size, but /excel-sheets doesn't, enabling OOM via large uploads.

  ---
  NICE TO HAVE (Can address post-merge)

  13. N+1 queries in list_chat_sessions

  3 extra DB queries per session (connections, files, message count). With 50 sessions, that's 150+ queries. Could batch these.

  14. CSV parsed 3x during schema inference

  file_source_handler.py:473-518 -- read_csv_auto() appears in three separate queries (LIMIT 0, COUNT(*), LIMIT 5). For 100MB files, this reads the
  file three times.

  15. console.log('DEBUG: ...') left in production

  EnhancedChatInterface.tsx:170-172 -- Three debug statements should be removed.

  16. DuckDB memory_limit setting injection

  file_source_session.py:87 -- DUCKDB_FILE_MEMORY_LIMIT is a str interpolated into SQL. Should validate format (e.g., \d+[KMGT]B).

  17. File deduplication collision

  file_source_handler.py:398 -- Two uploads with same content hash + sanitized filename silently overwrite via os.replace. If one is later deleted,
  the other's physical file disappears.

  18. Missing test coverage

  The test suite covers utilities well (validation, sanitization, schema inference) but has zero coverage for:
  - process_upload() (the main orchestration method)
  - execute_query() / ensure_table_loaded() (the query execution path)
  - All API endpoints in files.py
  - excel_to_temp_csv()
  - list_connections soft-delete filtering
  - delete_file endpoint pipeline

  19. Frontend accessibility

  FileUploadModal lacks role="dialog", aria-modal, focus trap, and Escape key handling.

  ---
  What's GOOD About This PR

  - Clean architecture: The FileSourceHandler / FileSourceDuckDBSession / file_utils separation is well-thought-out
  - Security awareness: Path traversal validation, magic byte checking, filename sanitization, SQL injection defense for sheet names -- all present
  - Soft-delete design: Preserving references for chat history is the right call
  - Refactoring wins: _build_connection_infos() extraction, func.count() for message counts, datetime.now(timezone.utc) migration
  - DuckDB integration: The singleton pattern with async lock, cursor-based thread safety, and lazy loading is well-designed
  - Error recovery: process_upload cleans up partial files on failure, temp files use try/finally patterns
  - Background cleanup task: Proper CancelledError handling and backoff on persistent errors

  ---
  Recommended Path Forward

  1. Fix the 5 blockers (30-60 min of work)
  2. Address the "should fix" items (another 30-60 min)
  3. Merge
  4. Address "nice to have" items in follow-up PRs (especially test coverage)

  The feature is ~90% ready. The core design is solid, but the security and data-integrity issues in the blockers category need resolution before this
   hits main.
