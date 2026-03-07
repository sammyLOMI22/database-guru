PR Review: NoSQL Database Expansion (Phase 14) — Review #3

  Branch: no-sql-database-expansion (5 commits, 78 files, +10,884 / -322 lines)

  This review consolidates findings from Reviews #1 and #2, re-evaluates all previously flagged issues against
  the latest commit (09ca2e1), and adds new findings. Items marked [FIXED] were addressed since Review #2.
  Items marked [OPEN] remain unresolved.

  ---
  Status Summary

  | Category        | Review #2 | Fixed | Still Open | New in #3 | Fixed in #3 | Total Open |
  |-----------------|-----------|-------|------------|-----------|-------------|------------|
  | Critical        | 5         | 2     | 3          | 1         | 4           | 0          |
  | Major           | 14        | 3     | 11         | 1         | 1           | 11         |
  | Minor           | 20+       | 2     | 16+        | 2         | 0           | 18+        |

  ---
  Fixed Since Review #2

  [FIXED] C2. Timezone mismatch (naive vs aware datetime)
  datetime.utcnow() replaced with datetime.now(timezone.utc) and .replace(tzinfo=None) used consistently
  for comparison with connection.schema_updated_at. The pattern is still fragile (see M-NEW-1) but no
  longer causes TypeError.

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
  Critical Issues (0 open — all fixed in Review #3)

  C1. [FIXED in #3] password_encrypted used as plaintext — frontend claim corrected

  Files: All 5 client pools (mongodb, redis, cassandra, dynamodb, elasticsearch)

  The field connection.password_encrypted is passed directly to database clients as the password/secret.
  The field stores plaintext (connections.py:121 stores raw password). The field name is misleading and
  AWS secret keys sit unencrypted in the SQLite metadata DB.

  Fix applied: DatabaseConnectionModal.tsx:314 changed from "Credentials are stored encrypted" to
  "AWS credentials are stored locally" to stop misleading users.

  Note: The underlying plaintext storage remains. Full encryption is a separate effort (field rename +
  encrypt/decrypt layer across all client pools). Tracked as a future improvement, not a blocker.

  C4. [FIXED in #3] Credential leakage in connection tester error messages

  File: src/core/connection_tester.py

  Added _sanitize_error() helper that strips:
  - Connection URIs (mongodb://, postgresql://, etc.)
  - AWS access keys (AKIA...)
  - Password/secret key-value pairs
  Applied to all 10 _test_* methods and the top-level catch-all (13 call sites total).

  C5. [FIXED in #3] Dead router test — replaced with full dispatch coverage

  File: tests/nosql/test_router.py

  The broken test_routes_to_mongodb was replaced with 5 working tests that actually call
  execute_nosql_query() and assert the correct handler is instantiated and invoked for each
  NoSQL database type (MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch). All 29 tests pass.

  C-NEW-1. [FIXED in #3] CQL injection — added _validate_cql() to Cassandra executor

  File: src/nosql/cassandra/query_executor.py

  Added _validate_cql() method modeled after DynamoDB's _validate_partiql():
  - Strips single-quoted string literals (handling escaped quotes '')
  - Strips block comments (/* ... */)
  - Rejects multi-statement queries (semicolons outside strings/comments)
  - Validates first keyword against allowlist (SELECT/INSERT/UPDATE/DELETE/USE)
  - Write check now operates on comment-stripped input (blocks /* comment */ INSERT ...)

  ---
  Major Issues (12 open)

  M2. [OPEN] Duplicated schema caching logic (DRY violation)

  Files: src/nosql/router.py:138-169 duplicates src/nosql/base.py:234-273

  Both implement TTL-check-then-inspect-then-persist. If semantics change, both must be updated in lockstep.

  M3. [OPEN] MongoDB missing_count never incremented — nullability detection broken

  File: src/nosql/mongodb/schema_inspector.py:107

  missing_count is initialized to 0 but never updated, so the nullability check (info["missing_count"] > 0)
  is always False.

  M4. [OPEN] MongoDB write operations defined in enum but executor raises on them

  File: src/nosql/mongodb/query_executor.py:82-97

  MQLOperationType includes INSERT/UPDATE/DELETE, and allow_write parameter exists, but _execute_query has no
  handlers for them. They hit a generic ValueError. Either implement write execution or remove the enum values.

  M5. [OPEN] Redis KEYS command in the allowlist — blocks server on large keyspaces

  File: src/nosql/redis/query_executor.py:33

  KEYS scans the entire keyspace, blocking Redis. SCAN is already in the list as the safe alternative.
  The schema inspector prompt (schema_inspector.py:134) also lists KEYS as available, making it likely
  the LLM will generate it. Remove KEYS from both locations.

  M6/C-NEW-1. [FIXED in #3] CQL injection — escalated to Critical, fixed (see above)

  M7. [OPEN] DynamoDB execute_statement ignores pagination (NextToken)

  File: src/nosql/dynamodb/query_executor.py:98-107

  Large results may be silently truncated. At minimum, add a truncated flag when NextToken is present.

  M8. [OPEN] evict_nosql_pool failure after DB commit causes 500

  File: src/api/endpoints/connections.py:254-256

  Connection is deleted in DB, then pool eviction runs unwrapped. If eviction throws, user gets 500 even
  though deletion succeeded. Wrap in try/except with warning log.

  M9. [OPEN] Multi-DB NoSQL path missing db, query_history_id, chat_session_id

  File: src/core/multi_db_handler.py:~637-648

  NoSQL queries via multi-DB handler skip metadata session, query history, and session context — no learned
  corrections or tracking.

  M10. [OPEN] Elasticsearch scheme inferred from auth presence

  Files: src/nosql/elasticsearch/client_pool.py:46-48, src/core/connection_tester.py:354-355

  scheme = "https" if has_auth else "http" — breaks for HTTP+auth (local dev) or HTTPS+no-auth (VPN) clusters.

  M11. [PARTIALLY FIXED in #3] No routing tests for Redis, Cassandra, DynamoDB, or Elasticsearch

  File: tests/nosql/test_router.py

  Dispatch tests added for all 5 NoSQL types (see C5 fix). Still no tests for get_cached_or_fresh_schema()
  or evict_nosql_pool().

  M12. [OPEN] No executor tests for Cassandra or DynamoDB

  Missing coverage for CQL execution/normalization and PartiQL execution through boto3.

  M13. [OPEN] No happy-path handler tests for Redis, Cassandra, or DynamoDB

  These only test the error path (connection refused). MongoDB and Elasticsearch both have full handler
  success tests.

  M-NEW-1. Elasticsearch write detection only checks top-level keys

  File: src/nosql/elasticsearch/query_executor.py:28-41

  _WRITE_INDICATORS = {"script", "update", "delete", ...} only checks top-level keys of the query DSL dict.
  Elasticsearch scripting can be deeply nested (e.g., {"query": {"script_score": {"script": {"source": "..."}}}}
  or {"aggs": {"scripted_metric": {...}}}). An LLM-generated response could embed scripts at deeper levels and
  bypass the check.

  Fix: Recursively check for script keys in the entire query DSL dict.

  ---
  Minor Issues (18+ open)

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

  New minor items:
  - Timezone comparison still fragile: .replace(tzinfo=None) works but breaks if schema_updated_at becomes
    timezone-aware. Consider storing UTC-aware timestamps consistently.
  - No test for DynamoDB _validate_partiql() injection protection (semicolons, unsupported statements,
    semicolons inside string literals). This validation code is untested.

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

  All 4 critical issues have been resolved. Remaining priority for major/minor items:

  1. M-NEW-1 (ES write detection) — recursive check needed for nested scripts
  2. M5 (KEYS command) — production safety risk
  3. M8 (evict error handling) — user-facing 500
  4. M9 (multi-DB missing params) — silent feature degradation
  5. M3 (MongoDB nullability) — broken schema inference
  6. M12-M13 (executor/handler test coverage) — Cassandra, DynamoDB, Redis
  7. M11 (remaining router tests) — get_cached_or_fresh_schema(), evict_nosql_pool()
  8. M2 (duplicated schema caching) — DRY violation
  9. M7 (DynamoDB pagination) — silent truncation
