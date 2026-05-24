# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Database Guru is an AI-powered natural language to database query assistant. Users ask questions in plain English, and the system generates, executes, and self-corrects queries using LLMs. Supports 8 LLM providers (local and cloud), both SQL and NoSQL databases with native query generation for each.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy 2.0 (async) + Python 3.11+
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- LLM Providers: Ollama (default local), OpenAI, Azure OpenAI, Anthropic, Google Vertex AI, AWS Bedrock, LM Studio, vLLM
- SQL Databases: PostgreSQL, MySQL, SQLite, DuckDB, MSSQL, Oracle
- NoSQL Databases: MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch
- File Sources: CSV, Excel (via DuckDB)
- Metadata: SQLite

## Development Commands

After completing a task that involves tool use, provide a quick summary of the work you've done.

### Backend
```bash
source venv/bin/activate                    # Activate venv
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000  # Start server
./run_tests.sh                              # Run all tests
./run_tests.sh tests/test_file.py           # Run specific test
python -m pytest tests/ --cov=src --cov-report=html  # Coverage
```

### Frontend
```bash
cd frontend
npm run dev      # Start dev server
npm test         # Run tests
npm run build    # Production build
npm run lint     # Lint
```

### System
```bash
./start.sh       # Start all services (local dev)
./stop.sh        # Stop all services (local dev)
ollama serve     # Ensure Ollama is running
```

### Docker
```bash
docker compose up -d                           # Default: SQLite + BYO LLM
docker compose --profile ollama up -d          # + bundled Ollama
docker compose --profile full up -d            # + PostgreSQL + Redis
docker compose --profile full --profile ollama up -d  # Everything
docker compose build                           # Rebuild after code changes
docker compose down                            # Stop all
docker compose down -v                         # Stop + remove volumes
```

## Architecture Overview

The system uses a multi-agent architecture with 40+ specialized agents (including 6 NoSQL handlers, auth system, and DML pipeline). See [.claude/AGENTS.md](.claude/AGENTS.md) for detailed agent documentation.

### Key Agents (Quick Reference)
| Agent | File | Purpose |
|-------|------|---------|
| Self-Correcting | `src/llm/self_correcting_agent.py` | Main orchestrator, parallel corrections |
| Conversational Memory | `src/llm/conversational_memory_agent.py` | Multi-turn dialog context |
| Query Planning | `src/llm/query_planning_agent.py` | Chain-of-thought reasoning |
| Confidence Scorer | `src/llm/confidence_scorer.py` | Success probability prediction |
| Multi-DB Handler | `src/core/multi_db_handler.py` | Parallel database execution |
| File Source Handler | `src/core/file_source_handler.py` | CSV/Excel file processing (Phase 13) |
| File Source Session | `src/core/file_source_session.py` | DuckDB session for file queries |
| Result Narrator | `src/llm/result_narrator.py` | Human-readable insights, tiered prompts, parallel analysis (Phase 19) |
| Model Router | `src/llm/model_router.py` | Per-task model + provider selection, fallback chains (Phase 15) |
| Provider Registry | `src/llm/providers/registry.py` | Multi-provider registration, security enforcement (Phase 15) |
| Tracked LLM Client | `src/llm/tracked_client.py` | Provider-agnostic LLM wrapper with usage tracking (Phase 15) |
| Provider Config Service | `src/services/provider_config_service.py` | Encrypted API key storage, provider CRUD (Phase 15) |
| SQL Lineage Parser | `src/lineage/sql_lineage_parser.py` | Column-level lineage |
| Lineage Narrator | `src/lineage/lineage_narrator.py` | LLM-powered lineage explanations (Phase 12.1) |
| Impact Advisor | `src/lineage/impact_advisor.py` | Migration plans & SQL patches (Phase 12.2) |
| Schema Health Analyzer | `src/lineage/schema_health_analyzer.py` | Database design quality (Phase 12.3) |
| Pattern Intelligence | `src/lineage/pattern_intelligence.py` | Query pattern insights (Phase 12.4) |
| Lineage Conversation | `src/lineage/lineage_conversation_agent.py` | Natural language Q&A (Phase 12.5) |
| LLM Usage Tracker | `src/services/llm_usage_tracker.py` | Token & cost tracking, 6 provider formats (Phase 16/17) |
| LLM Cost Service | `src/services/llm_cost_service.py` | User-managed model pricing, cost calculation (Phase 16/17) |
| Narrative Tiers | `src/llm/prompts/narrative_tiers.py` | Model-size-aware prompt templates (Phase 19) |
| Analytics Cache | `src/services/analytics_cache.py` | Two-tier stats/pattern cache (Phase 19) |
| Schema Comparator | `src/migration/schema_comparator.py` | DB-to-DB schema diff engine (Phase 20) |
| Migration Planner | `src/migration/migration_planner.py` | Dependency-aware migration planning (Phase 20) |
| Script Generator | `src/migration/script_generator.py` | up.sql/down.sql/verify.sql generation (Phase 20) |
| Data Migration Asst. | `src/migration/data_migration_assistant.py` | Batched INSERT SELECT with validation (Phase 20) |
| Explain Analyzer | `src/guru/explain_analyzer.py` | Deterministic EXPLAIN plan parser, multi-dialect (Phase 22) |
| Explain Interpreter | `src/guru/explain_interpreter.py` | LLM-powered plan interpretation with fallback (Phase 22) |
| NoSQL Router | `src/nosql/router.py` | NoSQL dispatch, result normalization (Phase 14) |
| MongoDB Handler | `src/nosql/mongodb/handler.py` | MQL generation, aggregation, schema inference (Phase 14) |
| Redis Handler | `src/nosql/redis/handler.py` | Redis command generation, all data types (Phase 14) |
| Cassandra Handler | `src/nosql/cassandra/handler.py` | CQL generation, partition-aware queries (Phase 14) |
| DynamoDB Handler | `src/nosql/dynamodb/handler.py` | PartiQL generation, boto3 integration (Phase 14) |
| Elasticsearch Handler | `src/nosql/elasticsearch/handler.py` | Query DSL generation, aggregations (Phase 14) |
| Graph Router | `src/graph/router.py` | Graph dispatch by `database_type`; canonical `GRAPH_DATABASE_TYPES` (Phase 25) |
| Neo4j Graph Adapter | `src/graph/neo4j/handler.py` | `GraphAdapter` impl — connection-test surface (Phase 25.1) |
| Neo4j Driver Pool | `src/graph/neo4j/driver_pool.py` | Per-connection `AsyncDriver` cache, LRU, lifespan-closed (Phase 25.1) |
| Neo4j Schema Inspector | `src/graph/neo4j/schema_inspector.py` | Parallel Cypher probes (labels/rels/indexes/constraints/patterns/counts) in `READ_ACCESS` sessions, partial-failure tolerant (Phase 25.2) |
| Graph Schema Normalizer | `src/graph/schema/normalizer.py` | Raw Neo4j rows → `GraphSchema` dataclass; `graph_schema_from_dict` reload (Phase 25.2) |
| Graph Schema Summarizer | `src/graph/ai/schema_summarizer.py` | LLM "Overview" card with `fallback_schema_summary` (Phase 25.2) |
| Cypher Safety Classifier | `src/graph/safety/classifier.py` | 5-tier classifier (READ_ONLY/WRITE/ADMIN/DANGEROUS/UNKNOWN); strips literals + comments, validates procedure FQNs (Phase 25.3) |
| Cypher Query Executor | `src/graph/neo4j/query_executor.py` | Wraps `session.run` with safety gate, READ_ACCESS sessions, query timeout, record cap; never raises (Phase 25.3) |
| Cypher Result Formatter | `src/graph/result_formatter.py` | Duck-typed walker: Node/Relationship/Path → table + Cytoscape `graph_viz`, viz caps via `GRAPH_MAX_VIZ_*` (Phase 25.3) |
| Neo4j Error Classifier | `src/graph/neo4j/error_classifier.py` | Maps driver exceptions to UX categories (auth/timeout/syntax/unknown_label/…) without leaking URIs (Phase 25.3) |
| Cypher Generator | `src/graph/neo4j/cypher_generator.py` | NL → Cypher via LLM, fence stripping, LIMIT injection, unknown-label detection (Phase 25.4) |
| Cypher Explainer | `src/graph/neo4j/cypher_explainer.py` | Cypher → plain-English explanation with deterministic fallback (Phase 25.4) |
| Auth Service | `src/auth/service.py` | JWT auth, bcrypt hashing, user CRUD; `bump_password_version()`, `check_password_history()`, `record_password_history()`, `count_active_admins()` helpers (Phase 21 + 24.8) |
| Auth Dependencies | `src/auth/dependencies.py` | get_current_user, get_optional_user, require_admin; rejects stale `pv` JWT claim (Phase 21 + 24.8 token versioning) |
| Audit Logger | `src/auth/audit.py` | AuditLog model, never-raising log_action(), facets/count helpers (Phase 21 + 24.7) |
| Admin Users API | `src/api/endpoints/admin_users.py` | Operator-driven user CRUD; reset-password honours `AUTH_PASSWORD_RESET_MODE` (temp_password/reset_token/both); admin-quorum guard on demote/deactivate when `AUTH_REQUIRE_ADMIN_QUORUM=True` (Phase 24.7 + 24.8) |
| Auth Endpoints | `src/api/endpoints/auth.py` | login (with optional username lockout), register, logout (optional pv bump), `/me`, `/change-password`, `/redeem-reset` — password-history block on both change paths (Phase 21 + 24.8) |
| Rate Limit | `src/middleware/rate_limit.py` | Per-IP middleware, EndpointRateLimiter; Phase 24.8 adds `_UserKeyedRateLimiter` (change-password) + `LoginAttemptTracker` (per-username login lockout) |
| DML Generator | `src/dml/dml_generator.py` | Parameterized INSERT/UPDATE/DELETE generation (Phase 18) |
| DML Validator | `src/dml/dml_validator.py` | Safety checks, write permissions, row limits (Phase 18) |
| DML Executor | `src/dml/dml_executor.py` | Transaction-wrapped DML execution (Phase 18) |

### Data Flow
```
Natural Language Query → Auth Check (optional, REQUIRE_AUTH flag)
  → Input Sanitization → Injection Detection
  → Conversational Memory → Tool-Using Agent → Query Planning
  → [SQL Path] SQL Generator → Confidence Scorer → SQL Executor
      → Result Verification → [If Error: Parallel Corrections / Self-Correction Loop]
      → [If Success: Learn Pattern]
  → [NoSQL Path] NoSQL Router → Native Query Generator (MQL/CQL/PartiQL/DSL/Commands) → Executor
      → [If Error: Non-retryable check → Schema Hints → Correction Learner lookup
         → Confidence Scorer gate → Self-Correction Loop (up to 3 attempts)]
      → [If Success: Result Verification → Correction Learner persist]
  → Parallel Analysis (stats/anomalies/correlations)
  → Tiered Narrative Generation → Return Results
  → [Edit Mode] Inline Editing → Change Tracker → DML Generator → Validator
      → Preview → DML Executor (transaction-wrapped)
  → [Every Response] X-Request-ID echoed to client → Frontend axios interceptor
      captures request_id + traceparent → LastRequestBadge in header
  → [Admin Tab, gated by ADMIN_UI_ENABLED + is_admin]
      Users (list/create/role-toggle/disable/reset-password)
      Audit Log (filters: action/resource/user/date, JSON drawer)
      Health (live /health, recent queries, audit feed, observability gates,
              auth-hardening gates: token versioning / rate limit / lockout /
              reset mode / password history / admin quorum)
  → [Phase 24.8 Auth Hardening, all opt-in via AUTH_* flags]
      Login → optional username lockout → bcrypt → on success record_success()
      Change Password → per-user rate limit → reuse-history check → bcrypt
                      → record_password_history() → bump_password_version()
                      → fresh TokenResponse (caller stays signed in)
      Admin Reset → mode-conditional (temp_password | reset_token | both)
                  → bump_password_version() (kicks every prior session)
      Redeem Reset → /reset?token=... → bcrypt-walk outstanding tokens
                   → reuse-history check → mark used_at → fresh TokenResponse
      Admin demote/deactivate → optional quorum guard (block last admin)
      get_current_user → reject stale `pv` JWT claim (legacy tokens accepted)
```

### Detailed References
- **[.claude/AGENTS.md](.claude/AGENTS.md)** - All agents with methods and features
- **[.claude/ARCHITECTURE.md](.claude/ARCHITECTURE.md)** - Architectural patterns (pooling, caching, security)
- **[.claude/API.md](.claude/API.md)** - All API endpoints by category
- **[.claude/CODE_LOCATIONS.md](.claude/CODE_LOCATIONS.md)** - Quick lookup for key code locations
- **[.claude/FRONTEND.md](.claude/FRONTEND.md)** - Frontend components and structure

## Development Workflow

### Adding a New Feature
1. **Backend**: Add endpoint in `src/api/endpoints/`
2. **Database Models**: Add SQLAlchemy models in `src/database/models.py`
3. **Schemas**: Add Pydantic schemas in `src/models/schemas.py`
4. **Tests**: Add tests in `tests/`
5. **Frontend**: Add components in `frontend/src/components/`
6. **API Integration**: Update `frontend/src/services/api.ts`

### Testing Strategy
- Use `pytest` with async support (`pytest-asyncio`)
- Mock database connections with in-memory SQLite
- Mock LLM provider responses for deterministic tests
- Test markers: `@pytest.mark.asyncio`, `@pytest.mark.integration`, `@pytest.mark.slow`

### Common Issues
| Issue | Solution |
|-------|----------|
| Ollama Connection | Ensure `ollama serve` is running and model is pulled |
| Port Conflicts | Kill processes on ports 3000/8000 |
| Schema Issues | Check database connection is active |
| Async/Sync Mixing | DuckDB uses sync sessions, `SQLExecutor` handles both |
| Import Cycles | Import within functions if needed |

### Debugging Tips
- Backend logs to console and `backend.log`
- Use `logger.info()` for agent decisions
- Check `AgentTrace` in API responses
- Use `/api/docs` (Swagger UI) for API testing

## Configuration

Settings in `src/config/settings.py`:
- Environment variables from `.env` file
- Type-safe with Pydantic validation
- Supports multiple deployment environments
- Auth settings: `JWT_EXPIRATION_MINUTES` (default 1440), `REQUIRE_AUTH` (default False), `RATE_LIMIT_PER_USER` (200), `RATE_LIMIT_LLM_PER_USER` (30)
- LLM Provider settings: `DATA_SECURITY_LEVEL` (default `local_only`), per-provider `*_ENABLED`/`*_API_KEY`/`*_DEFAULT_MODEL` flags for OpenAI, Azure, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM
- Observability (Phase 24, all opt-in): `LOG_FORMAT` (default `console`, set to `json` in prod), `LOG_LEVEL`, `LOG_INCLUDE_REQUEST_ID` (default true), `LOG_INCLUDE_USER_ID` (default false), `METRICS_ENABLED` (false), `METRICS_EXPOSE_ENDPOINT` (false — gates `GET /metrics`), `OTEL_ENABLED` (false), `OTEL_EXPORTER_OTLP_ENDPOINT` (default `http://jaeger:4318`), `OTEL_SERVICE_NAME`, `OTEL_TRACES_SAMPLER_RATIO` (default 0.1)
- Admin & Observability UI (Phase 24.7): `ADMIN_UI_ENABLED` (default false — opt-in, matching `METRICS_ENABLED` / `OTEL_ENABLED`; when false the audit/admin-users routers aren't mounted and the frontend hides the Admin tab and Observability section), plus optional deep-link URLs surfaced to the UI: `JAEGER_UI_URL`, `GRAFANA_URL`, `METRICS_PUBLIC_URL` (browser-reachable URL for `/metrics`)
- Auth Hardening (Phase 24.8, all opt-in, validated by `Settings.check_auth_hardening()` at startup):
  - **Phase A** — `AUTH_TOKEN_VERSIONING_ENABLED` (false; stamps `pv` JWT claim, rejects stale), `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE` (false), `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` (false; logout kicks every device when on)
  - **Phase B** — `AUTH_RATE_LIMIT_CHANGE_PASSWORD` (false), `AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE` (5), `AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED` (false), `AUTH_LOGIN_LOCKOUT_THRESHOLD` (5), `AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS` (900)
  - **Phase C** — `AUTH_PASSWORD_RESET_MODE` (`temp_password` | `reset_token` | `both`; default `temp_password`), `AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES` (15), `AUTH_PASSWORD_RESET_BASE_URL` (used to build redemption links — startup warning if mode requires it but it's empty)
  - **Phase D1/D3** — `AUTH_PASSWORD_HISTORY_DEPTH` (0 = disabled; e.g. 5 to block reuse of last 5), `AUTH_REQUIRE_ADMIN_QUORUM` (false; blocks demoting/deactivating the last active admin)
  - All flags surface read-only via `/api/settings` and render in Admin → Health → Auth hardening so an operator can see live state. Phase D2 (JWT JTI denylist on logout) deferred — covered coarsely by `AUTH_INVALIDATE_TOKENS_ON_LOGOUT`; revisit when Redis is in the standard deploy story.
- Graph Mode (Phase 25, opt-in): `GRAPH_MODE_ENABLED` (default `False` — matches the project's opt-in feature-flag convention; when off, the `/graph` router and connection create/test endpoints return HTTP 400 for `database_type='neo4j'`), `GRAPH_DEFAULT_READ_ONLY` (default True), `GRAPH_QUERY_TIMEOUT_MS` (10_000), `GRAPH_INTROSPECTION_TIMEOUT_MS` (30_000), `GRAPH_INTROSPECTION_COUNT_CAP` (10_000_000), `GRAPH_MAX_RECORDS` (1000), `GRAPH_MAX_VIZ_NODES` (200), `GRAPH_MAX_VIZ_EDGES` (500), `GRAPH_ALLOW_APOC` (False — APOC procedures deny-by-default), `GRAPH_ALLOW_WRITES` (False)

## Documentation

Key docs in `docs/`:

| Category | Key Files |
|----------|-----------|
| **Guides** | `guides/MULTI_DATABASE_GUIDE.md`, `guides/CONNECTION_POOLING_GUIDE.md`, `guides/DATA_LINEAGE_GUIDE.md`, `guides/LINEAGE_INTELLIGENCE_USER_GUIDE.md`, `guides/FILE_DATA_SOURCE_USER_GUIDE.md` |
| **Technical** | `technical/PARALLEL_EXECUTION.md`, `technical/SEMANTIC_CACHING.md`, `technical/SQL_GENERATION_PIPELINE.md` |
| **Modules** | `modules/QUERY_PLANNING_AGENT.md`, `modules/TOOL_USING_AGENT.md` |
| **Testing** | `guides/testing/LINEAGE_INTELLIGENCE_TESTING.md`, `guides/testing/DATA_INSIGHTS_TESTING.md`, `guides/testing/PHASE_22_PERFORMANCE_GURU_TESTING.md`, `guides/testing/PHASE_14_NOSQL_EXPANSION_TESTING.md`, `guides/testing/PHASE_21_SECURITY_AUTH_TESTING.md`, `guides/testing/PHASE_15_LLM_PROVIDER_EXPANSION_TESTING.md`, `guides/testing/PHASE_17_MULTI_PROVIDER_MONITORING_TESTING.md`, `guides/testing/PHASE_24_OBSERVABILITY_TESTING.md`, `guides/testing/TESTING_GUIDE.md` |
| **Planning** | `planning/FUTURE_PLANS.md`, `planning/MASTER_ROADMAP.md` |
| **LLM Usage** | `guides/LLM_USAGE_MONITORING_GUIDE.md` |
| **Data Insights** | `planning/DATA_INSIGHTS_ENHANCEMENT_PLAN.md` |
| **Migration** | `planning/MIGRATION_TOOLKIT_PROPOSAL.md` |
| **Performance** | `guides/PERFORMANCE_GURU_GUIDE.md` |
| **NoSQL** | `planning/NOSQL_EXPANSION_PLAN.md` |
| **Security & Auth** | `planning/MASTER_ROADMAP.md` (Phase 21 section) |
| **Auth Hardening** | `planning/PASSWORD_AUTH_HARDENING_PLAN.md` (Phase 24.8 — token versioning, change-pwd rate limit, login lockout, one-shot reset tokens, password history, admin quorum; D2 deferred) |
| **Edit Mode & DML** | `planning/PHASE_18_EDIT_MODE_FEATURE_IMP_PLAN.md` |
| **LLM Providers** | `planning/LLM_PROVIDER_EXPANSION_PLAN.md` |
| **Deployment** | `guides/DOCKER_DEPLOYMENT_GUIDE.md`, `planning/DOCKER_CONTAINERIZATION_PLAN.md` |
| **Observability** | `guides/OBSERVABILITY_GUIDE.md` (Phase 24 — structlog, Prometheus `/metrics`, OpenTelemetry tracing, Docker `observability` profile; Phase 24.7 — Admin UI deep-links, Health sub-tab, request-id badge) |
| **Admin & Observability UI** | `planning/PHASE_24_Observability_&_Monitoring_UI_PLAN.md` (Phase 24.7 — trace-id surfacing, audit viewer, user CRUD, Health sub-tab, `ADMIN_UI_ENABLED` kill-switch) |
