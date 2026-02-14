PR Review: Phase 16 — LLM Usage Monitoring                                                                                                        
                                                                                                                                                      
  Branch: phase-16-llm-usage-monitoring-5485606923046318167                                                                                           
  Scope: 54 files, ~3,900 lines added — new LLM usage tracking system with backend services, DB models, API endpoints, frontend dashboard, and
  integration across 10+ agents.

  ---
  Critical / High Severity

  1. BUG: agent_trace_dict used before assignment — narratives silently discarded

  src/api/endpoints/query.py:472

  agent_trace_dict is referenced at line 472 but not assigned until line 505. When narratives are enabled, this raises NameError, caught by the broad
  except, and the successfully-generated narrative is silently discarded. This is a regression from code reordering in this PR.

  Fix: Move agent_trace_dict = agent_result.get("agent_trace") to before the narrative block.

  2. ORM cascade conflicts with DB-level ondelete — usage history will be destroyed

  src/database/models.py

  LLMUsage foreign keys use ondelete="SET NULL" (intent: preserve usage records when parent is deleted), but the parent models (QueryHistory,
  ChatSession, ChatMessage) declare cascade="all, delete-orphan". The ORM cascade fires first and deletes the usage records, defeating the SET NULL
  intent. Deleting a chat session will destroy all associated usage history.

  Fix: Change cascades to save-update, merge (or remove delete-orphan) on the parent relationships.

  3. created_at not indexed — full table scans on every dashboard query

  src/database/models.py

  All API endpoints filter on LLMUsage.created_at >= since, but this column has no index. The request_timestamp column has an index but is never
  queried by any endpoint. At scale, every dashboard load triggers a full table scan.

  Fix: Add index=True to created_at, or switch API queries to use the indexed request_timestamp.

  4. Duplicate DB session dependency skips initialization check

  src/api/endpoints/llm_usage.py:19-23

  Defines a local get_session() dependency instead of using the shared get_db from src/api/dependencies/common.py. The local version skips the
  async_session_factory initialization check, which could cause cryptic errors if the DB hasn't been initialized.

  Fix: Use the shared Depends(get_db) dependency.

  5. Breaking return type on create_query_plan()

  src/llm/query_planning_agent.py

  Return type changed from QueryPlan to tuple[QueryPlan, dict]. All callers in the PR are updated, but this is a fragile pattern — any external/plugin
   code calling this method will break. Additionally, _last_correction_token_info instance attribute is used as a side-channel between methods, which
  is not safe for concurrent calls on a shared agent instance.

  ---
  Medium Severity

  6. Model configs not seeded during normal startup

  src/main.py + src/database/init_db.py

  LLMCostService.ensure_default_configs() only runs when init_database() is called manually. The normal app startup via lifespan() does not seed
  configs, so the llm_model_config table will be empty and all cost calculations return $0.00.

  7. Multi-DB parallel queries lose tracking context

  src/api/endpoints/multi_db_query.py

  _execute_single_query_task does not receive db, query_history_id, or chat_session_id. Per-database SQL generation LLM calls (the most expensive
  ones) are untracked in the multi-db path.

  8. Orphaned QueryHistory records on error

  src/api/endpoints/query.py:221-231

  A QueryHistory record is created with status="processing" before SQL generation. If the request fails, this record is never updated to
  status="failed", leaving orphaned processing records.

  9. SQLite-specific SQL in aggregator and API

  src/services/llm_usage_aggregator.py + src/api/endpoints/llm_usage.py

  func.strftime() and func.date() are SQLite-only. If the metadata DB is ever migrated to PostgreSQL, these will fail at runtime.

  10. N+1 upsert in aggregator

  src/services/llm_usage_aggregator.py:57-93

  Individual SELECT + INSERT/UPDATE per aggregation bucket. Could be dozens of queries. Should use INSERT ... ON CONFLICT UPDATE.

  11. LLMCostService.calculate_cost runs DB queries per tracked call, uncached

  src/services/llm_usage_tracker.py:175

  Every LLM call triggers 1-2 DB queries for cost lookup. With 5+ agents per request, that's 5-10 extra DB queries. Should cache model configs in
  memory.

  12. Two competing token-tracking patterns

  sql_generator.py, query_planning_agent.py, result_narrator.py

  Some agents use Pattern A (let the client track via llm_usage_tracker, simple) while others use Pattern B (also request return_full_response=True
  and manually extract token counts for AgentTrace). The token extraction logic is duplicated between the tracker and the callers.

  13. Frontend: Pervasive any types mask a bug

  frontend/src/components/dashboard/LLMUsageDashboard.tsx:302

  recentCalls.map((call: any) casts away the LLMUsageRecord type. Line 322 accesses call.estimated_cost_usd which does not exist on the LLMUsageRecord
   interface — this is a runtime bug hidden by the any cast.

  Also: byModel, byProvider state typed as any[]; getByModel/getByProvider/getSessionUsage return Promise<any>.

  14. Frontend: No error state in dashboard

  LLMUsageDashboard.tsx:41-43

  Fetch failures are only logged to console.error. Users see a blank dashboard with all zeros, indistinguishable from "no usage data."

  15. response_model=List[dict] on two endpoints

  src/api/endpoints/llm_usage.py:94,127

  No validation or OpenAPI documentation. Should use proper Pydantic response models.

  ---
  Low Severity
  ┌─────┬───────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  #  │             File              │                                                 Issue                                                  │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 16  │ llm_usage_tracker.py:21-28    │ Encoder retry on every call after initial failure — no sentinel to prevent repeated retries + log spam │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 17  │ llm_usage_tracker.py:195      │ Redundant request_timestamp column — created_at does the same thing                                    │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 18  │ llm_cost_service.py:24-28     │ LIKE pattern doesn't escape %/_ wildcards in model names                                               │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 19  │ llm_cost_service.py:57-86     │ Missing qwen2.5-coder (the primary project model) from default configs                                 │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 20  │ llm_usage_aggregator.py:58    │ int(row.hour) crashes on NULL hours                                                                    │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 21  │ models.py:92                  │ Nullable hour in unique constraint allows duplicate daily aggregates                                   │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 22  │ schemas.py                    │ InlineUsageStats defined but never used                                                                │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 23  │ ollama_client.py              │ generate() return type weakened from str to Any — should use Union or @overload                        │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 24  │ pattern_intelligence.py       │ _generate_optimizations accepts tracking params but never makes LLM calls — dead params                │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 25  │ lineage_conversation_agent.py │ Missing chat_session_id/chat_message_id — calls tracked without session context                        │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 26  │ multi_db_query.py:938         │ query_record_id captured but never used (dead code)                                                    │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 27  │ query.py:368                  │ Same dead query_record_id variable                                                                     │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 28  │ LLMUsageDashboard.tsx         │ No request cancellation (AbortController) — rapid time-range switches cause race conditions            │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 29  │ SessionUsageBadge.tsx         │ usage state typed as any with no null-safety                                                           │
  ├─────┼───────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 30  │ LLMUsageDashboard.tsx         │ Accessibility: time range buttons lack aria-pressed; loading spinner lacks aria-label                  │
  └─────┴───────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────┘
  ---
  Test Coverage Gaps

  The test suite covers basic happy paths but misses important scenarios:
  Gap: No test for track_call failure/error path (set_response never called, DB flush fails)
  Impact: Silent data loss undetected
  ────────────────────────────────────────
  Gap: No test for aggregation idempotency (calling aggregate_usage twice)
  Impact: Could double-count
  ────────────────────────────────────────
  Gap: No test for any of the 7 API endpoints in llm_usage.py
  Impact: Response shape mismatches with frontend go undetected
  ────────────────────────────────────────
  Gap: No test for session usage endpoint (/session/{session_id})
  Impact: SessionUsageBadge depends on untested endpoint
  ────────────────────────────────────────
  Gap: extract_tokens not tested for None/empty response, unknown provider, or partial Ollama response
  Impact: Edge case crashes
  ────────────────────────────────────────
  Gap: Fuzzy model name matching (llama3:latest → llama3) untested
  Impact: Core cost service feature
  ────────────────────────────────────────
  Gap: Token estimation test only asserts > 0, not a reasonable range
  Impact: Would pass even with wildly wrong values
  ---
  Positive Observations

  - Tracking doesn't break the main flow — all tracking calls are wrapped in try/except with logging, so failures are isolated.
  - Non-breaking for existing callers — all new parameters default to None.
  - Clean migration chain — both migrations are properly ordered and reversible.
  - SessionUsageBadge respects document.visibilityState — no polling when browser tab is hidden.
  - Good defensive sanitization in prepare_response_for_storage — caps result rows, strips trace data.
  - Streaming endpoint correctly stores response_data with empty results.

  ---
  Recommended Fix Priority

  1. Fix the agent_trace_dict NameError (#1) — this is an active bug that silently breaks narratives
  2. Fix the cascade conflict (#2) — usage history will be destroyed on session deletion
  3. Add index to created_at (#3) — performance will degrade quickly with real usage
  4. Switch to shared get_db dependency (#4) — one-line fix
  5. Seed model configs in lifespan (#6) — cost tracking is DOA without this
  6. Add estimated_cost_usd to LLMUsageRecord TypeScript interface (#13) — runtime bug