PR review from the branch-critique subagent. Verdict: Request changes — one blocking, two important, plus polish.

  ---
  Blocking
  
  - Credential leak in 502 detail strings — src/api/endpoints/graph.py:211, 251. f"Neo4j introspection failed: {exc}" reproduces the driver's exception
   text verbatim in the HTTP body. Neo4j's ServiceUnavailable / AuthError / ConfigurationError embed the connection URI, and bolt://user:pass@host:port
   URIs (allowed by the modal) would round-trip back to the caller. You already logger.exception(...) server-side, so return a generic message and rely
   on the log for diagnostics.

  Important

  - _to_schema_response() belongs on GraphSchema — src/api/endpoints/graph.py:93–115. It calls schema.to_dict() and immediately unpacks every key by
  name. Move it onto the dataclass as to_response(conn, *, cached) so adding a schema field doesn't require touching two files. The nosql analogue
  (normalize_nosql_result()) lives next to the handler for the same reason.
  - Missing tests for two failure paths:
    - Corrupt schema_cache falling through to fresh introspection (endpoints/graph.py:187–199) — no test fixture exercises the except.
    - /ai/schema-summary when the summarizer raises — only the happy path is covered; the endpoint has no explicit guard, so the contract "fallback,
  not 500" isn't locked in.

  Nits

  - useGraphSchema (frontend/src/hooks/useGraphSchema.ts:21): connectionId !== undefined is redundant — the type is number | null.
  - LabelsView selection fallback (GraphSchemaExplorer.tsx:191): when the filter eliminates the selected label, ?? labels[0] silently snaps focus to a
  different item. Either clear selected on filter change (you already do this on tab switch) or render an empty detail panel.
  - frontend/src/services/graphApi.ts re-creates the Axios client + auth interceptor that src/services/api.ts already owns. Either reuse the shared
  instance or add a one-liner explaining the deliberate isolation.
  - src/graph/ai/__init__.py re-exports the summarizer eagerly, partially undermining the lazy-import in endpoints/graph.py:292. Worth a comment so a
  future contributor doesn't accidentally pull the LLM stack into module init.


⏺ Let me also verify the agent's claim about Settings() being bare-instantiated in multi_db_handler.py, since that one is fact-checkable quickly:

  Searched for 2 patterns (ctrl+o to expand)

⏺ PR review from the branch-critique subagent. Verdict: Request changes — one blocking, two important, plus polish.

  ---
  Blocking

  - Credential leak in 502 detail strings — src/api/endpoints/graph.py:211, 251. f"Neo4j introspection failed: {exc}" reproduces the driver's exception
   text verbatim in the HTTP body. Neo4j's ServiceUnavailable / AuthError / ConfigurationError embed the connection URI, and bolt://user:pass@host:port
   URIs (allowed by the modal) would round-trip back to the caller. You already logger.exception(...) server-side, so return a generic message and rely
   on the log for diagnostics.

  Important

  - _to_schema_response() belongs on GraphSchema — src/api/endpoints/graph.py:93–115. It calls schema.to_dict() and immediately unpacks every key by
  name. Move it onto the dataclass as to_response(conn, *, cached) so adding a schema field doesn't require touching two files. The nosql analogue
  (normalize_nosql_result()) lives next to the handler for the same reason.
  - Missing tests for two failure paths:
    - Corrupt schema_cache falling through to fresh introspection (endpoints/graph.py:187–199) — no test fixture exercises the except.
    - /ai/schema-summary when the summarizer raises — only the happy path is covered; the endpoint has no explicit guard, so the contract "fallback,
  not 500" isn't locked in.

  Nits

  - useGraphSchema (frontend/src/hooks/useGraphSchema.ts:21): connectionId !== undefined is redundant — the type is number | null.
  - LabelsView selection fallback (GraphSchemaExplorer.tsx:191): when the filter eliminates the selected label, ?? labels[0] silently snaps focus to a
  different item. Either clear selected on filter change (you already do this on tab switch) or render an empty detail panel.
  - frontend/src/services/graphApi.ts re-creates the Axios client + auth interceptor that src/services/api.ts already owns. Either reuse the shared
  instance or add a one-liner explaining the deliberate isolation.
  - src/graph/ai/__init__.py re-exports the summarizer eagerly, partially undermining the lazy-import in endpoints/graph.py:292. Worth a comment so a
  future contributor doesn't accidentally pull the LLM stack into module init.

  Praise

  - _safe_query in src/graph/neo4j/schema_inspector.py — each parallel probe degrades independently with a human-readable warning. asyncio.gather
  without return_exceptions=True is safe precisely because _safe_query is the exception boundary.
  - graph_schema_from_dict is defensively written with data.get(key) or [] fallbacks — old cached payloads deserialize gracefully.
  - sanitize_uri_for_log in driver_pool.py is correct; the gap is only in the 502 body, not in server logs.
  - useGraphSchemaSummary using useMutation (not useQuery) prevents the summary from being fetched on every Graph tab open — avoids burning LLM tokens
  silently.
  - renderWithQueryClient + the listConnections / settingsAPI mock corrections in this session are clean, minimal fixes that match the production call
  sites.

  One agent claim I want to push back on: the review flagged settings = Settings() at src/core/multi_db_handler.py:68 as bypassing get_settings(). I
  confirmed it via grep — but the same bare instantiation exists at src/main.py:28,62, src/database/connection.py:206, src/database/init_db.py:22,52.
  It's a codebase-wide convention, not a Phase 25.2 regression. Worth fixing as a separate cleanup, not blocking this PR.
##Summary of changes

  ┌─────────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────┐
  │                                     Fix                                     │                              Files                               │
  ├─────────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Blocking — sanitized 502 detail strings so Neo4j driver exceptions can't    │ src/api/endpoints/graph.py:210-215, 240-245                      │
  │ leak bolt URI / creds                                                      │                                                                   │
  ├────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────┤
  │ Important — moved to_response_payload() onto GraphSchema; endpoint      │ src/graph/schema/normalizer.py (+method),                            │
  │ helper now a thin wrapper                                               │ src/api/endpoints/graph.py:93-110                                    │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Important — added defensive try/except so a summarizer regression       │ src/api/endpoints/graph.py:283-318                                   │
  │ returns 200+fallback, not 500                                           │                                                                      │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Important — new test: corrupt schema_cache falls through to fresh       │ tests/graph/test_graph_endpoints.py (TestGetSchemaEndpoint)          │
  │ introspection                                                           │                                                                      │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Important — new test: summarizer raise → fallback, not 500              │ tests/graph/test_graph_endpoints.py (TestSchemaSummaryEndpoint)      │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Test update — rewrote 502 test to assert sanitized body + no credential │ tests/graph/test_graph_endpoints.py                                  │
  │  leak                                                                   │                                                                      │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Nit — removed redundant !== undefined                                   │ frontend/src/hooks/useGraphSchema.ts:21                              │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Nit — clear selected on filter change so the detail panel doesn't       │ frontend/src/components/graph/GraphSchemaExplorer.tsx                │
  │ silently snap focus                                                     │                                                                      │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Nit — documented why graphApi.ts keeps its own axios instance           │ frontend/src/services/graphApi.ts:14-21                              │
  ├─────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ Nit — removed dead eager re-exports that defeated the lazy-import       │ src/graph/ai/__init__.py                                             │
  │ contract; doc-only stub                                                 │                                                                      │
  └─────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────┘

  The agent's Settings() claim in multi_db_handler.py was the only one I declined to touch — it's a codebase-wide convention (5+ other call sites), so
  churn here would be inconsistent with the rest of the repo.
