 PR Review: Phase 16 — LLM Usage Monitoring
                                                                                                                                                      
  Branch: phase-16-llm-usage-monitoring                                                                                                             
  Scope: ~3,000 lines added across 43 files (3 new services, 3 new DB tables, 7 API endpoints, 3 frontend components, 3 test files, integration across
   ~10 agents)

  ---
  What Works Well

  1. Clean architecture. The tracker follows a context-manager pattern (async with tracker.track_call(...) as tracking) that's easy for agents to
  adopt. The three-layer decomposition — LLMUsageTracker (recording), LLMCostService (pricing), LLMUsageAggregator (rollups) — gives good separation
  of concerns.

  2. Non-intrusive integration. The OllamaClient changes are well done: tracking is opt-in via db= parameter. When db is None, the code path is
  unchanged. Existing callers that don't pass db are completely unaffected.

  3. Native token extraction with fallback chain. The priority order (Ollama native → tiktoken → char estimate) is sensible. The
  token_estimation_method column preserves provenance so you can audit accuracy later.

  4. Frontend dashboard. The LLMUsageDashboard is comprehensive — time series, agent/model/provider breakdowns, latency bars, and a
  recent-transactions table. The SessionUsageBadge is a nice lightweight touch for inline visibility.

  5. Good test structure. The unit/integration/extended split covers the tracker, cost service, aggregator, and the full SQLGenerator → tracking flow.

  6. Migration is well-formed. Indexes on the high-cardinality query columns (agent_type, model_name, provider, request_timestamp, chat_session_id)
  are correct for the API query patterns.

  ---
  Issues & Edge Cases

  Critical

  1. begin_nested() can silently swallow tracking failures — llm_usage_tracker.py:203-208

  try:
      async with self.db.begin_nested():
          self.db.add(usage_record)
          await self.db.flush()
  except Exception as e:
      logger.error(f"Failed to save LLM usage record: {e}")

  If the outer transaction is not in a valid state (e.g., the session was already rolled back due to the LLM call exception), begin_nested() itself
  will throw. Since save() runs in the finally block of the context manager, this means:
  - If the LLM call raises AND the session is invalidated, save() silently fails and you lose the error record.
  - Worse, if SQLite doesn't fully support SAVEPOINTs (the async driver has known quirks), begin_nested() may degrade. Consider wrapping the entire
  save in a try/except at the session level or using a separate session for telemetry writes.

  2. request_timestamp uses datetime.utcnow (naive) — models.py:33,50

  request_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

  But the tracker sets request_timestamp=datetime.now(timezone.utc) (aware) at line 193. Mixing naive and aware datetimes in SQLite will cause
  comparison issues in the API's WHERE created_at >= since filters (where since is timezone-aware from datetime.now(timezone.utc)). The model defaults
   and the tracker code should be consistent — prefer timezone.utc everywhere.

  3. LLMUsageResponse schema has total_tokens field but LLMUsage model exposes it as a @property — models.py:57-59, schemas.py:839

  The LLMUsageResponse Pydantic model declares total_tokens: int = 0, but the SQLAlchemy model has total_tokens as a @property, not a column. When
  FastAPI serializes result.scalars().all() at llm_usage.py:279, the ORM objects won't have total_tokens in their __dict__, so Pydantic's
  from_attributes (or orm_mode) may return 0 instead of the computed value. You likely need model_config = ConfigDict(from_attributes=True) on the
  schema and to verify that Pydantic v2 reads properties (it does with from_attributes=True, but the default 0 could mask silent failures).

  Moderate

  4. Fuzzy model matching can match wrong models — llm_cost_service.py:23-26

  base_name = model_name.split(":")[0]
  stmt = select(LLMModelConfig).where(LLMModelConfig.model_name.like(f"{base_name}%"))
  result = await db.execute(stmt)
  config = result.scalar_one_or_none()

  scalar_one_or_none() will throw MultipleResultsFound if base_name = "llama3" matches both llama3 and llama3.1. This should use .first() instead, or
  add ordering to prefer exact prefix matches.

  5. Aggregator uses SQLite-specific func.strftime — llm_usage_aggregator.py:37

  func.strftime('%H', LLMUsage.created_at).label('hour'),

  This hardcodes SQLite dialect. If the project ever moves metadata to Postgres (mentioned in the tech stack as supported), aggregation breaks. This
  is fine for now but worth a comment/TODO.

  6. No pagination on /recent endpoint beyond limit — llm_usage.py:260-279

  The /recent endpoint has limit (max 500) but no offset or cursor. For production usage, scrolling past the first page is impossible. This is fine as
   an initial implementation but will need pagination.

  7. No authentication/authorization on usage endpoints — llm_usage.py:17

  The /api/llm/usage/* routes and especially POST /aggregate and POST /configs/seed are open. The POST endpoints mutate data (trigger aggregation,
  seed configs). If other endpoints in the app have auth, these should too.

  8. _TrackingContext.ollama_response is misnamed — llm_usage_tracker.py:138,141

  The field is called ollama_response but extract_tokens supports OpenAI and Anthropic too. The naming is misleading for multi-provider scenarios.

  9. SessionUsageBadge polls every 30 seconds unconditionally — SessionUsageBadge.tsx:27

  const interval = setInterval(fetchUsage, 30000);

  This fires even when the tab is in the background. For users with many sessions open, this creates unnecessary API load. Consider using
  document.visibilityState or only polling when the component is visible.

  10. ensure_default_configs runs on every startup — init_db.py:33-36

  await LLMCostService.ensure_default_configs(session)

  It does a SELECT for each model before inserting, which is fine, but ensure_default_configs calls await db.commit() at line 90 — this commits inside
   init_database() which may interfere with the broader initialization transaction context. Should be idempotent but the commit scope is worth
  verifying.

  11. Timeseries endpoint has inconsistent days max — llm_usage.py:162

  The /timeseries endpoint limits to le=30 days, but the time-range selector in the dashboard offers 90d. Requests for 90-day timeseries will return a
   422 validation error.

  Minor

  12. Duplicate formatNumber / formatCurrency helpers — Defined separately in LLMUsageDashboard.tsx, SessionUsageBadge.tsx, and UsageSummary.tsx.
  Should be in a shared utils file.

  13. any types in frontend — byModel, byProvider states in LLMUsageDashboard.tsx:16-17 and usage in SessionUsageBadge.tsx:12 are typed as any. Create
   interfaces for these.

  14. Cost defaults are already stale — llm_cost_service.py:63-80 lists GPT-4o at $5/$15 and Claude 3.5 Sonnet at $3/$15. Current pricing has changed.
   Consider making this user-configurable via the settings UI rather than hardcoded.

  15. LLMUsage created_at column uses deprecated datetime.utcnow — Python 3.12+ deprecated datetime.utcnow(). The other models in this file already
  use lambda: datetime.now(timezone.utc).

  ---
  Future Improvements

  1. Data retention/cleanup — The llm_usage table will grow unboundedly. Add a TTL-based cleanup job (e.g., keep 90 days of raw records, rely on
  aggregates for older data).
  2. Streaming support — The tracker doesn't handle streaming responses (stream=True). When streaming is enabled, time_to_first_token_ms is always
  None and token counts may be inaccurate. Consider adding a streaming-aware tracking mode.
  3. Rate/budget alerts — The dashboard shows current costs but doesn't alert when spending exceeds a threshold. A simple budget limit in
  SystemSettings could be useful.
  4. Export/download — No way to export usage data as CSV for external analysis.
  5. Aggregate scheduling — The aggregator is only triggered via a manual POST /aggregate call. A periodic background task (e.g., on startup or via a
  scheduler) would keep the aggregate table fresh.
  6. Token calibration — The token_calibration_factor column exists in LLMModelConfig but is never used. Wire it into the cost calculation to correct
  for known estimation biases.
  7. Tests for API endpoints — There are no tests for the /api/llm/usage/* FastAPI endpoints themselves. The unit tests cover the services but not the
   HTTP layer.

  ---
  Summary

  This is a solid Phase 16 implementation that adds meaningful observability to the system. The core design (context-manager tracker, per-call DB
  records, multi-provider token extraction) is well thought out. The highest-priority fixes are:

  1. Naive vs. aware datetime inconsistency — will cause real query bugs
  2. scalar_one_or_none() in fuzzy matching — will throw on multiple model matches
  3. Timeseries max days (30) vs. dashboard option (90d) — will cause 422 errors
  4. Verify total_tokens property serialization — could silently return 0