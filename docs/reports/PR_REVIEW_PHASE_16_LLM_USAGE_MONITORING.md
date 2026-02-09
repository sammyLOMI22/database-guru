  PR Review: Phase 16 - LLM Usage Monitoring
                                                                                                                                                      
  Merge Status                           

  The merge from main (8c79ddf) was clean -- no conflict markers found anywhere in the codebase. The merge integrated the CSV/Excel PR (#50)
  correctly.

  Uncommitted Changes

  There are uncommitted working tree changes that improve upon the initial commit. Key fixes:
  - commit() -> flush() in query.py and tracker (good - keeps single transaction)
  - Router registration added to main.py
  - Frontend API paths fixed (/llm/usage/... -> /api/llm/usage/...)
  - Import of AsyncSession added to self_correcting_agent.py
  - TypeScript lint fixes in dashboard

  ---
  BLOCKERS

  1. QueryHistory.generated_sql is NOT NULL -- early record creation will crash

  query.py:220-228 creates a QueryHistory record before SQL generation to get an ID for tracking:
  query_record = QueryHistory(
      natural_language_query=request.question,
      database_type=database_type,
      connection_id=active_connection.id,
      status="processing"  # <-- also a problem, see #2
  )
  db.add(query_record)
  await db.flush()  # BOOM: IntegrityError
  But QueryHistory.generated_sql is Column(Text, nullable=False) (models.py:134), and no value is provided. The flush() will raise IntegrityError: NOT
   NULL constraint failed: query_history.generated_sql.

  Fix: Either make generated_sql nullable, or provide a placeholder like generated_sql="PENDING".

  2. QueryHistory has no status column

  The code sets status="processing" on creation (line 224) and query_record.status = "completed" later (line 367), but QueryHistory has no status
  column defined in the model. SQLAlchemy will silently accept setting an unknown attribute on the Python object but it won't be persisted -- worse,
  this means there's no way to distinguish processing vs completed records. The status update at line 367 is a no-op.

  Fix: Either add a status = Column(String(20), default='pending') to QueryHistory (and a migration), or remove the status-related code.

  ---
  HIGH SEVERITY

  3. Tracker rollback can destroy parent transaction

  In llm_usage_tracker.py:205, the save() method catches flush errors and calls await self.db.rollback(). Since the tracker shares the same db session
   as the caller (query endpoint), a rollback here rolls back the entire transaction, including the query history record and any other work. This can
  silently lose data.

  try:
      await self.db.flush()
  except Exception as e:
      logger.error(f"Failed to save LLM usage record: {e}")
      await self.db.rollback()  # <-- rolls back parent's work too!

  Fix: Use a savepoint instead:
  try:
      async with self.db.begin_nested():
          self.db.add(usage_record)
          await self.db.flush()
  except Exception:
      logger.error(...)
      # Savepoint rolled back, parent transaction intact

  4. Streaming endpoint breaking change

  In query.py:655-664, the streaming generate_sql call was changed from:
  sql = await sql_generator.generate_sql(...)
  to:
  sql_result = await sql_generator.generate_sql(...)
  sql = sql_result["sql"]
  However, generate_sql() has always returned a Dict -- so the old code was already broken (assigning a dict to sql). This fix is correct, but it
  means the streaming endpoint was never working properly before this PR. Worth noting but not a regression.

  ---
  MEDIUM SEVERITY

  5. LLMUsageResponse.total_tokens property won't serialize

  In schemas.py:846-848:
  @property
  def total_tokens(self) -> int:
      return self.input_tokens + self.output_tokens
  Pydantic @property fields are not included in JSON serialization by default. The recent calls table in the dashboard computes call.input_tokens +
  call.output_tokens client-side, so this isn't currently breaking, but the schema claims to have total_tokens which it doesn't actually return.

  6. Dashboard table colSpan mismatch

  LLMUsageDashboard.tsx:356: The empty state has colSpan={7} but the table has 8 columns (Time, Agent, Provider, Model, Tokens, Cost, Latency,
  Status). Should be colSpan={8}.

  7. No UsageSummary component is used anywhere

  UsageSummary.tsx exists and is imported nowhere in the committed or uncommitted changes. SessionUsageBadge and LLMUsageDashboard are used, but
  UsageSummary appears to be dead code. It was modified but never wired up.

  ---
  LOW SEVERITY / NOTES

  8. generate_tracked() and chat_tracked() deprecated stubs

  ollama_client.py:158-160,253-255 adds deprecated forwarding methods. These add unnecessary API surface -- consider removing them entirely if nothing
   calls them.

  9. datetime.utcnow() deprecation

  Multiple new files use datetime.utcnow() which is deprecated in Python 3.12+. The existing models already use datetime.now(timezone.utc) -- the new
  code should be consistent.

  10. LLMUsage.metadata_json naming

  The model uses Column(JSON, name="metadata") with a Python attribute metadata_json to avoid colliding with SQLAlchemy's Base.metadata. The migration
   correctly creates it as metadata. This works but is a subtle trap for future developers.

  11. LLMCostService.ensure_default_configs runs on every startup

  init_db.py calls ensure_default_configs() on every startup. It does check for existing records, so it's idempotent, but it's extra DB queries on
  every boot.

  ---
  GOOD THINGS

  - Comprehensive agent instrumentation: Tracking parameters are threaded through all 10+ agents consistently (sql_generator, query_planner,
  self_correcting, result_narrator, impact_advisor, lineage agents, etc.)
  - Clean OllamaClient refactoring: Split into _generate_internal/_chat_internal + tracking wrapper is well done
  - Proper opt-in tracking: The if db: guard means existing code without a session still works untracked
  - Good Alembic migration: Clean table creation with proper FK constraints, indexes, and unique constraints
  - Solid test coverage: Unit tests for token estimation/extraction, integration test with real DB session, extended tests for cost calculation and
  aggregation
  - Frontend dashboard: Well-built with proper charting (recharts), time range selector, agent/model/provider breakdowns
  - Frontend API path fix in uncommitted changes catches the /llm/usage/... -> /api/llm/usage/... mismatch

  ---
  Summary
  ┌──────────┬───────────────────────────────────────────────────────┐
  │ Category │                         Count                         │
  ├──────────┼───────────────────────────────────────────────────────┤
  │ Blockers │ 2 (generated_sql NOT NULL, missing status column)     │
  ├──────────┼───────────────────────────────────────────────────────┤
  │ High     │ 2 (rollback danger, streaming fix)                    │
  ├──────────┼───────────────────────────────────────────────────────┤
  │ Medium   │ 3 (property serialization, colSpan, dead code)        │
  ├──────────┼───────────────────────────────────────────────────────┤
  │ Low      │ 4 (deprecated stubs, utcnow, naming, startup queries) │
  └──────────┴───────────────────────────────────────────────────────┘
  The two blockers (#1 and #2) will cause the main query endpoint to crash at runtime. These must be fixed before merging.
  All fixes applied and verified. Here's a summary of what was fixed:                                                                                        
  Fixes Applied                                                                                                                                       
  ┌─────┬──────────┬─────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────┐             
  │  #  │ Severity │                              Issue                              │                       Fix                        │             
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤             
  │ 1   │ BLOCKER  │ QueryHistory.generated_sql NOT NULL but not set in early record │ Added generated_sql="" placeholder               │             
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤             
  │ 2   │ BLOCKER  │ QueryHistory had no status column                               │ Added status column to model + Alembic migration │             
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤             
  │ 3   │ HIGH     │ Tracker rollback() destroys parent transaction                  │ Changed to begin_nested() savepoint              │             
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 4   │ MEDIUM   │ LLMUsageResponse.total_tokens @property doesn't serialize       │ Replaced with model_post_init computed field     │             
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 5   │ MEDIUM   │ Dashboard empty row colSpan={7} vs 8 columns                    │ Fixed to colSpan={8}                             │
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 6   │ LOW      │ datetime.utcnow() deprecated in new files                       │ Replaced with datetime.now(timezone.utc)         │
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 7   │ LOW      │ Deprecated generate_tracked/chat_tracked stubs                  │ Removed dead code                                │
  ├─────┼──────────┼─────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 8   │ TEST     │ Unit test mock didn't support begin_nested()                    │ Added proper async context manager mock          │
  └─────┴──────────┴─────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────┘
