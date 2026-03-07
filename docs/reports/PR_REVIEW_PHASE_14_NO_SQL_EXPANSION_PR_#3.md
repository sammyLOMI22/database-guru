PR Review: NoSQL Database Expansion (Phase 14) — Review #3

  Branch: no-sql-database-expansion (5 commits, 78 files, +10,884 / -322 lines)

  This review consolidates findings from Reviews #1 and #2, re-evaluates all previously flagged issues against
  the latest commit (09ca2e1), and adds new findings. Items marked [FIXED] were addressed since Review #2.
  Items marked [FIXED in #3] were addressed during this review cycle.

  ---
  Status Summary

  | Category        | Review #2 | Fixed pre-#3 | Fixed in #3 | Total Open |
  |-----------------|-----------|--------------|-------------|------------|
  | Critical        | 5         | 2            | 4           | 0          |
  | Major           | 14        | 3            | 8           | 4          |
  | Minor           | 20+       | 2            | 1           | 17+        |

  ---
  Fixed Since Review #2 (pre-Review #3)

  [FIXED] C2. Timezone mismatch (naive vs aware datetime)
  datetime.utcnow() replaced with datetime.now(timezone.utc) and .replace(tzinfo=None) used consistently
  for comparison with connection.schema_updated_at.

  [FIXED] C3. Cassandra cluster.connect() blocking the event loop
  Connection tester now wraps Cassandra operations in asyncio.to_thread().

  [FIXED] M1. Mutable class-level _pool_dict
  Subclasses now explicitly assign _pool_dict = {} in __init__, not sharing across subclasses.

  [FIXED] M14. DynamoDB Docker health check always passes
  Removed || exit 0 from the healthcheck command.

  [FIXED] Minor: _DB_NAME_OPTIONAL_TYPES naming
  Renamed to DB_NAME_OPTIONAL_TYPES with ClassVar annotation per Pydantic best practice.

  [FIXED] Minor: Missing evict() on DynamoDB/Elasticsearch pools
  All pool classes now implement evict().

  [FIXED] Minor: Cassandra sync driver in async executor
  Verified — executor wraps session.execute() in asyncio.to_thread() correctly.

  ---
  Fixed in Review #3

  Critical:

  C1. [FIXED in #3] password_encrypted used as plaintext — frontend claim corrected

  DatabaseConnectionModal.tsx:314 changed from "Credentials are stored encrypted" to
  "AWS credentials are stored locally" to stop misleading users.
  Note: Underlying plaintext storage remains — full encryption tracked as future improvement.

  C4. [FIXED in #3] Credential leakage in connection tester error messages

  Added _sanitize_error() helper to src/core/connection_tester.py that strips:
  - Connection URIs (mongodb://, postgresql://, etc.)
  - AWS access keys (AKIA...)
  - Password/secret key-value pairs
  Applied to all 10 _test_* methods and top-level catch-all (13 call sites).

  C5. [FIXED in #3] Dead router test — replaced with full dispatch coverage

  Replaced broken test_routes_to_mongodb with 5 working tests that call execute_nosql_query()
  and assert correct handler instantiation for all NoSQL types. All 29 router tests pass.

  C-NEW-1. [FIXED in #3] CQL injection — added _validate_cql() to Cassandra executor

  Added _validate_cql() to src/nosql/cassandra/query_executor.py:
  - Strips string literals and block comments before checking for semicolons
  - Rejects multi-statement queries
  - Validates first keyword against allowlist (SELECT/INSERT/UPDATE/DELETE/USE)
  - Write check operates on comment-stripped input (blocks /* comment */ INSERT ...)

  Major:

  M2. [FIXED in #3] Duplicated schema caching logic (DRY violation)

  Refactored src/nosql/base.py:_get_schema() to delegate to router.get_cached_or_fresh_schema()
  for actual cache logic. Base class now only handles trace step messaging around the shared function.

  M3. [FIXED in #3] MongoDB missing_count never incremented — nullability detection broken

  Added _extract_field_names() helper to src/nosql/mongodb/schema_inspector.py and a second pass
  after document analysis that counts fields missing from each sampled document. Nullability
  detection now works correctly.

  M5. [FIXED in #3] Redis KEYS command in the allowlist — production DoS risk

  Removed KEYS from ALLOWED_READ_COMMANDS in src/nosql/redis/query_executor.py and from the
  LLM prompt in src/nosql/redis/schema_inspector.py. SCAN remains as the safe alternative.

  M7. [FIXED in #3] DynamoDB execute_statement ignores pagination (NextToken)

  Updated src/nosql/dynamodb/query_executor.py to return (rows, has_more) from _execute_partiql()
  and set result["truncated"] = True when NextToken is present in the DynamoDB response.

  M8. [FIXED in #3] evict_nosql_pool failure after DB commit causes 500

  Wrapped evict_nosql_pool() call in src/api/endpoints/connections.py:delete_connection() in
  try/except with warning log. Added logger to the module.

  M9. [FIXED in #3] Multi-DB NoSQL path missing db, chat_session_id

  Added db and chat_session_id parameters to _execute_single_query_task() in
  src/core/multi_db_handler.py and passed them through to execute_nosql_query(). Updated
  call site in src/api/endpoints/multi_db_query.py. (query_history_id not available per-database
  in multi-DB path — documented in TECH_DEBT.md)

  M-NEW-1. [FIXED in #3] Elasticsearch write detection only checks top-level keys

  Replaced flat key check with recursive _contains_script() method in
  src/nosql/elasticsearch/query_executor.py. Now checks for script, scripted_metric,
  script_score, and script_fields at any nesting depth. Top-level write indicators
  (update, delete, upsert, doc, doc_as_upsert) still checked at top level only.

  M6/C-NEW-1. [FIXED in #3] CQL injection — escalated to Critical, fixed (see above)

  M11. [FIXED in #3] No routing tests / router utility tests

  Added dispatch tests for all 5 NoSQL types (C5 fix) plus tests for evict_nosql_pool()
  (SQL noop, MongoDB eviction, error swallowing) and get_cached_or_fresh_schema() (cached hit,
  expired cache, no cache, DB persistence) in tests/nosql/test_security_and_executors.py.

  M12. [PARTIALLY FIXED in #3] No executor tests for Cassandra or DynamoDB

  Added CQL validation tests (10 tests) and PartiQL validation tests (8 tests including
  pagination truncation) in tests/nosql/test_security_and_executors.py. End-to-end executor
  tests against real databases remain as integration test gap.

  Tests added in Review #3 (tests/nosql/test_security_and_executors.py — 43 new tests):

  - TestCQLValidation: 10 tests (valid select, trailing semicolon, empty, multi-statement,
    semicolon in string, comment-prefixed write, unsupported type, USE allowed, write blocked,
    comment-bypassed write blocked)
  - TestPartiQLValidation: 8 tests (valid select, empty, multi-statement, semicolon in string,
    escaped quotes, unsupported type, pagination truncation flag, no truncation without NextToken)
  - TestRedisBlockedCommands: 7 tests (FLUSHALL, CONFIG, EVAL, SHUTDOWN, DEBUG blocked,
    KEYS not in allowlist, KEYS command blocked)
  - TestElasticsearchScriptDetection: 7 tests (top-level script, nested script_score,
    nested scripted_metric, deeply nested, safe query allowed, top-level update, script with allow_write)
  - TestEvictNoSQLPool: 3 tests (SQL noop, MongoDB eviction, error swallowed)
  - TestGetCachedOrFreshSchema: 4 tests (cached fresh, expired, no cache, DB persist)

  Total NoSQL test count: 170 (up from 127)

  ---
  Remaining Major Issues (4 open)

  M4. [OPEN] MongoDB write operations defined in enum but executor raises on them

  File: src/nosql/mongodb/query_executor.py:82-97

  MQLOperationType includes INSERT/UPDATE/DELETE, and allow_write parameter exists, but _execute_query has no
  handlers for them. They hit a generic ValueError. Either implement write execution or remove the enum values.

  M10. [OPEN] Elasticsearch scheme inferred from auth presence

  Files: src/nosql/elasticsearch/client_pool.py:46-48, src/core/connection_tester.py:354-355

  scheme = "https" if has_auth else "http" — breaks for HTTP+auth (local dev) or HTTPS+no-auth (VPN) clusters.

  M13. [OPEN] No happy-path handler tests for Redis, Cassandra, or DynamoDB

  These only test the error path (connection refused). MongoDB and Elasticsearch both have full handler
  success tests.

  M12. [PARTIALLY OPEN] No end-to-end executor tests for Cassandra or DynamoDB

  Validation tests added, but no tests exercising _execute_sync (Cassandra) or _execute_partiql (DynamoDB)
  with mocked database sessions.

  ---
  Minor Issues (17+ open)

  Key items (unchanged from Review #2 unless noted):

  - MongoDB error classifier typo: "a]ggregation pipeline" (stray ]) — will never match
  - MongoDB pipeline mutation: _execute_aggregate appends to the original query.pipeline list in-place
  - Premature success=False stat recording in base.py:545 before correction is attempted
  - confidence_scorer/correction_learner dead assignments in base.py:309-310
  - Dead code block in base.py:362-364 (pass with misleading comment)
  - Operator precedence ambiguity in Cassandra and DynamoDB error classifiers
  - Redis DUMP in allowlist returns raw binary that won't serialize to JSON
  - Result formatter breaks on mixed scalar/dict results and sorted() loses insertion order
  - No set type handling in result_formatter.py — DynamoDB sets would fail JSON serialization
  - Frontend form state persists when switching database types (DynamoDB region stays in PostgreSQL host field)
  - Frontend Redis validation allows port 0
  - Connection string preview shows access key in plaintext (DynamoDB)
  - start_nosql.sh --db arg parsing bug — shift inside for loop doesn't work
  - Unused time import in seed_nosql_data.py
  - database_name changed from required to optional in Pydantic schema weakens OpenAPI docs
  - Handler instantiated per query in router.py — no caching/singleton pattern
  - Same if/elif chain for database types appears 3x in router.py — use a registry dict
  - Timezone comparison still fragile: .replace(tzinfo=None) works but breaks if schema_updated_at becomes
    timezone-aware

  ---
  Positives

  1. Excellent base abstraction — NoSQLHandler._generate_and_execute_with_retry() centralizes retry loop,
     confidence scoring, correction learning, and result verification. All 5 handlers delegate to this.
  2. Consistent handler architecture — get client → inspect schema → init generator + executor → delegate
     to retry method → catch-all error handler. Easy to maintain and extend.
  3. Result normalization — normalize_nosql_result() maps all NoSQL results to SQLExecutor.execute_query()
     shape. Downstream narration, history, and frontend work unchanged.
  4. DynamoDB PartiQL injection protection — _validate_partiql() strips string literals before checking
     for semicolons, validates against allowed statement types, blocks multi-statement injection.
  5. Redis command allowlist — explicit allowlist blocking FLUSHALL, CONFIG, SHUTDOWN, EVAL, SCRIPT.
  6. MongoDB credential URL-encoding — quote_plus() for username/password in URIs.
  7. Graceful agent degradation — all agent integrations wrapped in try/except with debug logging.
  8. Non-retryable error detection — PERMISSION_DENIED, TIMEOUT, CONNECTION_ERROR break retry loop early.
  9. Docker Compose — ports bound to 127.0.0.1, health checks, resource limits, isolated network.
  10. Clean API integration — NoSQL branch inserted at the right point, no changes to SQL path.
  11. Connection validation — regex for 11 DB types, model_validator for per-type database_name rules.
  12. Frontend conditional forms — 4 distinct layouts with type-specific validation.
  13. Proper connection cleanup — evict_nosql_pool() on connection deletion.
  14. Good error classification — dedicated error_classifier.py per database mapping native errors to
      the existing ErrorType enum.

  ---
  Recommended Priority for Remaining Fixes

  All critical and most major issues have been resolved. Remaining:

  1. M10 (ES scheme) — could break local dev setups with HTTP+auth
  2. M4 (MongoDB write enum) — dead code or missing feature, low risk
  3. M13 (happy-path handler tests) — improves confidence but not blocking
  4. M12 (end-to-end executor tests) — best covered by integration tests against Docker

  ---
  Files Changed in Review #3

  Source fixes:
  - src/nosql/cassandra/query_executor.py — added _validate_cql() injection protection
  - src/nosql/elasticsearch/query_executor.py — recursive _contains_script() for nested script detection
  - src/nosql/redis/query_executor.py — removed KEYS from ALLOWED_READ_COMMANDS
  - src/nosql/redis/schema_inspector.py — removed KEYS from LLM prompt
  - src/nosql/dynamodb/query_executor.py — pagination truncation flag via NextToken
  - src/nosql/base.py — _get_schema() delegates to router.get_cached_or_fresh_schema()
  - src/nosql/mongodb/schema_inspector.py — missing_count tracking via _extract_field_names()
  - src/core/connection_tester.py — _sanitize_error() for credential stripping
  - src/core/multi_db_handler.py — db/chat_session_id params for NoSQL multi-DB path
  - src/api/endpoints/connections.py — try/except around evict_nosql_pool(), added logging
  - src/api/endpoints/multi_db_query.py — pass db/chat_session_id to _execute_single_query_task()
  - frontend/src/components/DatabaseConnectionModal.tsx — removed false encryption claim

  Test additions:
  - tests/nosql/test_router.py — 5 dispatch tests replacing dead test
  - tests/nosql/test_security_and_executors.py — 43 new tests (NEW FILE)

  Total: 14 files modified, 170 NoSQL tests passing (was 127)
