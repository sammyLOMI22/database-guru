PR Review: Phase 17 — Multi-Provider Monitoring

  Branch: phase-17-Multi-Provider-Monitoring → main (2 commits, 16 files, +2157/−125)

  Overview

  Adds user-managed LLM model pricing (CRUD endpoints + admin UI), cost-summary & provider-comparison analytics endpoints, Vertex/Bedrock/LM Studio/vLLM
  token extraction, and a 519-line test suite. Removes the hardcoded ensure_default_configs seed in favor of explicit user configuration.

  Strengths

  - Clean service layer. LLMCostService CRUD methods are small, composable, and mirror existing patterns.
  - Good test coverage across token extraction (all 8 providers), service methods, and endpoints — ~519 lines, uses FastAPI TestClient +
  dependency_overrides properly.
  - Thoughtful UX: unpriced-models surfacing drives users to configure pricing rather than silently charging $0.
  - Schemas are well-typed (Pydantic models added to schemas.py for all new responses).
  - Divide-by-zero is guarded in both avg_cost_per_call and success_rate.

  Issues & Risks

  High — Missing authentication on admin endpoints

  src/api/endpoints/llm_usage.py:676-725 — POST /model-configs and DELETE /model-configs/{name} accept no auth dependency. Phase 21 added
  require_admin/get_current_user but these mutating endpoints expose pricing tampering to any caller when REQUIRE_AUTH=True. Add Depends(require_admin) to
   POST/DELETE (and likely GET on unpriced/configs too).

  Medium — Upsert is not race-safe

  llm_cost_service.py upsert reads → checks → writes without locking. LLMModelConfig.model_name is unique=True (models.py:102), so concurrent creates will
   raise IntegrityError rather than merge. Either catch and retry, or use INSERT ... ON CONFLICT DO UPDATE via sqlalchemy.dialects.sqlite.insert.

  Medium — model_name uniqueness conflicts with multi-provider models

  Unique constraint is on model_name alone, but the same model (e.g. llama3) can live on ollama, vllm, and lm_studio simultaneously. Upserting llama3 for
  vllm would overwrite the ollama config. The unique key should be (model_name, provider) — this is already the convention in uq_llm_agg_dimensions
  (models.py:93).

  Medium — Cost calculation uses float arithmetic

  USD amounts stored/summed as float; precision drift across millions of calls. Consider Numeric(12, 6) for estimated_cost_usd and cost_per_1m_*. Not
  blocking, but worth flagging before large deployments.

  Low — Timezone handling in daily breakdown

  func.date(LLMUsage.created_at) groups by the raw timestamp. SQLite stores these naive; if records are inserted as UTC but viewed from a PT user, day
  boundaries shift. Consider accepting a tz param or documenting UTC.

  Low — AWS Bedrock token shape assumes Converse API

  llm_usage_tracker.py:68-71 reads usage.inputTokens / outputTokens — correct for Bedrock's Converse API, but InvokeModel responses vary by model family
  (e.g. Anthropic on Bedrock returns usage.input_tokens). If the tracked client uses Converse exclusively, add a comment; otherwise this will silently
  yield None.

  Low — Redundant patch in tests

  tests/test_multi_provider_monitoring.py:1372 patches src.api.endpoints.llm_usage.get_db and uses app.dependency_overrides. FastAPI resolves via the
  dependency system — the patch has no effect. Remove for clarity.

  Low — Pydantic request model missing server-side validation

  ModelConfigCreateRequest doesn't enforce cost >= 0. Frontend validates, but never trust the client. Add Field(ge=0) to both cost fields.

  Nit — UI polish

  - frontend/src/components/dashboard/LLMUsageDashboard.tsx:164 — capitalize on azure_openai renders "Azure_openai". Replace underscores before
  capitalizing.
  - ModelPricingManager.tsx:322-330 — "Add Model" starts with empty model_name/provider strings; save button has no disabled state, letting users POST
  blank payloads (backend would accept them — no length/format validation).

  Summary

  Feature is solid and well-tested, but before merge: add admin auth, fix the (model_name, provider) uniqueness, and address the upsert race. The
  float/timezone/Bedrock items are fine as follow-ups.

  Changes                                                                                                                                                 
                                                                                                                                                          
  Auth (High) — src/api/endpoints/llm_usage.py                                                                                                            
  - POST /model-configs and DELETE /model-configs/{provider}/{model_name} now require Depends(require_admin).                                             
  - Delete route restructured to {provider}/{model_name} to match the new composite key.                                                                  
                                                                                                                                                          
  Composite uniqueness (Medium) — src/database/models.py + new migration a7c2e9b1d3f4                                                                     
  - Changed LLMModelConfig unique constraint from model_name alone to (model_name, provider) so the same model on ollama vs. vllm doesn't overwrite.      
  - Migration uses batch_alter_table(copy_from=..., recreate='always') to actually drop SQLite's anonymous column-level unique. Verified round-trip       
  upgrade/downgrade.                                                                                                                                      
                                                                                                                                                          
  Race-safe upsert (Medium) — src/services/llm_cost_service.py                                                                                          
  - Upsert now retries on IntegrityError: on concurrent create it rolls back, re-reads, and updates.                                                      
  - Delete signature is (model_name, provider=None) for back-compat, but the endpoint now always passes provider.                                         
  - get_unpriced_models compares (model_name, provider) tuples against configured pairs, not just names.                                                  
                                                                                                                                                          
  Server-side validation (Low) — src/models/schemas.py                                                                                                    
  - ModelConfigCreateRequest enforces min_length, max_length, and ge=0 for costs.                                                                         
                                                                                                                                                          
  Frontend polish — frontend/src/components/dashboard/{LLMUsageDashboard,ModelPricingManager}.tsx                                                         
  - Added formatProvider() helper that splits on _ and title-cases each word (so azure_openai → Azure Openai instead of Azure_openai).                    
  - ModelPricingManager trims and validates name/provider before save; row keys now use ${provider}-${model_name} composite.                              
  - Delete button now passes both provider and model name.                                                                                                
                                                                                                                                                          
  Tests — tests/test_multi_provider_monitoring.py                                                                                                       
  - Removed redundant patch("...get_db") next to dependency_overrides.                                                                                    
  - Added 3 new tests: test_create_model_config_requires_admin, test_create_model_config_rejects_negative_cost, test_delete_model_config_requires_admin,  
  test_upsert_model_config_race_falls_back_to_update.                                                                                                     
  - Updated delete URLs to /openai/gpt-4o shape; admin-endpoint tests override require_admin.                                                             
                                                                                                                                                        
  Not changed (flagged as acceptable follow-ups in the review): Float→Numeric for cost columns, timezone handling in func.date(), Bedrock Converse vs     
  InvokeModel response shape. These are non-blocking and deferred.