The reviewer flagged two critical correctness issues, one security latent bomb, and several design/doc gaps. Here's the rolled-up verdict:

  Critical (block merge)

  1. encrypted toggle silently dropped — ConnectionTester.test_connection / _test_neo4j have no encrypted param, so the UI's TLS toggle has no effect
  during connection test. src/core/connection_tester.py:40 + src/api/endpoints/connections.py dispatch.
  2. DatabaseUnavailable misclassified — Neo4j 5's DatabaseUnavailable is NOT a subclass of ServiceUnavailable; falls through to the catch-all with
  error_code="unknown_error". src/graph/neo4j/handler.py:154–178.

  Important (fix this PR)

  3. Latent credential-leak in details["raw"] — ConnectionTestResult.to_dict() will surface raw driver exception text (often embeds URIs) when 25.2
  wires up /api/graph/*. Two-line fix: wrap with sanitize_uri_for_log(). src/graph/neo4j/handler.py:156,165,177.
  4. _sanitize_error regex [a-zA-Z+]+ breaks on neo4j+s:// — digit 4 excluded; leaves neo4 prefix in sanitized output. Switch to [\w+.-]+://.
  src/core/connection_tester.py:21.
  5. read_only NOT NULL DEFAULT TRUE applies to ALL existing rows — postgres/mysql/mongodb/redis/cassandra connections all become read_only=True after
  migration. Not breaking yet, but 25.2 must gate every read of this column on is_graph(). Reviewer recommends switching the column default to NULL,
  enforce at app layer.
  6. GRAPH_MODE_ENABLED is inert — exists in settings, no code reads it. Either gate neo4j in ConnectionCreate regex on this flag, or remove until 25.2
   wires it.
  7. Plan doc drift — PHASE_25_GRAPH_MODE_NEO4J_PLAN.md §4 still lists POST /api/graph/connections/test as a 25.1 deliverable. Update to match reality.

  Important (design / tests)

  8. Neo4jDriverPool._drivers mutated without per-instance lock — race when 25.2 wires it (two coroutines could double-create + leak a driver). Not
  used in 25.1 but fix before 25.2.
  9. No integration-test skeleton — all 26 tests fully mock the driver. Add at least one @pytest.mark.integration skipped-by-default test that hits
  bolt://localhost:7687 from the graph profile container.
  10. test_missing_host_returns_helpful_error fragile — fails if neo4j pkg isn't installed in CI (hits ImportError branch before reaching the empty-URI
   check). Mock the import or relax the assertion.

  Nit

  11. NEO4J_AUTH default neo4j/password is a known default — add to .env.example with override warning. start_period: 20s is tight for cold image
  pulls; bump to 30s.

  Recommendation: REQUEST CHANGES — fix #1 (encrypted threading) and #2 (DatabaseUnavailable) before merge; the rest can ride in a follow-up commit on
  the same PR.
### FIXES
All 11 review items fixed and verified.

  Summary of fixes applied

  ┌─────┬──────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  #  │        Reviewer issue        │                                                    Fix                                                     │
  ├─────┼──────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 1   │ encrypted toggle silently    │ Added encrypted= param to ConnectionTester.test_connection + _test_neo4j; threaded from                    │
  │     │ dropped                      │ /api/connections/test endpoint. New test: test_encrypted_threaded_to_build_driver.                         │
  ├─────┼──────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 2   │ DatabaseUnavailable falls into    │ Imported + dedicated except DatabaseUnavailable branch returning error_code="database_unavailable"   │
  │     │ catch-all                         │ with the database name in the message. New test: test_database_unavailable.                          │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │ details["raw"] credential leak    │ Wrapped str(exc) with sanitize_uri_for_log() in all 4 failure paths. New test:                       │
  │ 3   │ (latent for 25.2)                 │ test_details_raw_is_sanitized exercises a ServiceUnavailable whose message embeds                    │
  │     │                                   │ bolt://neo4j:supersecret@host.                                                                       │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 4   │ _sanitize_error regex skipped     │ Switched scheme class from [a-zA-Z+]+ to [A-Za-z][\w+.-]*. 2 new tests for neo4j+s and bolt+ssc.     │
  │     │ neo4j+s://                        │                                                                                                      │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │ read_only NOT NULL DEFAULT TRUE   │ Migration 7b1e9f3a2c4d now creates read_only nullable with no server_default; model matches;         │
  │ 5   │ polluted legacy rows              │ application layer (_resolve_read_only helper) sets True only when database_type='neo4j'. 3 new tests │
  │     │                                   │  for the resolver. Migration downgraded + re-upgraded locally; existing tests still pass.            │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 6   │ GRAPH_MODE_ENABLED was inert      │ Added _ensure_graph_mode_enabled() guard wired into both create + test endpoints via get_settings    │
  │     │                                   │ dependency. 3 new tests: disabled blocks, enabled allows, non-graph types unaffected.                │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │ Plan doc said                     │ Plan §4 rewritten — API table now has a "Ships in" column; Phase 25.1 row updated to reflect actual  │
  │ 7   │ /api/graph/connections/test ships │ delivery (reuses /api/connections/test); §5.1 modal text aligned.                                    │
  │     │  in 25.1                          │                                                                                                      │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │                                   │ Renamed class-level lock to _singleton_lock; added per-instance _mutation_lock; refactored helpers   │
  │ 8   │ Neo4jDriverPool._drivers race     │ to _locked variants. New test test_concurrent_get_creates_one_driver proves 3 concurrent get() calls │
  │     │                                   │  produce exactly 1 build_driver.                                                                     │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 9   │ No integration test               │ Added TestNeo4jIntegration class with @pytest.mark.integration + skipif(not                          │
  │     │                                   │ os.getenv("NEO4J_TEST_URI")). Documented invocation in the docstring.                                │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 10  │ Fragile import-dependent test     │ Relaxed assertion to accept either "URI is required" or "Neo4j support not installed" — passes       │
  │     │                                   │ regardless of CI driver presence.                                                                    │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 1   │ encrypted toggle silently dropped │ Added encrypted= param to ConnectionTester.test_connection + _test_neo4j; threaded from              │
  │     │                                   │ /api/connections/test endpoint. New test: test_encrypted_threaded_to_build_driver.                   │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 2   │ DatabaseUnavailable falls into    │ Imported + dedicated except DatabaseUnavailable branch returning error_code="database_unavailable"   │
  │     │ catch-all                         │ with the database name in the message. New test: test_database_unavailable.                          │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │ details["raw"] credential leak    │ Wrapped str(exc) with sanitize_uri_for_log() in all 4 failure paths. New test:                       │
  │ 3   │ (latent for 25.2)                 │ test_details_raw_is_sanitized exercises a ServiceUnavailable whose message embeds                    │
  │     │                                   │ bolt://neo4j:supersecret@host.                                                                       │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 4   │ _sanitize_error regex skipped     │ Switched scheme class from [a-zA-Z+]+ to [A-Za-z][\w+.-]*. 2 new tests for neo4j+s and bolt+ssc.     │
  │     │ neo4j+s://                        │                                                                                                      │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │ read_only NOT NULL DEFAULT TRUE   │ Migration 7b1e9f3a2c4d now creates read_only nullable with no server_default; model matches;         │
  │ 5   │ polluted legacy rows              │ application layer (_resolve_read_only helper) sets True only when database_type='neo4j'. 3 new tests │
  │     │                                   │  for the resolver. Migration downgraded + re-upgraded locally; existing tests still pass.            │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 6   │ GRAPH_MODE_ENABLED was inert      │ Added _ensure_graph_mode_enabled() guard wired into both create + test endpoints via get_settings    │
  │     │                                   │ dependency. 3 new tests: disabled blocks, enabled allows, non-graph types unaffected.                │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │ Plan doc said                     │ Plan §4 rewritten — API table now has a "Ships in" column; Phase 25.1 row updated to reflect actual  │
  │ 7   │ /api/graph/connections/test ships │ delivery (reuses /api/connections/test); §5.1 modal text aligned.                                    │
  │     │  in 25.1                          │                                                                                                      │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │     │                                   │ Renamed class-level lock to _singleton_lock; added per-instance _mutation_lock; refactored helpers   │
  │ 8   │ Neo4jDriverPool._drivers race     │ to _locked variants. New test test_concurrent_get_creates_one_driver proves 3 concurrent get() calls │
  │     │                                   │  produce exactly 1 build_driver.                                                                     │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 9   │ No integration test               │ Added TestNeo4jIntegration class with @pytest.mark.integration + skipif(not                          │
  │     │                                   │ os.getenv("NEO4J_TEST_URI")). Documented invocation in the docstring.                                │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 10  │ Fragile import-dependent test     │ Relaxed assertion to accept either "URI is required" or "Neo4j support not installed" — passes       │
  │     │                                   │ regardless of CI driver presence.                                                                    │
  ├─────┼───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 11  │ NEO4J_AUTH default + healthcheck  │ Added Graph-profile section to .env.docker.example with override warning + GRAPH_MODE_ENABLED doc;   │
  │     │ timing                            │ bumped healthcheck start_period from 20s → 30s.                                                      │
  └─────┴───────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Test results

  - 40 graph tests collected: 39 passing, 1 integration test correctly skipped (no NEO4J_TEST_URI).
  - 333 tests passing across tests/graph/, tests/nosql/, tests/dml/, tests/test_admin_users_endpoints.py.
  - Pre-existing failures in tests/test_ownership.py and tests/test_feedback_api.py confirmed to be unrelated (reproduced with this branch's changes
  stashed).
  - Frontend TypeScript: clean.
  - Alembic: downgrade → upgrade cycle clean against SQLite.