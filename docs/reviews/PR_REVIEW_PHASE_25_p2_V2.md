PR review summary for the phase-25-graph-mode-Neo4J branch:

  Verdict: Approve with minor changes — 1 critical bug + handful of important items

  🔴 Critical (blocks merge)

  1. Wrong default_access_mode="r" in src/graph/neo4j/schema_inspector.py:356 — Neo4j 5.x driver only accepts "READ" or "WRITE"; "r" raises
  ConfigurationError. The bug is invisible because driver.session is a MagicMock in tests. Use neo4j.READ_ACCESS. This will break every schema
  introspection against a real Neo4j server.

  🟡 Important

  2. Neo4jDriverPool not closed on shutdown — src/main.py:192-203 iterates 5 NoSQL pools but skips Neo4j. Bolt connections leak on teardown.
  3. _introspect_graph_database doesn't persist fresh schema — src/core/multi_db_handler.py:85-101. Forces re-introspection on every chat round-trip
  when cache is empty.
  4. _GRAPH_DB_TYPES duplicated in connections.py:25 — should import from src.graph.router.GRAPH_DATABASE_TYPES to avoid sync trap when
  Memgraph/Neptune are added.
  5. Commit 91c07d6 mislabeled as "auth foundation" but actually adds Neo4j schema inspector/normalizer — breaks git bisect for this branch.
  6. GRAPH_MODE_ENABLED=True defaults to opt-out — breaks the project's "opt-in feature flag" convention (ADMIN_UI_ENABLED, METRICS_ENABLED,
  OTEL_ENABLED all default False).
  7. GraphPanel.tsx bypasses react-query — raw useEffect + setState means stale connection list after adding a new Neo4j connection.

  ✅ Done well

  - Clean mirror of src/nosql/ → src/graph/ directory structure
  - _safe_query partial-failure design for degraded DBs
  - 502 endpoint refuses to echo driver errors (credentialed URIs)
  - uri_scheme_forces_tls correctly avoids ConfigurationError
  - Backtick escaping (  ``) for label names
  - fallback_schema_summary guarantees non-blank AI Overview
  - asyncio.gather parallelizes 6 introspection probes
  - 69 test functions / 1,654 lines — strongest phase test suite yet
  - hunter2 credential-leak regression test is well-named

  📝 Docs gap

  - .claude/AGENTS.md and CLAUDE.md not updated with Neo4jGraphAdapter, Neo4jSchemaInspector, GraphSchemaSummarizer, or GRAPH_MODE_ENABLED

  Vibe score: 8.1/10 — very close to mergeable. Fix the default_access_mode bug and the pool shutdown hook; everything else can land as 25.3 prep.
  ##Summary of changes:

  Critical

  - src/graph/neo4j/schema_inspector.py:356 — replaced default_access_mode="r" with neo4j.READ_ACCESS so introspection actually works against a real
  Neo4j 5.x server. Added regression test test_session_opens_with_neo4j_read_access_constant that pins both the constant and the literal "READ" string.

  Important

  - src/main.py — added Neo4jDriverPool.close_all() to the lifespan shutdown alongside the five NoSQL pools so Bolt drivers don't leak.
  - src/core/multi_db_handler.py — fresh introspections now persist to DatabaseConnection.schema_cache via a new _persist_graph_schema_cache helper
  using a short-lived db_manager.get_async_session() (non-fatal on failure).
  - src/api/endpoints/connections.py:25 — _GRAPH_DB_TYPES now imports from src.graph.router.GRAPH_DATABASE_TYPES (single source of truth).
  - src/config/settings.py:209 — GRAPH_MODE_ENABLED default flipped from True → False to match the ADMIN_UI_ENABLED / METRICS_ENABLED / OTEL_ENABLED
  opt-in convention. .env.docker.example doc updated accordingly.
  - frontend/src/components/graph/GraphPanel.tsx — replaced the raw useEffect+setState loader with a useQuery(['connections', 'graph']) hook for
  cache+refetch parity with the rest of the app.

  Docs

  - .claude/AGENTS.md — new "Graph Mode System (Phase 25 — Neo4j)" section covering the router, adapter, driver pool, schema inspector, normalizer,
  summarizer, endpoints, multi-DB integration, and frontend.
  - CLAUDE.md — Key Agents table gets 6 new graph rows; Configuration section gains the 10 GRAPH_* settings with GRAPH_MODE_ENABLED=False opt-in note.

  Verification

  - 85 graph + multi-DB tests pass (2 integration tests skipped — require live Neo4j).
  - tsc --noEmit clean on the frontend.
  - Backend imports load without error.