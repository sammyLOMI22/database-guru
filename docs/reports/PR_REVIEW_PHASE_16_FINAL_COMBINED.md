 Common Themes (Issues raised by 3+ reviewers)

  These are the highest-confidence problems — multiple independent reviewers flagged them:

  1. datetime.utcnow() deprecation — Still unfixed

  Raised by: All 4 reviews | Severity: HIGH

  The tracker itself uses datetime.now(timezone.utc) correctly, but the model defaults in models.py still use datetime.utcnow (lines 33, 50, 88, 89, 119, 120). This
  creates naive-vs-aware datetime mixing that will cause WHERE clause comparison bugs in the API filters. Deprecated since Python 3.12.

  2. SQLite-specific strftime in aggregator — Still unfixed

  Raised by: Technical Audit, Jules, Review #2, Action Plan | Severity: MEDIUM

  LLMUsageAggregator uses func.strftime('%H', ...) which is SQLite-only. All reviewers agree this is acceptable for now but needs at minimum a TODO comment, and
  ideally should use sqlalchemy.extract().

  3. scalar_one_or_none() fuzzy matching bug — Still unfixed

  Raised by: Jules, Review #1, Review #2 | Severity: HIGH

  LLMCostService.get_model_config uses scalar_one_or_none() with a LIKE query. If base_name = "llama3" matches both llama3 and llama3.1, it throws
  MultipleResultsFound. Should use .first() with an ORDER BY length preference.

  4. total_tokens @property serialization — Partially fixed

  Raised by: Jules, Review #1, Review #2 | Severity: LOW (mitigated)

  The schema now uses model_post_init to compute it, which works but is clunky. The frontend also computes it client-side, so this isn't actively breaking anything. A
  @computed_field would be cleaner.

  5. begin_nested() / save resilience — Fixed

  Raised by: Technical Audit, Jules, Review #1, Review #2

  The tracker now correctly uses begin_nested() savepoints. The parent transaction is protected.

  6. SessionUsageBadge background polling — Still unfixed

  Raised by: Jules, Review #1, Review #2 | Severity: MEDIUM

  Polls every 30 seconds unconditionally, even when the tab is hidden. Should use document.visibilityState to pause.

  ---
  Issues Raised by 2 Reviewers
  ┌───────────────────────────────────────────────────────────────────┬──────────────────────────────┬──────────────────────┬──────────┐
  │                               Issue                               │           Reviews            │        Status        │ Severity │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ Duplicate formatNumber/formatCurrency helpers across 3 components │ Jules, Review #2             │ Unfixed              │ Low      │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ Timeseries max days = 30 but frontend offers 90d                  │ Jules, Review #2             │ Unfixed              │ Medium   │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ UsageSummary.tsx is dead code (never imported)                    │ Jules, Review #1             │ Unfixed              │ Low      │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ No pagination on /recent endpoint                                 │ Jules, Review #2             │ Unfixed              │ Low      │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ ensure_default_configs runs on every startup                      │ Review #1, Review #2         │ Unfixed (acceptable) │ Low      │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ Hardcoded provider logic (if-elif chain)                          │ Technical Audit, Action Plan │ Unfixed              │ Low      │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ SchemaHealthAnalyzer God Class                                    │ Technical Audit, Action Plan │ Out of scope         │ N/A      │
  ├───────────────────────────────────────────────────────────────────┼──────────────────────────────┼──────────────────────┼──────────┤
  │ Add connection_id to LLMUsage                                     │ Technical Audit, Action Plan │ Out of scope         │ N/A      │
  └───────────────────────────────────────────────────────────────────┴──────────────────────────────┴──────────────────────┴──────────┘
  ---
  Issues Unique to One Review

  Review #1 (most detailed) found two blockers that no other review caught:
  - QueryHistory.generated_sql NOT NULL crash — Fixed (placeholder added)
  - QueryHistory missing status column — Fixed (column + migration added)
  - Dashboard colSpan mismatch — Fixed (now 8)
  - Deprecated generate_tracked/chat_tracked stubs — Fixed (removed)

  Review #2 uniquely flagged:
  - No auth on usage endpoints (especially POST /aggregate and /configs/seed)
  - _TrackingContext.ollama_response misleading name for multi-provider use
  - Cost defaults already stale (GPT-4o, Claude 3.5 pricing outdated)
  - No tests for the HTTP endpoint layer itself
  - token_calibration_factor column exists but is never used

  ---
  What Needs Fixing Before Merge

  Must fix (will cause runtime bugs):

  1. datetime.utcnow() in model defaults — Replace with lambda: datetime.now(timezone.utc) in all LLMUsage/LLMUsageAggregate/LLMModelConfig column defaults
  2. scalar_one_or_none() fuzzy match — Change to .first() with ORDER BY func.length(model_name) to prefer exact matches
  3. Timeseries max days mismatch — Change le=30 to le=90 in the endpoint parameter

  Should fix (quality/correctness):

  4. SessionUsageBadge visibility polling — Add document.visibilityState check
  5. Duplicate format helpers — Extract to a shared utils/format.ts
  6. Remove dead UsageSummary.tsx — or wire it up somewhere
  7. Rename ollama_response to provider_response on _TrackingContext

  Nice to have (can be follow-up):

  8. Add TODO comment on strftime SQLite portability
  9. Pagination on /recent endpoint
  10. Auth on mutation endpoints (/aggregate, /configs/seed)
  11. Extract provider token logic to a registry pattern
  12. Wire up token_calibration_factor

  ---
  Verdict

  The two original blockers (QueryHistory schema issues) and the rollback danger appear to already be fixed. The remaining must-fix items (#1-3) are straightforward —
  summary of the three fixes applied:                                                                                                              
  #: 1                                                                                                                                                                 
  Fix: datetime.utcnow() deprecation                                                                                                                                   
  File: src/database/models.py                                                                                                                                         
  Change: Replaced 6 instances with lambda: datetime.now(timezone.utc) across LLMUsage, LLMUsageAggregate, and LLMModelConfig                                          
  ────────────────────────────────────────                                                                                                                             
  #: 2                                                                                                                                                                 
  Fix: Fuzzy match MultipleResultsFound bug
  File: src/services/llm_cost_service.py
  Change: Changed scalar_one_or_none() to scalars().first() with ORDER BY length(model_name) to prefer shortest (most exact) match
  ────────────────────────────────────────
  #: 3
  Fix: Timeseries max days mismatch
  File: src/api/endpoints/llm_usage.py
  Change: Changed le=30 to le=90 to match the frontend's 90-day option
  Fix: Visibility-based polling                                                                                                                                        
  File(s): SessionUsageBadge.tsx                                                                                                                                       
  Change: Added document.visibilityState === 'visible' check before polling; wrapped fetchUsage in useCallback                                                         
  ────────────────────────────────────────                                                                                                                             
  #: 5                                                                                                                                                                 
  Fix: Extract duplicate format helpers
  File(s): New utils/formatUtils.ts, updated LLMUsageDashboard.tsx + SessionUsageBadge.tsx                                                                             
  Change: Centralized formatNumber/formatCurrency in shared util, removed local copies
  ────────────────────────────────────────
  #: 6
  Fix: Remove dead component
  File(s): Deleted UsageSummary.tsx
  Change: Was never imported anywhere
  ────────────────────────────────────────
  #: 7
  Fix: Rename misleading field
  File(s): llm_usage_tracker.py
  Change: ollama_response -> provider_response (attribute + parameter + docstring)
  ────────────────────────────────────────
  #: bonus
  Fix: Fix UTC date mismatch
  File(s): llm_usage_aggregator.py + test
  Change: date.today() -> datetime.now(timezone.utc).date() — latent bug causing aggregation to miss records when local/UTC dates differ

  fix for missing llm planning tokens:
                                                                                                                                                      
  Changes Summary                                                                                                                                     

  1. src/llm/query_planning_agent.py
  - create_query_plan(): Now uses return_full_response=True on the ollama.chat() call, extracts prompt_eval_count/eval_count into a
  planning_token_info dict, and returns a tuple (QueryPlan, token_info) instead of just QueryPlan
  - _correct_plan_with_suggestions(): Same pattern — uses return_full_response=True, extracts correction tokens
  - Token aggregation: If schema validation triggers a correction LLM call, those tokens are summed into the planning token_info
  - plan_and_generate_sql(): Unpacks the tuple and passes token_info in the return dict

  2. src/llm/self_correcting_agent.py
  - Planning trace step now spreads planning_token_info into the step metadata, so input_tokens, output_tokens, and model appear in the trace

  3. src/api/endpoints/multi_db_query.py
  - Per-database narrative calls now pass db=db, query_history_id, chat_session_id for usage tracking
  - Added narrative trace steps (with token info) to each database's agent trace
  - Combined narrative call now also passes tracking params

  4. src/api/endpoints/query.py
  - Narrative trace step elapsed_ms now computes relative to the trace start time instead of hardcoded 0

  5. src/api/endpoints/query_planning.py + tests/test_query_planning_agent.py
  - Updated to unpack the new tuple return from create_query_plan()


