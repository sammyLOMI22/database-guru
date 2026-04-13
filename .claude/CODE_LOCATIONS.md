# Key Code Locations Reference

Quick reference for finding important code in the Database Guru codebase.

## Security & Auth (Phase 21 - March 2026)
| Component | Location |
|-----------|----------|
| **Auth Module** | |
| Auth service | `src/auth/service.py` |
| Password hashing | `src/auth/service.py:hash_password()` |
| JWT create/decode | `src/auth/service.py:create_access_token()` / `decode_token()` |
| User model | `src/auth/models.py:User` |
| Auth schemas | `src/auth/schemas.py` (UserCreate, UserLogin, TokenResponse) |
| Auth dependencies | `src/auth/dependencies.py` |
| get_current_user | `src/auth/dependencies.py:get_current_user()` |
| get_optional_user | `src/auth/dependencies.py:get_optional_user()` |
| require_admin | `src/auth/dependencies.py:require_admin()` |
| **Audit Logging** | |
| AuditLog model | `src/auth/audit.py:AuditLog` |
| log_action helper | `src/auth/audit.py:log_action()` |
| **API Endpoints** | |
| Auth endpoints | `src/api/endpoints/auth.py` (register, login, me) |
| Audit endpoints | `src/api/endpoints/audit.py` (admin logs, user logs) |
| **Rate Limiting** | |
| User ID extraction | `src/middleware/rate_limit.py:_extract_user_id_from_token()` |
| **Migrations** | |
| Users table | `alembic/versions/a1b2c3d4e5f6_add_users_table.py` |
| Owner ID columns | `alembic/versions/b2c3d4e5f6a7_add_owner_id_columns.py` |
| Audit logs table | `alembic/versions/c3d4e5f6a7b8_add_audit_log_table.py` |
| **Tests** | |
| Auth tests | `tests/test_auth.py` (25 tests) |
| Ownership tests | `tests/test_ownership.py` (13 tests) |
| Rate limit tests | `tests/test_rate_limit_user.py` (8 tests) |
| Audit tests | `tests/test_audit.py` (8 tests) |
| Soft-delete tests | `tests/test_connection_soft_delete.py` (3 tests) |

## Edit Mode & DML (Phase 18 - March 2026)
| Component | Location |
|-----------|----------|
| **DML Module** | |
| DML Generator | `src/dml/dml_generator.py` |
| DML Validator | `src/dml/dml_validator.py` |
| DML Executor | `src/dml/dml_executor.py` |
| DML Models | `src/dml/models.py` |
| DML Constants | `src/dml/constants.py` (SAFE_IDENT_RE) |
| **API Endpoints** | |
| DML endpoints | `src/api/endpoints/dml.py` (preview, execute, permissions, table-info) |
| **Database Models** | |
| ConnectionWritePermission | `src/database/models.py:ConnectionWritePermission` |
| **Migrations** | |
| Write permissions table | `alembic/versions/d4e5f6a7b8c9_add_connection_write_permissions.py` |
| **Frontend** | |
| Edit components | `frontend/src/components/edit/` (7 components) |
| Change tracker hook | `frontend/src/hooks/useChangeTracker.ts` |
| Edit mode hook | `frontend/src/hooks/useEditMode.ts` |
| DML execution hook | `frontend/src/hooks/useDMLExecution.ts` |
| DML API service | `frontend/src/services/dmlApi.ts` |
| DML types | `frontend/src/types/dml.ts` |
| **Tests** | |
| Generator tests | `tests/dml/test_dml_generator.py` |
| Validator tests | `tests/dml/test_dml_validator.py` |
| Executor tests | `tests/dml/test_dml_executor.py` |

## Core Entry Points

| Component | Location |
|-----------|----------|
| Main application | `src/main.py:54` |
| Query processing | `src/api/endpoints/query.py:32` |
| Self-correction logic | `src/llm/self_correcting_agent.py:541` |
| Parallel corrections | `src/llm/self_correcting_agent.py:373` |
| Confidence scoring | `src/llm/confidence_scorer.py:147` |
| Multi-DB queries | `src/core/multi_db_handler.py:481` |
| Schema validation | `src/core/schema_validator.py` |
| SQL execution | `src/core/executor.py:42` |

## Conversational Memory
| Component | Location |
|-----------|----------|
| Memory agent | `src/llm/conversational_memory_agent.py` |
| Context endpoints | `src/api/endpoints/chat.py` |

## Security
| Component | Location |
|-----------|----------|
| Prompt Sanitization | `src/security/prompt_sanitizer.py` |
| Security Tests | `tests/test_prompt_sanitizer.py` |

## Parallel Execution (Production-Ready)
| Component | Location |
|-----------|----------|
| Parallel Multi-DB | `src/core/multi_db_handler.py:75` (schema), `:481` (queries), `:561` (throttling) |
| Parallel Tests | `tests/test_parallel_multi_db.py`, `tests/test_parallel_corrections.py` |
| Frontend Metrics | `frontend/src/components/ParallelExecutionMetrics.tsx` |

## Row Limit & Pagination (December 27, 2025)
| Component | Location |
|-----------|----------|
| Row limit dropdown | `frontend/src/components/QueryInput.tsx` |
| Table pagination | `frontend/src/components/QueryResults.tsx` |
| Multi-DB pagination | `frontend/src/components/MultiDatabaseResults.tsx` |
| Schema field | `src/models/schemas.py` (`row_limit` in QueryRequest) |
| Tests | `frontend/tests/QueryResults.test.tsx`, `frontend/tests/MultiDatabaseResults.test.tsx` |

## Multi-Database Query Validation (January 7, 2026)
| Component | Location |
|-----------|----------|
| Validator | `src/llm/multi_db_query_validator.py` (1061 lines) |
| SQL parsing | `src/llm/multi_db_query_validator.py:289` |
| NL analysis | `src/llm/multi_db_query_validator.py:650` |
| Location validation | `src/llm/multi_db_query_validator.py:767` |
| API integration | `src/api/endpoints/multi_db_query.py:662` |
| SchemaGlance UI | `frontend/src/components/SchemaGlance.tsx` (382 lines) |
| Assessment UI | `frontend/src/components/MultiDatabaseAssessment.tsx` (264 lines) |
| Badges | `frontend/src/components/QueryFeasibilityBadge.tsx` (194 lines) |
| Tests | `tests/test_multi_db_query_validator.py` (27 tests) |

## Tool-Using Agent
| Component | Location |
|-----------|----------|
| Agent | `src/llm/tool_using_agent.py` |
| Registry | `src/tools/tool_registry.py` |
| Schema Tools | `src/tools/schema_tools.py` |
| Data Tools | `src/tools/data_tools.py` |
| Query Tools | `src/tools/query_tools.py` |
| API | `src/api/endpoints/tools.py` |
| Tests | `tests/test_tools.py` (26 tests) |
| UI | `frontend/src/components/ToolsPanel.tsx` |
| UI Tests | `frontend/tests/ToolsPanel.test.tsx` (30 tests) |
| API Service | `frontend/src/services/toolsApi.ts` |

## Semantic Caching (November 22, 2025)
| Component | Location |
|-----------|----------|
| Embedding service | `src/cache/embedding_service.py` |
| Semantic cache | `src/cache/semantic_cache.py` |
| LLM cache | `src/cache/llm_cache.py` |
| Tests | `tests/test_semantic_caching.py` (20 tests) |
| API | `src/api/endpoints/cache.py` |
| UI Panel | `frontend/src/components/SemanticCachePanel.tsx` |
| UI Overview | `frontend/src/components/CacheOverview.tsx` |
| UI Stats | `frontend/src/components/CacheStatistics.tsx` |
| UI Recent | `frontend/src/components/RecentCachedQueries.tsx` |
| API Service | `frontend/src/services/cacheApi.ts` |
| UI Tests | `frontend/tests/SemanticCachePanel.test.tsx` (34 tests) |

## Result Narrator (December 13, 2025)
| Component | Location |
|-----------|----------|
| Narrator | `src/llm/result_narrator.py` |
| Main entry | `src/llm/result_narrator.py:63` |
| Anomaly detection | `src/llm/result_narrator.py:346` |
| Trend detection | `src/llm/result_narrator.py:593` |
| Correlation | `src/llm/result_narrator.py:694` |
| UI Summary | `frontend/src/components/ResultSummary.tsx` |
| UI Toggle | `frontend/src/components/ChatInterface.tsx` |
| Unit tests | `tests/test_result_narrator.py` (41 tests) |
| Perf tests | `tests/test_performance_narratives.py` (11 tests) |
| E2E tests | `tests/test_e2e_narratives.py` (12 tests) |
| Multi-DB narratives | `src/api/endpoints/multi_db_query.py:662-740` |
| Multi-DB tests | `tests/test_multi_db_narratives.py` (10 tests) |

## Data Insights Enhancement (Phase 19 - February 2026)
| Component | Location |
|-----------|----------|
| **19.1 Tiered Narrative Prompts** | |
| Prompt templates | `src/llm/prompts/narrative_tiers.py` |
| Prompt selector | `src/llm/prompts/narrative_tiers.py:get_narrative_prompt()` |
| Token budgets | `src/llm/prompts/narrative_tiers.py:NARRATIVE_TOKEN_BUDGETS` |
| Model tier detection | `src/llm/result_narrator.py:_get_model_tier()` |
| Stats compression | `src/llm/result_narrator.py:_compress_statistics()` |
| Prompts package init | `src/llm/prompts/__init__.py` |
| Tests | `tests/test_narrative_tiers.py` (31 tests) |
| **19.2 Analytics Cache** | |
| Cache service | `src/services/analytics_cache.py` |
| Result hashing | `src/services/analytics_cache.py:compute_result_hash()` |
| Singleton getter | `src/services/analytics_cache.py:get_analytics_cache()` |
| Narrator integration | `src/llm/result_narrator.py:_get_or_compute_statistics()` |
| Settings | `src/config/settings.py` (ANALYTICS_CACHE_*) |
| Tests | `tests/test_analytics_cache.py` (21 tests) |
| **19.3 Multi-Source Quality** | |
| Quality metrics | `src/llm/result_narrator.py:DataQualityMetrics` |
| Gap detection | `src/llm/result_narrator.py:GapInsight` |
| Quality report | `src/llm/result_narrator.py:MultiSourceQualityReport` |
| Report builder | `src/llm/result_narrator.py:_build_multi_source_quality_report()` |
| Cached report | `src/llm/result_narrator.py:_get_or_compute_quality_report()` |
| Tests | `tests/test_multi_source_insights.py` (24 tests) |
| **19.4 Chart Intelligence** | |
| Adaptive presets | `frontend/src/utils/chartIntelligence.ts:ScoringPreset` |
| Column interest | `frontend/src/utils/chartIntelligence.ts:scoreColumnInterest()` |
| Context insights | `frontend/src/utils/chartIntelligence.ts:analyzeData()` |
| Tests | `frontend/tests/chartIntelligenceEnhancements.test.ts` (16 tests) |
| **19.5 Parallel Analysis** | |
| Parallel pipeline | `src/llm/result_narrator.py:generate_narrative()` (lines 193-227) |
| Early exit | `src/llm/result_narrator.py:generate_narrative()` (lines 188-190) |
| Tests | `tests/test_parallel_analysis.py` (16 tests) |

## Connection Pooling (December 6, 2025)
| Component | Location |
|-----------|----------|
| Pool manager | `src/core/connection_pool_manager.py` (489 lines) |
| DB connector | `src/core/user_db_connector.py` |
| API | `src/api/endpoints/pools.py` (4 endpoints, 240 lines) |
| Config | `src/config/settings.py` |
| UI Dashboard | `frontend/src/components/ConnectionPoolMetrics.tsx` (435 lines) |
| API Service | `frontend/src/services/poolsApi.ts` (150 lines) |
| Unit tests | `tests/test_connection_pool_manager.py` (18 tests) |
| Integration | `tests/test_pooled_query_execution.py` (8 tests) |
| Perf tests | `tests/test_pooling_performance.py` (3 tests) |
| Docker infra | `tests/fixtures/docker-compose.test.yml` |
| Setup script | `scripts/setup_test_databases.sh` |

## Advanced Visualization (December 20-26, 2025)
| Component | Location |
|-----------|----------|
| Chart intelligence | `frontend/src/utils/chartIntelligence.ts` (~700 lines) |
| Intent parser | `frontend/src/utils/chartIntentParser.ts` (~240 lines) |
| Time series | `frontend/src/utils/timeSeriesDetector.ts` (~180 lines) |
| Hierarchy | `frontend/src/utils/hierarchyDetector.ts` (~150 lines) |
| Hierarchy utils | `frontend/src/utils/hierarchicalChartUtils.ts` (~300 lines) |
| Statistical utils | `frontend/src/utils/statisticalChartUtils.ts` (~360 lines) |
| TreemapView | `frontend/src/components/visualization/TreemapView.tsx` |
| SunburstView | `frontend/src/components/visualization/SunburstView.tsx` |
| HistogramView | `frontend/src/components/visualization/HistogramView.tsx` |
| BoxPlotView | `frontend/src/components/visualization/BoxPlotView.tsx` |
| AreaChartView | `frontend/src/components/visualization/AreaChartView.tsx` |
| BubbleChartView | `frontend/src/components/visualization/BubbleChartView.tsx` |
| Main container | `frontend/src/components/visualization/ChartVisualization.tsx` |
| Toggle | `frontend/src/components/visualization/ChartToggle.tsx` |
| Tests | `frontend/tests/AdvancedCharts.test.tsx` (61 tests) |

## Small Model Optimization (January 2-11, 2026)
| Component | Location |
|-----------|----------|
| Model router | `src/llm/model_router.py` (246 lines) |
| Query templates | `src/llm/query_templates.py` (1024 lines) |
| Dialect registry | `src/llm/dialect_registry.py` (205 lines) |
| Query preprocessor | `src/llm/query_preprocessor.py` (504 lines) |
| Prompt optimizer | `src/llm/prompt_optimizer.py` (1013 lines) |
| Quality profile | `src/llm/quality_profile.py` |
| Agent integration | `src/llm/self_correcting_agent.py:821-907, 1068-1111` |
| DB models | `src/database/models.py` |
| Settings API | `src/api/endpoints/settings.py` |
| Models API | `src/api/endpoints/models.py` |
| UI Config | `frontend/src/components/ModelConfigPanel.tsx` (465 lines) |
| Settings UI | `frontend/src/components/SettingsPanel.tsx` |
| Router tests | `tests/test_model_router.py` (220 lines) |
| Preprocessor tests | `tests/test_query_preprocessor.py` (264 lines) |
| Template tests | `tests/test_query_templates.py` (510 lines) |
| Dialect tests | `tests/test_dialect_registry.py` (72 lines) |
| Optimizer tests | `tests/test_prompt_optimizer.py` (600 lines, 52 tests) |

## Data Lineage System (January 2026)
| Component | Location |
|-----------|----------|
| SQL parser | `src/lineage/sql_lineage_parser.py` (835 lines) |
| Parser entry | `src/lineage/sql_lineage_parser.py:parse()` |
| Table extraction | `src/lineage/sql_lineage_parser.py:_extract_tables()` |
| Column processing | `src/lineage/sql_lineage_parser.py:_process_select_item()` |
| Impact analyzer | `src/lineage/impact_analyzer.py` (341 lines) |
| Column impact | `src/lineage/impact_analyzer.py:analyze_column_impact()` |
| Table impact | `src/lineage/impact_analyzer.py:analyze_table_impact()` |
| Pattern analyzer | `src/lineage/query_pattern_analyzer.py` (399 lines) |
| Heatmap data | `src/lineage/query_pattern_analyzer.py:get_heatmap_data()` |
| Bottlenecks | `src/lineage/query_pattern_analyzer.py:identify_bottlenecks()` |
| API | `src/api/endpoints/lineage.py` (6 endpoints, 227 lines) |
| LineagePanel UI | `frontend/src/components/lineage/LineagePanel.tsx` |
| LineageGraph | `frontend/src/components/lineage/LineageGraph.tsx` |
| Heatmap | `frontend/src/components/lineage/QueryPatternHeatmap.tsx` |
| API Service | `frontend/src/services/lineageApi.ts` |
| Layout utils | `frontend/src/utils/lineageLayoutUtils.ts` |
| Parser tests | `tests/test_sql_lineage_parser.py` (100+ tests) |
| Impact tests | `tests/test_impact_analyzer.py` (20+ tests) |
| Pattern tests | `tests/test_query_pattern_analyzer.py` (20+ tests) |
| Frontend tests | `frontend/tests/LineageGraph.test.tsx` (15+ tests) |

## Lineage Intelligence (Phase 12 - January 2026)
| Component | Location |
|-----------|----------|
| **Phase 12.1: Lineage Narrator** | |
| Narrator agent | `src/lineage/lineage_narrator.py` (553 lines) |
| Narrative generation | `src/lineage/lineage_narrator.py:generate_narrative()` |
| Prompt building | `src/lineage/lineage_narrator.py:_build_prompt()` |
| UI component | `frontend/src/components/lineage/LineageNarrative.tsx` (215 lines) |
| Tests | `tests/test_lineage_narrator.py` (474 tests) |
| **Phase 12.2: Impact Advisor** | |
| Advisor agent | `src/lineage/impact_advisor.py` (796 lines) |
| Recommendations | `src/lineage/impact_advisor.py:analyze_with_recommendations()` |
| Migration plans | `src/lineage/impact_advisor.py:_generate_migration_plan()` |
| SQL patches | `src/lineage/impact_advisor.py:_generate_sql_patches()` |
| UI component | `frontend/src/components/lineage/ImpactAdvisorPanel.tsx` (408 lines) |
| Tests | `tests/test_impact_advisor.py` (455 tests) |
| **Phase 12.3: Schema Health Analyzer** | |
| Health analyzer | `src/lineage/schema_health_analyzer.py` (1105 lines) |
| Health analysis | `src/lineage/schema_health_analyzer.py:analyze_schema_health()` |
| Score calculation | `src/lineage/schema_health_analyzer.py:_calculate_score()` |
| Index suggestions | `src/lineage/schema_health_analyzer.py:_suggest_indexes()` |
| UI component | `frontend/src/components/schema/SchemaHealthDashboard.tsx` (739 lines) |
| Tests | `tests/test_schema_health.py` (817 tests) |
| **Phase 12.4: Pattern Intelligence** | |
| Intelligence agent | `src/lineage/pattern_intelligence.py` (959 lines) |
| Pattern analysis | `src/lineage/pattern_intelligence.py:analyze_patterns()` |
| Bottleneck analysis | `src/lineage/pattern_intelligence.py:analyze_bottleneck()` |
| Anti-pattern detection | `src/lineage/pattern_intelligence.py:_detect_anti_patterns()` |
| UI enhancement | `frontend/src/components/lineage/QueryPatternHeatmap.tsx` (429 lines) |
| Tests | `tests/test_pattern_intelligence.py` (584 tests) |
| **Phase 12.5: Conversational Lineage** | |
| Conversation agent | `src/lineage/lineage_conversation_agent.py` (1055 lines) |
| Question answering | `src/lineage/lineage_conversation_agent.py:ask()` |
| Question classifier | `src/lineage/lineage_conversation_agent.py:_classify_question()` |
| UI component | `frontend/src/components/lineage/LineageChat.tsx` (363 lines) |
| Tests | `tests/test_lineage_conversation.py` (630 tests) |
| **API Integration** | |
| Lineage endpoints | `src/api/endpoints/lineage.py` (773 lines, 11 endpoints) |
| API service | `frontend/src/services/lineageApi.ts` (165 lines) |
| Type definitions | `frontend/src/types/lineage.ts` (264 lines) |

## LLM Usage Monitoring (Phase 16 - February 2026)
| Component | Location |
|-----------|----------|
| **Backend Services** | |
| Usage tracker | `src/services/llm_usage_tracker.py` |
| Track call context mgr | `src/services/llm_usage_tracker.py:track_call()` |
| Token estimation | `src/services/llm_usage_tracker.py:estimate_tokens()` |
| Token extraction (6 providers) | `src/services/llm_usage_tracker.py:extract_tokens()` |
| Cost service | `src/services/llm_cost_service.py` |
| Cost calculation | `src/services/llm_cost_service.py:calculate_cost()` |
| Usage aggregator | `src/services/llm_usage_aggregator.py` |
| **API Endpoints** | |
| Usage API | `src/api/endpoints/llm_usage.py` (16 endpoints) |
| Stats endpoint | `src/api/endpoints/llm_usage.py:get_usage_stats()` |
| Session endpoint | `src/api/endpoints/llm_usage.py:get_session_usage()` |
| **Database Models** | |
| LLMUsage model | `src/database/models.py:LLMUsage` |
| LLMUsageAggregate | `src/database/models.py:LLMUsageAggregate` |
| LLMModelConfig | `src/database/models.py:LLMModelConfig` |
| Migration | `alembic/versions/f451a46c49e1_add_llm_usage_tables.py` |
| **Schemas** | |
| Response schemas | `src/models/schemas.py` (LLMUsageResponse, LLMUsageStatsResponse, etc.) |
| Phase 17 schemas | `src/models/schemas.py` (ModelConfigResponse, CostSummaryResponse, ProviderComparisonResponse, etc.) |
| **Frontend Components** | |
| Usage dashboard | `frontend/src/components/dashboard/LLMUsageDashboard.tsx` |
| Model pricing manager | `frontend/src/components/dashboard/ModelPricingManager.tsx` |
| Session usage summary | `frontend/src/components/UsageSummary.tsx` |
| Session usage badge | `frontend/src/components/SessionUsageBadge.tsx` |
| API service | `frontend/src/services/llmUsageApi.ts` |
| **Agent Integration** | |
| LLM client factory | `src/llm/__init__.py:get_llm_client()` |
| Tracked LLM client | `src/llm/tracked_client.py` |
| Ollama client (legacy shim) | `src/llm/ollama_client.py` |
| Self-correcting agent | `src/llm/self_correcting_agent.py` |
| Query planning agent | `src/llm/query_planning_agent.py` |
| Result narrator | `src/llm/result_narrator.py` |
| **Tests** | |
| Unit tests | `tests/unit/test_llm_usage_tracker.py` |
| Extended tests | `tests/test_llm_usage_extended.py` |
| Integration tests | `tests/integration/test_usage_tracking_integration.py` |
| Multi-provider tests | `tests/test_multi_provider_monitoring.py` (29 tests) |

## Multi-Provider Monitoring (Phase 17 - April 2026)
| Component | Location |
|-----------|----------|
| **Backend** | |
| Token extraction (6 formats) | `src/services/llm_usage_tracker.py:extract_tokens()` |
| Model config CRUD | `src/services/llm_cost_service.py` (get_all_configs, upsert, delete) |
| Unpriced model detection | `src/services/llm_cost_service.py:get_unpriced_models()` |
| Cost summary endpoint | `src/api/endpoints/llm_usage.py:get_cost_summary()` |
| Provider comparison endpoint | `src/api/endpoints/llm_usage.py:get_provider_comparison()` |
| Model config endpoints | `src/api/endpoints/llm_usage.py` (list, upsert, delete model-configs) |
| Unpriced models endpoint | `src/api/endpoints/llm_usage.py:list_unpriced_models()` |
| **Schemas** | |
| ModelConfigResponse | `src/models/schemas.py:ModelConfigResponse` |
| ModelConfigCreateRequest | `src/models/schemas.py:ModelConfigCreateRequest` |
| UnpricedModelResponse | `src/models/schemas.py:UnpricedModelResponse` |
| CostSummaryResponse | `src/models/schemas.py:CostSummaryResponse` |
| ProviderComparisonResponse | `src/models/schemas.py:ProviderComparisonResponse` |
| **Frontend** | |
| Model pricing manager | `frontend/src/components/dashboard/ModelPricingManager.tsx` (~294 lines) |
| Dashboard updates | `frontend/src/components/dashboard/LLMUsageDashboard.tsx` (cost summary, provider comparison) |
| API service extensions | `frontend/src/services/llmUsageApi.ts` (getCostSummary, getProviderComparison, model config CRUD) |
| **Tests** | |
| Multi-provider tests | `tests/test_multi_provider_monitoring.py` (29 tests) |

## Database Migration Toolkit (Phase 20 - February 2026)
| Component | Location |
|-----------|----------|
| **Backend Core** | |
| Schema comparator | `src/migration/schema_comparator.py` |
| Schema diff model | `src/migration/schema_comparator.py:SchemaDiff` |
| SchemaDiff.from_dict | `src/migration/schema_comparator.py:SchemaDiff.from_dict()` |
| Migration planner | `src/migration/migration_planner.py` |
| Topo sort (with FKs) | `src/migration/migration_planner.py:_topological_sort_tables()` |
| Script generator | `src/migration/script_generator.py` |
| SQLite recreate | `src/migration/script_generator.py:_sqlite_recreate()` |
| SQL injection escape | `src/migration/script_generator.py:_escape_literal()` |
| Data migration asst. | `src/migration/data_migration_assistant.py` |
| Drift detector (stub) | `src/migration/drift_detector.py` |
| **API Endpoints** | |
| Migration API | `src/api/endpoints/migration.py` (13 endpoints) |
| Schema diff | `src/api/endpoints/migration.py:compare_schemas()` |
| Plan generation | `src/api/endpoints/migration.py:generate_plan()` |
| Script generation | `src/api/endpoints/migration.py:create_scripts()` |
| Data migration | `src/api/endpoints/migration.py:generate_data_migration()` |
| Script download | `src/api/endpoints/migration.py:download_script()` |
| **Database Model** | |
| MigrationProject model | `src/database/models.py:MigrationProject` |
| Migration (Alembic) | `alembic/versions/b7e3a1d2f456_*.py` |
| **Schemas** | |
| Request/Response schemas | `src/models/schemas.py` (SchemaDiffRequest, MigrationPlanResponse, etc.) |
| MigrationToolkitStepSchema | `src/models/schemas.py:MigrationToolkitStepSchema` |
| **Tests** | |
| Migration API tests | `tests/test_migration_api.py` |

## File Data Source System (Phase 13 - January 2026)
| Component | Location |
|-----------|----------|
| **Backend Core** | |
| File handler | `src/core/file_source_handler.py` (~400 lines) |
| File validation | `src/core/file_source_handler.py:validate_file()` |
| Schema inference | `src/core/file_source_handler.py:infer_schema()` |
| File saving | `src/core/file_source_handler.py:save_file()` |
| DuckDB session | `src/core/file_source_session.py` (~300 lines) |
| Session singleton | `src/core/file_source_session.py:get_instance()` |
| Table loading | `src/core/file_source_session.py:ensure_table_loaded()` |
| Query execution | `src/core/file_source_session.py:execute_query()` |
| **API Endpoints** | |
| File endpoints | `src/api/endpoints/files.py` (~350 lines, 8 endpoints) |
| Upload endpoint | `src/api/endpoints/files.py:upload_file()` |
| Schema endpoint | `src/api/endpoints/files.py:get_file_schema()` |
| Preview endpoint | `src/api/endpoints/files.py:get_file_preview()` |
| Excel sheets | `src/api/endpoints/files.py:get_excel_sheets()` |
| **Database Model** | |
| FileSource model | `src/database/models.py:FileSource` (lines 198-256) |
| Migration | `alembic/versions/c22b240bc731_*.py` |
| **Schemas** | |
| Request schemas | `src/models/schemas.py` (lines 1041-1158) |
| FileSourceCreate | `src/models/schemas.py:FileSourceCreate` |
| FileSchemaResponse | `src/models/schemas.py:FileSchemaResponse` |
| FilePreviewResponse | `src/models/schemas.py:FilePreviewResponse` |
| **Frontend Components** | |
| Upload modal | `frontend/src/components/FileUploadModal.tsx` (~400 lines) |
| Preview panel | `frontend/src/components/FilePreviewPanel.tsx` (~350 lines) |
| API service | `frontend/src/services/api.ts:filesAPI` (lines 480-562) |
| Type definitions | `frontend/src/types/api.ts` (lines 644-690) |
| **Tests** | |
| Backend tests | `tests/test_file_sources.py` (50+ tests) |
| Validation tests | `tests/test_file_sources.py:TestFileValidation` |
| Schema tests | `tests/test_file_sources.py:TestSchemaInference` |
| Session tests | `tests/test_file_sources.py:TestDuckDBSession` |
| **Configuration** | |
| Settings | `src/config/settings.py` (lines 65-74) |
| Upload directory | `FILE_UPLOAD_DIR` |
| Max file size | `FILE_MAX_SIZE_MB` |
| DuckDB memory | `DUCKDB_FILE_MEMORY_LIMIT` |

---

### Performance Guru (Phase 22)

| Component | Location |
|-----------|----------|
| **Backend Core** | |
| Explain Analyzer | `src/guru/explain_analyzer.py` (~640 lines) |
| Explain Interpreter | `src/guru/explain_interpreter.py` (~380 lines) |
| Explain Prompts | `src/guru/prompts/explain_prompts.py` (~200 lines) |
| Package init | `src/guru/__init__.py` |
| **API** | |
| Performance endpoints | `src/api/endpoints/performance.py` (~160 lines) |
| Router registration | `src/main.py` (line ~192) |
| **Schemas** | |
| Request/Response schemas | `src/models/schemas.py` (Performance Guru section) |
| PerformanceAnalysisRequest | `src/models/schemas.py:PerformanceAnalysisRequest` |
| ExecutionPlanSchema | `src/models/schemas.py:ExecutionPlanSchema` |
| PerformanceInsightsSchema | `src/models/schemas.py:PerformanceInsightsSchema` |
| SQL validator | `src/models/schemas.py:_validate_explain_sql` |
| **Model Router** | |
| TaskType.EXPLAIN_ANALYSIS | `src/llm/model_router.py` |
| **Frontend Components** | |
| Performance Panel | `frontend/src/components/performance/PerformancePanel.tsx` (~215 lines) |
| Execution Plan Tree | `frontend/src/components/performance/ExecutionPlanTree.tsx` (~147 lines) |
| Insights Panel | `frontend/src/components/performance/PerformanceInsightsPanel.tsx` (~245 lines) |
| API service | `frontend/src/services/performanceApi.ts` |
| Type definitions | `frontend/src/types/performance.ts` |
| **Tests** | |
| Analyzer tests | `tests/test_explain_analyzer.py` (355+ tests) |
| Interpreter tests | `tests/test_explain_interpreter.py` (374+ tests) |
| API tests | `tests/test_performance_api.py` (257+ tests) |

## LLM Provider Expansion (Phase 15 - April 2026)
| Component | Location |
|-----------|----------|
| **Provider Abstraction** | |
| Base provider ABC | `src/llm/providers/base.py` (BaseLLMProvider, DataLocality, LLMResponse) |
| Provider registry | `src/llm/providers/registry.py` (ProviderRegistry, initialize_registry_from_settings) |
| Tracked LLM client | `src/llm/tracked_client.py` (TrackedLLMClient) |
| Client factory | `src/llm/__init__.py:get_llm_client()` |
| Ollama shim | `src/llm/ollama_client.py` (backward-compatible OllamaClient alias) |
| **Provider Implementations** | |
| Ollama | `src/llm/providers/ollama.py` (LOCAL) |
| OpenAI-compatible base | `src/llm/providers/openai_compat.py` |
| OpenAI | `src/llm/providers/openai_provider.py` (CLOUD_PUBLIC) |
| Azure OpenAI | `src/llm/providers/azure_openai.py` (CLOUD_PRIVATE) |
| Anthropic | `src/llm/providers/anthropic.py` (CLOUD_PUBLIC) |
| Google Vertex AI | `src/llm/providers/google_vertex.py` (CLOUD_PRIVATE) |
| AWS Bedrock | `src/llm/providers/aws_bedrock.py` (CLOUD_PRIVATE) |
| LM Studio | `src/llm/providers/lm_studio.py` (LOCAL) |
| vLLM | `src/llm/providers/vllm.py` (LOCAL) |
| **API & Config** | |
| Provider API endpoints | `src/api/endpoints/llm_providers.py` (8 endpoints) |
| Provider config service | `src/services/provider_config_service.py` (Fernet encryption) |
| Model router (provider) | `src/llm/model_router.py:get_provider_for_task()`, `execute_with_fallback()` |
| DB models | `src/database/models.py:LLMProviderConfig`, `LLMTaskRouting` |
| Settings | `src/config/settings.py` (DATA_SECURITY_LEVEL, per-provider flags) |
| **Frontend** | |
| Provider settings panel | `frontend/src/components/LLMProviderSettings.tsx` |
| Provider card | `frontend/src/components/ProviderCard.tsx` |
| Task routing config | `frontend/src/components/TaskRoutingConfig.tsx` |
| Provider API client | `frontend/src/services/llmProviderApi.ts` |
| Model locality badges | `frontend/src/components/ModelConfigPanel.tsx:ModelSelect` |
| **Tests** | |
| Provider abstraction | `tests/llm/test_tracked_client.py` |
| OpenAI-compat providers | `tests/llm/test_openai_compat.py` |
| Azure + Anthropic | `tests/llm/test_azure_anthropic.py` |
| Vertex + Bedrock | `tests/llm/test_vertex_bedrock.py` |
| Router + config + API | `tests/llm/test_phase15_4.py` |
