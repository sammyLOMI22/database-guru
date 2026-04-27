# Database Guru - Master Development Roadmap

**Last Updated**: April 25, 2026
**Purpose**: Unified view of all planned features and their dependencies

---

## Visual Roadmap

```
                              DATABASE GURU - MASTER DEVELOPMENT ROADMAP
                              ==========================================

    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    COMPLETED FEATURES                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Parallel Multi-DB  │  │  Parallel Corrections │  │   Semantic Caching   │
    │   Execution (3x)     │  │   (1.6x speedup)     │  │   (50% hit rate)     │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Tool-Using Agent   │  │  Connection Pooling  │  │   Result Narrator    │
    │   (10 tools)         │  │   (30x faster)       │  │   (Advanced Analysis)│
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Chart Intelligence │  │   Advanced Charts    │  │   Query Compilation  │
    │   (Phase 8)          │  │   (Phase 10)         │  │   & Prepared Stmts   │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ IN REVIEW       │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Model Router       │  │   Query Templates    │  │   Prompt Optimizer   │
    │   (Per-task models)  │  │   (20% LLM bypass)   │  │   (40% token save)   │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Dialect Registry   │  │  Multi-DB Validator  │  │   ER Diagrams        │
    │   (DB-specific SQL)  │  │   (Pre-flight check) │  │   (Phase 7)          │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Data Lineage       │  │ Lineage Intelligence │  │  CSV/Excel Files     │
    │   (Phase 11)         │  │   (Phase 12)         │  │   (Phase 13)         │
    │   185 tests passing  │  │   151 tests passing  │  │   50+ tests passing  │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐
    │  CSV/Excel Files     │  │  LLM Usage Monitor   │
    │   (Phase 13)         │  │   (Phase 16)         │
    │   50+ tests passing  │  │   Token/cost tracking│
    │   ✅ COMPLETE        │  │   9 API endpoints    │
    │                      │  │   Full dashboard UI  │
    │                      │  │   ✅ COMPLETE        │
    └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    READY TO IMPLEMENT                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐
    │   Table Statistics   │  │   Column Resizing    │
    │   (Row counts, size) │  │   (Drag to resize)   │
    │   Est: ~280 lines    │  │   Est: ~300 lines    │
    │   Standalone         │  │   Enhancement        │
    └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                         NOSQL EXPANSION (Phase 14) - ✅ COMPLETE                        │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    NOSQL DATABASE SUPPORT (Phase 14) - ✅ COMPLETE                       │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
    │  │ 14.1 ✅     │   │ 14.2 ✅     │   │ 14.3 ✅     │   │ 14.4 ✅     │   │ 14.5 ✅     │ │
    │  │ MongoDB     │──▶│ Redis       │──▶│ Cassandra   │──▶│ DynamoDB    │──▶│ Elastic-    │ │
    │  │             │   │             │   │             │   │             │   │ search      │ │
    │  │ • MQL gen   │   │ • Commands  │   │ • CQL gen   │   │ • PartiQL   │   │ • Query DSL │ │
    │  │ • Aggreg.   │   │ • All data  │   │ • Partition │   │ • boto3 API │   │ • Aggreg.   │ │
    │  │ • Schema    │   │   types     │   │   aware     │   │ • GSI query │   │ • Search    │ │
    │  │   inference │   │ • RediSearch│   │ • Keyspaces │   │ • Cost est. │   │ • Highlight │ │
    │  │             │   │             │   │             │   │             │   │             │ │
    │  │ ~1,500 lines│   │ ~1,000 lines│   │ ~1,000 lines│   │ ~1,200 lines│   │ ~1,300 lines│ │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘ │
    │                                                                                           │
    │  Includes: Frontend connection modal (11 DB types), mixed SQL+NoSQL chat, schema          │
    │  introspection for all NoSQL types, self-correcting retry loops, 127 tests                │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    LLM PROVIDER EXPANSION (Phase 15) ✅ COMPLETE                        │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    MULTI-PROVIDER LLM SUPPORT (Phase 15) ✅ COMPLETE                     │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 15.1 Provider│   │ 15.2 OpenAI │   │ 15.3 Azure+ │   │ 15.4 Router │                  │
    │  │ Abstraction │──▶│ Compat      │──▶│ Anthropic   │──▶│ DB + API    │                   │
    │  │ ✅          │   │ ✅          │   │ ✅          │   │ ✅          │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                                     │
    │  │ 15.5 Vertex │   │ 15.6 Front- │   │ 15.7 Caller │                                    │
    │  │ + Bedrock   │──▶│ end UI      │──▶│ Migration   │                                    │
    │  │ ✅          │   │ ✅          │   │ ✅          │                                    │
    │  └─────────────┘   └─────────────┘   └─────────────┘                                     │
    │                                                                                           │
    │  8 providers: Ollama, OpenAI, Azure OpenAI, Anthropic, Vertex AI, Bedrock,               │
    │  LM Studio, vLLM. Data security enforcement (local/cloud_private/cloud_public).          │
    │  Frontend: Local/Frontier toggle, provider cards, per-task routing, model badges.         │
    │  220 tests | 8 API endpoints | ~4,000 lines                                              │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                         LLM USAGE MONITORING (Phase 16)                                 │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    LLM TOKEN USAGE MONITORING (Phase 16) - MEDIUM PRIORITY               │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 16.1 Core   │   │ 16.2 Agent  │   │ 16.3 Dash-  │   │ 16.4 Inline │                   │
    │  │ Infrastruc- │──▶│ Integration │──▶│ board       │──▶│ Chat Stats  │                   │
    │  │ ture        │   │             │   │ Frontend    │   │             │                   │
    │  │             │   │             │   │             │   │             │                   │
    │  │ • LLMUsage  │   │ • SQL Gen   │   │ • Stats     │   │ • Per-msg   │                   │
    │  │   table     │   │ • Narrator  │   │   cards     │   │   tokens    │                   │
    │  │ • Tracker   │   │ • Planning  │   │ • Charts    │   │ • Session   │                   │
    │  │   service   │   │ • Lineage   │   │ • Recent    │   │   totals    │                   │
    │  │ • API       │   │   agents    │   │   calls     │   │ • Agent     │                   │
    │  │             │   │             │   │             │   │   breakdown │                   │
    │  │ ~400 lines  │   │ ~300 lines  │   │ ~500 lines  │   │ ~300 lines  │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: MEDIUM | Est: 2 weeks | ~1,500 lines            │
    │  Plan: LLM_USAGE_MONITORING_PLAN.md                                                      │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                   MULTI-PROVIDER MONITORING (Phase 17) - ✅ COMPLETE                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │               MULTI-PROVIDER MONITORING (Phase 17) - ✅ COMPLETE                         │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 17.1 ✅     │   │ 17.2 ✅     │   │ 17.3 ✅     │   │ 17.4 ✅     │                   │
    │  │ Token       │──▶│ Provider    │──▶│ API &       │──▶│ Dashboard   │                   │
    │  │ Extractors  │   │ Updates     │   │ Schema      │   │ Widgets     │                   │
    │  │             │   │             │   │ Updates     │   │             │                   │
    │  │ • 6 provider│   │ • User-     │   │ • /cost-    │   │ • Cost by   │                   │
    │  │   formats   │   │   managed   │   │   summary   │   │   provider  │                   │
    │  │ • Vertex AI │   │   pricing   │   │ • /provider │   │ • Provider  │                   │
    │  │ • Bedrock   │   │ • Upsert/   │   │   -compare  │   │   compare   │                   │
    │  │ • LM Studio │   │   delete    │   │ • /model-   │   │ • Model     │                   │
    │  │ • vLLM      │   │   configs   │   │   configs   │   │   pricing   │                   │
    │  │ ~100 lines  │   │ ~200 lines  │   │ ~350 lines  │   │ ~450 lines  │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  29 tests | 7 new API endpoints | ~1,373 lines                                           │
    │  Plan: MULTI_PROVIDER_MONITORING_INTEGRATION.md                                          │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    DATA INSIGHTS ENHANCEMENT (Phase 19) - ✅ COMPLETE                   │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              DATA INSIGHTS ENHANCEMENT (Phase 19) - ✅ COMPLETE                          │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
    │  │ 19.1 Small  │   │ 19.2        │   │ 19.3 Multi- │   │ 19.4 Chart  │   │ 19.5        │ │
    │  │ Model       │──▶│ Analytics   │──▶│ Source      │──▶│ Intelligence│──▶│ Parallel    │ │
    │  │ Optimization│   │ Caching     │   │ Insights    │   │ Enhance     │   │ Analysis    │ │
    │  │ ✅          │   │ ✅          │   │ ✅          │   │ ✅          │   │ ✅          │ │
    │  │ • Tiered    │   │ • Stats     │   │ • Quality   │   │ • Adaptive  │   │ • Async     │ │
    │  │   prompts   │   │   cache     │   │   metrics   │   │   weights   │   │   analysis  │ │
    │  │ • Token     │   │ • Pattern   │   │ • Gap       │   │ • Smart     │   │ • Early     │ │
    │  │   budgets   │   │   cache     │   │   analysis  │   │   columns   │   │   exit      │ │
    │  │ • 40% save  │   │ • 24hr TTL  │   │ • Freshness │   │ • Context   │   │ • 30-40%    │ │
    │  │             │   │             │   │             │   │   insights  │   │   speedup   │ │
    │  │ ~400 lines  │   │ ~350 lines  │   │ ~450 lines  │   │ ~350 lines  │   │ ~250 lines  │ │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘ │
    │                                                                                           │
    │  108 tests (92 backend + 16 frontend) | ~1,800 lines                                    │
    │  Plan: DATA_INSIGHTS_ENHANCEMENT_PLAN.md                                                 │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    SECURITY & AUTH FOUNDATION (Phase 21) - ✅ COMPLETE                   │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              SECURITY & AUTH FOUNDATION (Phase 21) - ✅ COMPLETE                          │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 21.1 ✅     │   │ 21.2 ✅     │   │ 21.3 ✅     │   │ 21.4 ✅     │                   │
    │  │ User Auth   │──▶│ Resource    │──▶│ Per-User    │──▶│ Audit       │                   │
    │  │ (JWT)       │   │ Ownership   │   │ Rate Limit  │   │ Logging     │                   │
    │  │             │   │             │   │             │   │             │                   │
    │  │ • JWT auth  │   │ • owner_id  │   │ • Per-user  │   │ • Action    │                   │
    │  │ • Login/    │   │   FK on 5   │   │   limits    │   │   trail     │                   │
    │  │   register  │   │   tables    │   │ • JWT-based │   │ • Never-    │                   │
    │  │ • bcrypt    │   │ • 403 on    │   │   user ID   │   │   raising   │                   │
    │  │   hashing   │   │   unauth'd  │   │   extraction│   │   log_action│                   │
    │  │ • Feature   │   │   access    │   │ • IP        │   │ • Admin +   │                   │
    │  │   flag      │   │ • Filtering │   │   fallback  │   │   user logs │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  61 tests | 3 Alembic migrations | REQUIRE_AUTH feature flag for gradual rollout          │
    │  UNBLOCKS: Phase 18 (Edit Mode), Phase 15 (Enterprise LLMs)                              │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    MIGRATION TOOLKIT (Phase 20) - ✅ COMPLETE                            │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              DATABASE MIGRATION TOOLKIT (Phase 20) - ✅ COMPLETE                          │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 20.1 Schema │   │ 20.2 Migr.  │   │ 20.3 Script │   │ 20.4 Data   │                   │
    │  │ Diff Engine │──▶│ Planner     │──▶│ Generator   │──▶│ Migration   │                   │
    │  │ ✅          │   │ ✅          │   │ ✅          │   │ ✅          │                   │
    │  │ • Visual    │   │ • Dependency│   │ • up.sql    │   │ • Staging   │                   │
    │  │   diff      │   │   ordering  │   │ • down.sql  │   │   table     │                   │
    │  │ • Drift     │   │ • Data loss │   │ • verify.sql│   │   pattern   │                   │
    │  │   analysis  │   │   detection │   │ • Multi-    │   │ • Batching  │                   │
    │  │ • DB vs DB  │   │ • Lock      │   │   dialect   │   │ • Validate  │                   │
    │  │ • Topo sort │   │   awareness │   │ • SQLite    │   │   queries   │                   │
    │  │   w/ FKs    │   │ • LLM intent│   │   recreate  │   │             │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  98 migration-related tests | ~5,676 lines | 13 API endpoints                            │
    │  Plan: MIGRATION_TOOLKIT_PROPOSAL.md                                                     │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    PERFORMANCE GURU (Phase 22) - ✅ COMPLETE                            │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    DEEP EXPLAIN ANALYSIS (Phase 22) - ✅ COMPLETE                        │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                                     │
    │  │ 22.1 ✅     │   │ 22.2 ✅     │   │ 22.3 ✅     │                                     │
    │  │ Explain     │──▶│ LLM        │──▶│ Action      │                                     │
    │  │ Analyzer    │   │ Interpreter│   │ Advisor     │                                     │
    │  │ • EXPLAIN   │   │ • Parse JSON│   │ • Index     │                                     │
    │  │   ANALYZE   │   │   plans     │   │   suggest   │                                     │
    │  │ • Multi-    │   │ • Identify  │   │ • Rewrite   │                                     │
    │  │   dialect   │   │   bottleneck│   │   advice    │                                     │
    │  │ • Cost model│   │ • Disk spill│   │ • Before/   │                                     │
    │  │             │   │   detection │   │   after est │                                     │
    │  │ ~500 lines  │   │ ~400 lines  │   │ ~400 lines  │                                     │
    │  └─────────────┘   └─────────────┘   └─────────────┘                                     │
    │                                                                                           │
    │  77 tests | 2 API endpoints | ~3,282 lines                                               │
    │  Source: FEATURE_SUGGESTIONS_BRAINSTORM.md                                               │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    DOCKER CONTAINERIZATION (Phase 23) - ✅ COMPLETE                     │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              DOCKER / "RUN ANYWHERE" (Phase 23) - ✅ COMPLETE                            │
    │                                                                                           │
    │  `docker compose up` → app on localhost:3000 — BYO LLM, files, data sources              │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ Backend     │   │ Frontend    │   │ Compose     │   │ Profiles    │                   │
    │  │ Dockerfile  │   │ Dockerfile  │   │ Orchestr.   │   │             │                   │
    │  │ ✅          │   │ ✅          │   │ ✅          │   │ ✅          │                   │
    │  │ • Multi-    │   │ • Node build│   │ • backend + │   │ • ollama    │                   │
    │  │   stage     │   │ • Nginx     │   │   frontend  │   │   (bundled  │                   │
    │  │ • Alembic   │   │   reverse   │   │ • Volumes:  │   │   w/ GPU)   │                   │
    │  │   auto-     │   │   proxy     │   │   data, up- │   │ • full      │                   │
    │  │   migrate   │   │ • Non-root  │   │   loads,logs│   │   (Postgres │                   │
    │  │ • curl      │   │ • CSP hdrs  │   │ • Healthchk │   │   + Redis)  │                   │
    │  │   health    │   │ • Asset     │   │ • Least-priv│   │             │                   │
    │  │ • Retry     │   │   caching   │   │   DB user   │   │ Combinable: │                   │
    │  │   logic     │   │             │   │ • Security  │   │ --profile   │                   │
    │  │             │   │             │   │   hardened  │   │ ollama full │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Also delivered: Ollama retry logic (tenacity), prompts refactoring,                     │
    │  CTE support in lineage parser, Postgres least-privilege init script                     │
    │                                                                                           │
    │  Plan: DOCKER_CONTAINERIZATION_PLAN.md | Guide: DOCKER_DEPLOYMENT_GUIDE.md              │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    OBSERVABILITY & MONITORING (Phase 24) ✅ COMPLETE                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              OBSERVABILITY STACK (Phase 24) ✅ COMPLETE                                  │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 24.1 Struct-│   │ 24.2 Metrics│   │ 24.3 Open-  │   │ 24.4 Docker │                   │
    │  │ ured Logging│──▶│ + /metrics  │──▶│ Telemetry   │──▶│ Profile     │                   │
    │  │             │   │             │   │ Tracing     │   │             │                   │
    │  │ • structlog │   │ • Prometheus│   │ • OTEL SDK  │   │ • Compose   │                   │
    │  │   JSON      │   │   collectors│   │ • OTLP HTTP │   │   profile   │                   │
    │  │ • request_id│   │ • Bounded   │   │ • Auto-     │   │ • Jaeger    │                   │
    │  │ • redaction │   │   labels    │   │   instrument│   │ • Prometheus│                   │
    │  │ • stdout    │   │ • /metrics  │   │ • LLM +     │   │ • Grafana   │                   │
    │  │   only      │   │   gated     │   │   agent     │   │   provisioned│                  │
    │  │             │   │             │   │   spans     │   │   dashboard │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: Phase 23 ✅ (Docker) | Status: ✅ Complete | Stdout JSON only (no aggregator)  │
    │  Guide: OBSERVABILITY_GUIDE.md | Test guide: PHASE_24_OBSERVABILITY_TESTING.md          │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │              ADMIN & OBSERVABILITY UI (Phase 24.7) ✅ COMPLETE                          │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              UI INTEGRATION GAPS (Phase 24.7) ✅ COMPLETE — Apr 25, 2026                 │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ PR1: Trace- │   │ PR2: Audit  │   │ PR3: Health │   │ PR4: User   │                   │
    │  │ ID Header   │──▶│ Log Viewer  │──▶│ Sub-Tab +   │──▶│ Management  │                   │
    │  │ + Axios     │   │ + Admin Tab │   │ Deep-links  │   │ CRUD        │                   │
    │  │ Interceptor │   │             │   │             │   │             │                   │
    │  │             │   │ • paginated │   │ • Prometheus│   │ • list/create│                  │
    │  │ • zustand   │   │ • filters   │   │   /Jaeger/  │   │ • role toggl│                   │
    │  │   store     │   │ • JSON      │   │   Grafana   │   │ • disable   │                   │
    │  │ • header    │   │   drawer    │   │   deep-links│   │ • reset pwd │                   │
    │  │   badge     │   │ • facets    │   │ • /health   │   │ • audit-log │                   │
    │  │ • copy id   │   │   endpoint  │   │   cards     │   │   side-eff  │                   │
    │  │             │   │             │   │ • obs gates │   │ • self-lock │                   │
    │  │             │   │             │   │ • last-req  │   │   protection│                   │
    │  │             │   │             │   │   widget    │   │             │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Plus: removed mock data (1,133 LOC ObservabilityDemo.tsx), introduced ADMIN_UI_ENABLED   │
    │  kill-switch (gates router mounting + frontend tab/section rendering), exposed            │
    │  observability config via /api/settings (jaeger_ui_url, grafana_url, metrics_public_url,  │
    │  metrics_enabled, metrics_endpoint_exposed, otel_enabled, otel_service_name,              │
    │  otel_traces_sampler_ratio, admin_ui_enabled).                                            │
    │                                                                                           │
    │  Prereq: Phase 21 ✅ (Auth+Audit), Phase 24 ✅ (Observability backend)                   │
    │  Plan: PHASE_24_Observability_&_Monitoring_UI_PLAN.md                                    │
    │  Tests: tests/test_admin_users_endpoints.py (320), tests/test_audit_endpoints.py (237),   │
    │         tests/test_admin_ui_toggle.py (35), tests/test_settings_observability.py (163)    │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              AUTH HARDENING (Phase 24.8) ✅ A/B/C/D1/D3 — Apr 26, 2026                   │
    │                                                                                           │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
    │  │ Phase A      │  │ Phase B      │  │ Phase C      │  │ Phase D1+D3  │                   │
    │  │ Token        │  │ Rate limit + │  │ One-shot     │  │ Pwd history  │                   │
    │  │ versioning   │  │ login lockout│  │ reset tokens │  │ + Admin       │                   │
    │  │              │  │              │  │              │  │ quorum       │                   │
    │  │ • password_  │  │ • per-user   │  │ • password_  │  │ • last-N hash│                   │
    │  │   version    │  │   change-pwd │  │   reset_     │  │   reuse block│                   │
    │  │   column     │  │   limiter    │  │   tokens     │  │ • depth-     │                   │
    │  │ • pv claim   │  │ • per-user   │  │   table      │  │   bounded    │                   │
    │  │   in JWT     │  │   login      │  │ • redeem     │  │ • no-quorum  │                   │
    │  │ • bumps on   │  │   lockout    │  │   endpoint   │  │   guard:     │                   │
    │  │   change/    │  │   tracker    │  │ • mode flag  │  │   block last │                   │
    │  │   reset      │  │ • case-      │  │   3-way      │  │   admin      │                   │
    │  │ • opt-in     │  │   insensitive│  │   (temp/     │  │   demote/    │                   │
    │  │   logout/    │  │ • account_   │  │   token/     │  │   deactivate │                   │
    │  │   deactivate │  │   locked     │  │   both)      │  │              │                   │
    │  │   triggers   │  │   audit log  │  │ • frontend   │  │              │                   │
    │  │              │  │              │  │   /reset?token│ │              │                   │
    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘                   │
    │                                                                                           │
    │  All toggles default OFF (behavior-preserving on upgrade). Surfaced read-only in           │
    │  Admin → Health → Auth hardening so operators can see live state.                          │
    │                                                                                           │
    │  Migrations: 3d8f4c2a1e9b (must_change_password), 4f9a1c8b2e3d (password_version),         │
    │              5e2b7a9d4c8f (password_reset_tokens), 6a3c5f8e7b1d (password_history)         │
    │  New endpoints: POST /api/auth/change-password, POST /api/auth/redeem-reset                │
    │  Tests: test_auth_change_password.py (4), test_auth_token_versioning.py (7),               │
    │         test_auth_rate_limit.py (8), test_auth_reset_tokens.py (9),                        │
    │         test_auth_history_and_quorum.py (9), test_settings_auth_hardening.py (7)           │
    │  Plan: PASSWORD_AUTH_HARDENING_PLAN.md                                                    │
    │                                                                                           │
    │  ⏳ Phase D2 (JWT JTI denylist on logout) — DEFERRED, requires Redis                      │
    │     Phase A's AUTH_INVALIDATE_TOKENS_ON_LOGOUT covers the coarse use case (kicks all       │
    │     devices). D2 only matters when per-session revocation is needed AND multi-device       │
    │     hygiene matters more than the simplicity of the version-bump approach. Slot it in     │
    │     once REDIS_URL is part of the standard deploy story (Phase 23 full profile).          │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                              INNOVATION PIPELINE (Future)                                │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Synthetic Data     │  │   API-ify            │  │   Auto-Documentation │
    │   Generator          │  │   (Query→Endpoint)   │  │   Site               │
    │                      │  │                      │  │                      │
    │  • Schema-aware      │  │  • One-click API     │  │  • Static site gen   │
    │  • FK-ordered inserts│  │  • FastAPI route gen  │  │  • AI column descs   │
    │  • faker integration │  │  • Swagger/OpenAPI   │  │  • Embed ER + lineage│
    │  • Distribution match│  │  • Parameterized     │  │  • Sample queries    │
    │                      │  │                      │  │                      │
    │  Priority: MEDIUM    │  │  Priority: MEDIUM    │  │  Priority: LOW       │
    │  Source: Brainstorm  │  │  Source: Brainstorm   │  │  Source: Brainstorm  │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Watchdog Agents    │  │   Business Glossary  │  │   Guru API           │
    │   (Scheduled Queries)│  │   (Term Definitions) │  │   (External Access)  │
    │                      │  │                      │  │                      │
    │  • Cron-style runs   │  │  • Define "Churn",   │  │  • REST/Webhook API  │
    │  • Anomaly alerting  │  │    "Active User" etc │  │  • Slack bot integr. │
    │  • Threshold triggers│  │  • Consistent LLM    │  │  • JSON/Markdown     │
    │  • Shifts from       │  │    definitions       │  │    responses         │
    │    "Tool" to "Mate"  │  │  • Cross-query reuse │  │  • Dashboard embed   │
    │                      │  │                      │  │                      │
    │  Priority: MEDIUM    │  │  Priority: MEDIUM    │  │  Priority: MEDIUM    │
    │  Source: PM Feedback  │  │  Source: PM Feedback  │  │  Source: PM+Brainstm │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐
    │   Webhook Sources    │  │   Metric Trees       │
    │   (JSON URL→Table)   │  │   (Auto-Breakdown)   │
    │                      │  │                      │
    │  • DuckDB http scan  │  │  • Revenue→Region→   │
    │  • REST endpoint as  │  │    Product drill-down│
    │    virtual table     │  │  • Auto-decompose    │
    │  • Refresh on query  │  │    metrics           │
    │                      │  │                      │
    │  Priority: LOW       │  │  Priority: MEDIUM    │
    │  Source: PM Feedback  │  │  Source: PM Feedback  │
    └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                              INSIGHT QUALITY IMPROVEMENTS                                │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │  Advanced Preprocess │──────▶│   Pattern Learning   │──────▶│   Model Performance  │
    │  (Phase 2.3)         │       │   (Phase 2.6)        │       │   Tracker            │
    │                      │       │                      │       │                      │
    │  • Date normalization│       │  • Learn from success│       │  • Track accuracy    │
    │  • Boolean handling  │       │  • Auto-templates    │       │  • Auto model select │
    │  • Status values     │       │  • Pattern matching  │       │  • Performance stats │
    │                      │       │                      │       │                      │
    │  NOT STARTED         │       │  NOT STARTED         │       │  NOT STARTED         │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    TABLE IMPROVEMENTS                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │   Table Sorting      │       │   Column Resizing    │       │   Export Options     │
    │   (Quick Win)        │       │   (Enhancement)      │       │   (CSV, Excel, JSON) │
    │                      │       │                      │       │                      │
    │  • Click column head │       │  • Drag to resize    │       │  • Multiple formats  │
    │  • Asc/Desc toggle   │       │  • Persist widths    │       │  • Filtered export   │
    │  • Smart type sort   │       │  • Auto-fit option   │       │  • Streaming export  │
    │                      │       │                      │       │                      │
    │  ✅ COMPLETE         │       │  NOT STARTED         │       │  NOT STARTED         │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                      EDIT MODE & DML (Phase 18) - ✅ COMPLETE                            │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              EDIT MODE & DML OPERATIONS (Phase 18) - ✅ COMPLETE                          │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                                     │
    │  │ 18.1 ✅     │   │ 18.2 ✅     │   │ 18.3 ✅     │                                     │
    │  │ Core        │──▶│ API &       │──▶│ Inline      │                                     │
    │  │ Backend     │   │ Execution   │   │ Editing UI  │                                     │
    │  │             │   │             │   │             │                                     │
    │  │ • DML       │   │ • 5 REST    │   │ • Editable  │                                     │
    │  │   generator │   │   endpoints │   │   cells     │                                     │
    │  │ • DML       │   │ • Preview   │   │ • Add row   │                                     │
    │  │   validator │   │   mode      │   │ • Delete    │                                     │
    │  │ • DML       │   │ • Execute   │   │   confirm   │                                     │
    │  │   executor  │   │   w/ Tx     │   │ • Changes   │                                     │
    │  │ • Change    │   │ • Write     │   │   summary   │                                     │
    │  │   tracker   │   │   perms     │   │ • DML       │                                     │
    │  │             │   │ • Table     │   │   preview   │                                     │
    │  │             │   │   info      │   │             │                                     │
    │  │ ~640 lines  │   │ ~320 lines  │   │ ~1,070 lines│                                     │
    │  └─────────────┘   └─────────────┘   └─────────────┘                                     │
    │                                                                                           │
    │  40 tests | 5 API endpoints | ~2,450 lines (backend + frontend)                         │
    │  Per-connection write permissions (INSERT/UPDATE/DELETE toggles)                          │
    │  Plan: PHASE_18_EDIT_MODE_FEATURE_IMP_PLAN.md                                            │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                                      FUTURE PHASES                                       │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
    │   Streaming Results  │       │   Query Suggestions  │       │   Collaborative      │
    │   (SSE)              │       │   (AI-powered)       │       │   Features           │
    │                      │       │                      │       │                      │
    │  • Real-time stream  │       │  • Schema-aware      │       │  • Share sessions    │
    │  • Progressive render│       │  • History-based     │       │  • Team queries      │
    │  • Large dataset UX  │       │  • Autocomplete      │       │  • Templates library │
    │                      │       │                      │       │                      │
    │  Priority: MEDIUM    │       │  Priority: LOW       │       │  Priority: LOW       │
    └──────────────────────┘       └──────────────────────┘       └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                               DEFERRED CHART COMPONENTS                                  │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Sankey Diagram     │  │   Violin Plot        │  │   Sparklines         │
    │   (Flow data)        │  │   (Distribution)     │  │   (Inline mini)      │
    │   Needs: d3-sankey   │  │   Complex: KDE calc  │  │   Lower priority     │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    SECURITY & INFRASTRUCTURE - ✅ DELIVERED                                │
    │         Phase 21 + Phase 18 + Phase 15 + Phase 17 complete                                │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Authorization      │  │   Session Expiration │  │   Rate Limiting      │
    │   System             │  │   (TTL, cleanup)     │  │   (Per-user)         │
    │   ✅ Phase 21        │  │   Remaining item     │  │   ✅ Phase 21        │
    │   JWT + ownership    │  │   Can bundle w/ P18  │  │   Per-user + IP      │
    └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

---

## Dependency Graph

```
                                    FEATURE DEPENDENCIES
                                    ====================

    ┌───────────────────────────────────────────────────────────────┐
    │           DATA LINEAGE (Phase 11) - COMPLETE ✅               │
    │                                                               │
    │  11.1 Backend Core ✅    11.2 Frontend Core ✅                │
    │  11.3 Column Lineage ✅  11.4 ER Extensions ✅                │
    │  11.5 Query Patterns ✅  11.6 Polish & Testing ✅             │
    │                                                               │
    │  185 tests (116 backend + 69 frontend)                        │
    └───────────────────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │        LINEAGE INTELLIGENCE (Phase 12) - COMPLETE ✅            │
    │                     LLM-Powered Features                         │
    │                                                                  │
    │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │  │ 12.1 ✅ │──▶│ 12.2 ✅ │──▶│ 12.3 ✅ │──▶│ 12.4 ✅ │──▶│ 12.5 ✅ │
    │  │ Lineage │   │ Impact  │   │ Schema  │   │ Pattern │   │ Lineage │
    │  │ Narrator│   │ Advisor │   │ Health  │   │ Intel.  │   │ Chat    │
    │  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
    │                                                                  │
    │  151 tests | ~11,266 lines | 5 LLM agents                        │
    └─────────────────────────────────────────────────────────────────┘


    COMPLETED:
    =========

    ┌───────────────────────────────────────────────────────────────────┐
    │        CSV & EXCEL FILE SUPPORT (Phase 13) ✅ COMPLETE            │
    │  • 50+ tests passing | Plan: CSV_EXCEL_SUPPORT_PLAN.md           │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        LLM USAGE MONITORING (Phase 16) ✅ COMPLETE                │
    │  • 9 API endpoints, full dashboard | Plan: LLM_USAGE_MONITORING  │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        DOCKER CONTAINERIZATION (Phase 23) ✅ COMPLETE             │
    │  • Docker Compose profiles, Nginx proxy, security hardened       │
    │  • Least-privilege Postgres, Ollama retry, CTE lineage support   │
    │  • Guide: DOCKER_DEPLOYMENT_GUIDE.md                             │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        DATA INSIGHTS ENHANCEMENT (Phase 19) ✅ COMPLETE          │
    │  • Tiered narratives, analytics cache, multi-source quality      │
    │  • Chart intelligence presets, parallel analysis pipeline         │
    │  • 108 tests (92 backend + 16 frontend)                          │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        DATABASE MIGRATION TOOLKIT (Phase 20) ✅ COMPLETE         │
    │  • Schema diff, migration planner, script generator, data migr.  │
    │  • Topo sort with FKs, SQLite recreate, staging table pattern    │
    │  • 98 tests | 13 API endpoints | ~5,676 lines                    │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        PERFORMANCE GURU (Phase 22) ✅ COMPLETE                    │
    │  • EXPLAIN plan parser (PG, MySQL, SQLite, DuckDB)               │
    │  • LLM-powered interpretation with tiered prompts + fallback     │
    │  • Index suggestions, query rewrites, bottleneck detection        │
    │  • 77 tests | 2 API endpoints | ~3,282 lines                     │
    └───────────────────────────────────────────────────────────────────┘


    INDEPENDENT FEATURES (Can Start Anytime):
    =========================================

    ┌───────────────────────────────────────────────────────────────────┐
    │   SECURITY & AUTH FOUNDATION (Phase 21) ◀── ✅ COMPLETE          │
    │                                                                   │
    │  UNBLOCKS: Phase 18 ✅ (Edit Mode) + Phase 15 ✅ (Enterprise LLMs)│
    │                                                                   │
    │  • JWT auth (bcrypt, python-jose) + resource ownership            │
    │  • Per-user rate limiting + audit logging                         │
    │  • REQUIRE_AUTH feature flag for gradual rollout                  │
    │  • 61 tests | 3 Alembic migrations                               │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        LLM PROVIDER EXPANSION (Phase 15) ◀── ✅ COMPLETE          │
    │                                                                   │
    │  • 8 providers: Ollama, OpenAI, Azure OpenAI, Anthropic,          │
    │    Vertex AI, Bedrock, LM Studio, vLLM                            │
    │  • Provider abstraction (BaseLLMProvider ABC + TrackedLLMClient)   │
    │  • ProviderRegistry with data security enforcement                │
    │  • Local/Frontier toggle UI, per-task routing, fallback chains     │
    │  • Fernet-encrypted API key storage, provider health checks       │
    │  • Frontend: provider cards, config modals, model locality badges │
    │  • 220 tests | 8 API endpoints | ~4,000 lines                     │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        NOSQL DATABASE EXPANSION (Phase 14) ◀── ✅ COMPLETE        │
    │                                                                   │
    │  • MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch             │
    │  • Native query gen, schema inference, error classification       │
    │  • Frontend: 11 DB types, conditional forms, mixed chat sessions  │
    │  • 127 tests | Plan: NOSQL_EXPANSION_PLAN.md                      │
    └───────────────────────────────────────────────────────────────────┘


    DEPENDENT FEATURES (Requires Prerequisites):
    ============================================

    ┌───────────────────────────────────────────────────────────────────┐
    │   EDIT MODE & DML (Phase 18) ◀── ✅ COMPLETE                        │
    │                                                                   │
    │   REQUIRES: Phase 21 ✅ (Security & Auth) — DELIVERED              │
    │                                                                   │
    │  • DML generator/validator/executor, inline editing UI            │
    │  • Preview mode, per-connection write permissions                 │
    │  • 40 tests | 5 API endpoints | ~2,450 lines                     │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │   MULTI-PROVIDER MONITORING (Phase 17) ✅ COMPLETE                 │
    │                                                                   │
    │   REQUIRES: Phase 15 ✅ (Providers) + Phase 16 ✅ (Monitoring)    │
    │                                                                   │
    │  • Native tokens from 6 providers (Ollama, OpenAI, Anthropic,     │
    │    Azure, Google Vertex, AWS Bedrock, LM Studio, vLLM)            │
    │  • User-managed model pricing (CRUD admin API)                    │
    │  • Cost summary, provider comparison, unpriced model detection    │
    │  • Model pricing manager UI, cost-by-provider chart               │
    │  • 29 tests | 7 new endpoints | ~1,373 lines                     │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │   MIGRATION TOOLKIT (Phase 20) ✅ COMPLETE                        │
    │                                                                   │
    │   REQUIRES: Phase 11 ✅ (Lineage) + Phase 12 ✅ (Intelligence)    │
    │                                                                   │
    │  • Schema Diff (visual DB-to-DB comparison)                       │
    │  • Migration Planner (dependency-aware, topo sort with FKs)       │
    │  • Script Generator (up.sql / down.sql / verify.sql, SQLite)      │
    │  • Data Migration Assistant (staging table pattern, batching)     │
    │  • 98 tests | 13 API endpoints | ~5,676 lines                    │
    └───────────────────────────────────────────────────────────────────┘

            ┌─────────────────┐          ┌─────────────────┐
            │   Phase 15 ✅   │          │   Phase 16 ✅   │
            │   Provider      │          │   Usage         │
            │   Expansion     │          │   Monitoring    │
            └────────┬────────┘          └────────┬────────┘
                     │                            │
                     └──────────┬─────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │     Phase 17 ✅     │
                     │   Multi-Provider    │
                     │     Monitoring      │
                     └─────────────────────┘

            ┌─────────────────┐
            │   Phase 21 ✅   │
            │   Security &    │
            │   Auth          │
            └────────┬────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
    ┌─────────────┐  ┌─────────────┐
    │  Phase 18 ✅│  │  Phase 15 ✅│
    │  Edit Mode  │  │  LLM Provs  │
    │  & DML      │  │  (cost ctrl)│
    └─────────────┘  └─────────────┘

    ┌─────────────────┐   ┌─────────────────┐
    │ Phase 11 ✅     │   │ Phase 12 ✅     │
    │ Lineage         │   │ Intelligence    │
    └────────┬────────┘   └────────┬────────┘
             │                     │
             └──────────┬──────────┘
                        ▼
              ┌─────────────────┐
              │   Phase 20 ✅   │
              │   Migration     │
              │   Toolkit       │
              └─────────────────┘


    OTHER INDEPENDENT FEATURES:
    ===========================

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Table Sorting ✅ │  │  Column Resizing  │  │  Export Options   │
    └───────────────────┘  └───────────────────┘  └───────────────────┘

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Streaming Results│  │  Advanced         │  │  Pattern Learning │
    └───────────────────┘  │  Preprocessing    │  │  (Phase 2.6)      │
                           │  (Phase 2.3)      │  └───────────────────┘
                           └───────────────────┘


    INNOVATION PIPELINE (Ideas for Evaluation):
    ============================================

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Synthetic Data   │  │  API-ify          │  │  Auto-Docs Site   │
    │  Generator        │  │  (Query→Endpoint) │  │  (MkDocs/Docusaur)│
    └───────────────────┘  └───────────────────┘  └───────────────────┘

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Watchdog Agents  │  │  Business Glossary│  │  Guru API         │
    │  (Scheduled Runs) │  │  (Term Defs)      │  │  (Slack/Ext API)  │
    └───────────────────┘  └───────────────────┘  └───────────────────┘

    ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
    │  Webhook Sources  │  │  Metric Trees     │  │  Shared Workspaces│
    │  (JSON URL→Table) │  │  (Auto-Breakdown) │  │  (Read-only share)│
    └───────────────────┘  └───────────────────┘  └───────────────────┘
```

---

## Recommended Next Steps (Updated April 25, 2026)

> **Strategic Direction** (per PM Review): Focus on "depth and safety" before "width expansion".
> Security/Auth, Edit Mode, Enterprise LLMs, Multi-Provider Monitoring, Observability backend, and the operator-facing Admin/Observability UI are now complete.

### Completed Priorities (this cycle)
- ~~Auth Hardening (Phase 24.8)~~ - ✅ COMPLETE for Phases A/B/C/D1/D3 (Apr 26, 2026): **Phase A** token versioning (`users.password_version` column, `pv` JWT claim, evicts every outstanding session on password change/admin reset, optional triggers for logout/deactivate). **Phase B** per-user change-password rate limit + per-username login lockout (case-insensitive, account_locked/account_unlocked audit events). **Phase C** one-shot password reset tokens (new `password_reset_tokens` table, `AUTH_PASSWORD_RESET_MODE` 3-way switch, `POST /api/auth/redeem-reset` endpoint, frontend `/reset?token=…` redemption screen, conditional admin reset modal). **Phase D1** password history (`password_history` table, depth-bounded reuse rejection). **Phase D3** admin quorum guard (refuses to demote/deactivate the last active admin). All 13 toggles default OFF, surfaced read-only in Admin → Health → Auth hardening. 4 migrations (`3d8f4c2a1e9b`, `4f9a1c8b2e3d`, `5e2b7a9d4c8f`, `6a3c5f8e7b1d`), 2 new endpoints (`/api/auth/change-password`, `/api/auth/redeem-reset`), 44 new tests across 6 files. **Phase D2 (JTI denylist) deferred** — covered coarsely by `AUTH_INVALIDATE_TOKENS_ON_LOGOUT`; revisit when Redis is part of the standard deploy story. Plan: `PASSWORD_AUTH_HARDENING_PLAN.md`.
- ~~Admin & Observability UI (Phase 24.7)~~ - ✅ COMPLETE: Trace-id badge in header (axios interceptor + zustand `lastRequestStore`), AuditLogViewer with server-side filters/pagination/JSON drawer + `/api/audit/facets`, UserManagement CRUD (list/create/role-toggle/disable/reset-password) with audit-log side-effects and self-lockout protection, SystemHealthPanel sub-tab replacing the 1,133-LOC `ObservabilityDemo.tsx` mock (live `/health`, recent queries, recent audit, observability gates, last-request widget), Settings → Observability section with Prometheus/Jaeger/Grafana deep-links, hard `ADMIN_UI_ENABLED` kill-switch (router mount + frontend tab/section gating). New endpoints: 5 under `/api/admin/users`, 3 under `/api/audit`. New tests: `test_admin_users_endpoints.py` (320 LOC), `test_audit_endpoints.py` (237 LOC), `test_admin_ui_toggle.py` (35 LOC), `test_settings_observability.py` (163 LOC). Plan: `PHASE_24_Observability_&_Monitoring_UI_PLAN.md`.
- ~~Observability & Monitoring (Phase 24)~~ - ✅ COMPLETE: structlog JSON logs with request_id propagation + sensitive-key redaction, Prometheus collectors (`dbguru_*`) for HTTP/LLM/SQL/pool/cache with bounded labels, gated `/metrics` endpoint, OpenTelemetry SDK + OTLP HTTP exporter with auto-instrumentation (FastAPI/SQLAlchemy/HTTPX/Redis), manual `llm.call` and `agent.self_correcting` spans reusing LLMUsageTracker values, Docker `observability` profile (Jaeger/Prometheus/Grafana with provisioned dashboard + alert rules). 17 tests, ~1,300 lines. Stdout JSON only — no log aggregator in scope.
- ~~Multi-Provider Monitoring (Phase 17)~~ - ✅ COMPLETE: Native token extraction for 6 provider formats (Ollama, OpenAI/Azure/LM Studio/vLLM, Anthropic, Google Vertex, AWS Bedrock), user-managed model pricing (CRUD admin API), cost summary with daily breakdown, provider performance comparison by agent type, unpriced model detection, ModelPricingManager UI. 29 tests, 7 new endpoints, ~1,373 lines.
- ~~LLM Provider Expansion (Phase 15)~~ - ✅ COMPLETE: 8 providers (Ollama, OpenAI, Azure OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM), provider abstraction + registry, data security enforcement (local/cloud_private/cloud_public), Local/Frontier toggle UI, per-task routing, fallback chains, Fernet-encrypted API keys, frontend provider management. 220 tests, 8 endpoints, ~4,000 lines.
- ~~Edit Mode & DML (Phase 18)~~ - ✅ COMPLETE: DML generator/validator/executor, inline editing UI, per-connection write permissions, preview mode. 40 tests, 5 endpoints, ~2,450 lines.
- ~~Security & Auth Foundation (Phase 21)~~ - ✅ COMPLETE: JWT auth, resource ownership, per-user rate limiting, audit logging. 61 tests, 3 migrations. Unblocks Phase 18 + Phase 15.
- ~~Migration Toolkit (Phase 20)~~ - ✅ COMPLETE: Schema diff, migration planner, script gen, data migration. 98 tests, 13 endpoints, ~5,676 lines.
- ~~Performance Guru (Phase 22)~~ - ✅ COMPLETE: EXPLAIN analysis, LLM interpretation, index suggestions, 4 dialects. 77 tests, 2 endpoints, ~3,282 lines.
- ~~Data Insights Enhancement (Phase 19)~~ - ✅ COMPLETE: Tiered narratives, analytics cache, parallel analysis. 108 tests.

### Innovation Pipeline (Future evaluation)
Ideas from [FEATURE_SUGGESTIONS_BRAINSTORM.md](FEATURE_SUGGESTIONS_BRAINSTORM.md) and [ROADMAP_FEEDBACK.md](ROADMAP_FEEDBACK.md):

| Idea | Source | Description |
|------|--------|-------------|
| **Synthetic Data Generator** | Brainstorm | Schema-aware test data generation with faker |
| **API-ify (Query→Endpoint)** | Brainstorm | One-click deploy query results as a REST API |
| **Auto-Documentation Site** | Brainstorm | Generate MkDocs/Docusaurus site from schema + lineage |
| **Watchdog Agents** | PM Feedback | Scheduled queries with anomaly alerting ("Tool→Teammate") |
| **Business Glossary** | PM Feedback | Consistent term definitions across all LLM queries |
| **Guru API** | PM+Brainstorm | Expose agent as REST API for Slack bots, dashboards |
| **Webhook Sources** | PM Feedback | Query JSON URLs as virtual tables (DuckDB http scan) |
| **Metric Trees** | PM Feedback | Auto-decompose metrics into breakdown dimensions |
| **Shared Workspaces** | PM Feedback | Read-only session sharing with URL |

### Completed Phases (for reference)
- **Phase 12** ✅: Lineage Intelligence (5 agents, 151 tests, ~11,266 lines)
- **Phase 13** ✅: CSV & Excel File Support (50+ tests)
- **Phase 16** ✅: LLM Usage Monitoring (9 endpoints, full dashboard)
- **Phase 17** ✅: Multi-Provider Monitoring (native token extraction for 6 provider formats, user-managed model pricing, cost summary, provider comparison — 29 tests, 7 new endpoints, ~1,373 lines)
- **Phase 19** ✅: Data Insights Enhancement (tiered narratives, analytics cache, multi-source quality, chart presets, parallel analysis — 108 tests)
- **Phase 20** ✅: Database Migration Toolkit (schema diff, planner, script gen, data migration — 98 tests, 13 endpoints, ~5,676 lines)
- **Phase 22** ✅: Performance Guru (EXPLAIN analysis, LLM interpretation, index suggestions, 4 dialects — 77 tests, 2 endpoints, ~3,282 lines)
- **Phase 23** ✅: Docker Containerization (Compose profiles, security hardened, least-privilege Postgres, Ollama retry, prompts refactor, CTE lineage support)
- **Phase 14** ✅: NoSQL Database Expansion (MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch — native query gen, schema inference, error classification, frontend integration, mixed SQL+NoSQL chat — 127 tests)
- **Phase 21** ✅: Security & Auth Foundation (JWT auth, resource ownership, per-user rate limiting, audit logging — 61 tests, 3 migrations)
- **Phase 15** ✅: LLM Provider Expansion (8 providers, provider abstraction + registry, data security enforcement, Local/Frontier toggle UI, per-task routing, fallback chains, Fernet-encrypted API keys — 220 tests, 8 endpoints, ~4,000 lines)
- **Phase 18** ✅: Edit Mode & DML Operations (DML generator/validator/executor, inline editing UI, per-connection write permissions, preview mode — 40 tests, 5 endpoints, ~2,450 lines)
- **Table Sorting** ✅: Click-to-sort with smart type detection
- Plus 10+ earlier phases (see Quick Reference below)

---

## Summary by Category

| Category | Features | Status | Total Effort |
|----------|----------|--------|--------------|
| **Visualization** | ER Diagrams, Data Lineage | Phase 7 ✅, Phase 11 ✅ | COMPLETE |
| **LLM Intelligence** | Lineage Narrator, Impact Advisor, Schema Health, Pattern Intel, Lineage Chat | **Phase 12 ✅ COMPLETE** | ~11,266 lines |
| **Data Sources** | CSV & Excel File Support | **Phase 13 ✅ COMPLETE** | ~2,500 lines |
| **LLM Monitoring** | Token usage tracking, dashboard, inline stats | **Phase 16 ✅ COMPLETE** | ~1,500 lines |
| **Security & Auth** | JWT auth, resource ownership, per-user rate limiting, audit logging | **Phase 21 ✅ COMPLETE** | ~2,200 lines |
| **Auth Hardening** | Token versioning (`pv` JWT claim), per-user change-pwd rate limit, login lockout, one-shot reset tokens, password history, admin quorum | **Phase 24.8 ✅ A/B/C/D1/D3** (D2 deferred) | ~1,400 lines |
| **LLM Integration** | 8 providers (Ollama, OpenAI, Azure OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM), data security, provider routing | **Phase 15 ✅ COMPLETE** | ~4,000 lines |
| **Migration Toolkit** | Schema diff, migration planner, script gen, data migration | **Phase 20 ✅ COMPLETE** | ~5,676 lines |
| **Edit Mode & DML** | Inline editing, INSERT/UPDATE/DELETE, preview mode, write permissions | **Phase 18 ✅ COMPLETE** | ~2,450 lines |
| **Performance Guru** | EXPLAIN analysis, LLM interpretation, index suggestions, 4 dialects | **Phase 22 ✅ COMPLETE** | ~3,282 lines |
| **Multi-Provider Monitoring** | Native tokens, cost tracking, provider comparison, model pricing admin | **Phase 17 ✅ COMPLETE** | ~1,373 lines |
| **Data Insights** | Tiered narratives, analytics cache, multi-source quality, chart presets, parallel analysis | **Phase 19 ✅ COMPLETE** | ~1,800 lines |
| **NoSQL Expansion** | MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch, frontend integration, mixed chat | **Phase 14 ✅ COMPLETE** | ~6,000 lines |
| **Table UX** | Sorting ✅, Resizing, Export | Sorting complete | ~400 lines remaining |
| **Insight Quality** | Preprocessing, Pattern Learning | Not started | ~1,200 lines |
| **Performance** | Streaming Results | Future | ~1,500 lines |
| **Docker Containerization** | Docker Compose, Nginx proxy, BYO LLM, profiles (ollama/full) | **Phase 23 ✅ COMPLETE** | ~200 lines config |
| **Observability** | Structured logging, OpenTelemetry tracing, Prometheus/Grafana, Docker observability profile | **Phase 24 ✅ Complete** | ~1,300 lines |
| **Innovation Pipeline** | Synthetic Data, API-ify, Auto-Docs, Watchdog, Guru API, etc. | Ideas stage | TBD |

---

## Quick Reference: What's Complete

| Feature | Impact | Tests |
|---------|--------|-------|
| Parallel Multi-DB | 3x speedup | 6 tests |
| Parallel Corrections | 1.6x speedup | 7 tests |
| Semantic Caching | 50% hit rate | 20 tests |
| Tool-Using Agent | Better first-attempt | 26 tests |
| Connection Pooling | 30x faster | 29 tests |
| Result Narrator | Advanced analysis | 75 tests |
| Data Insights (Phase 19) | Tiered narratives, analytics cache, quality insights, chart presets, parallel analysis | 108 tests (92 BE + 16 FE) |
| Chart Intelligence | Smart recommendations | 71 tests |
| Advanced Charts | 6 new chart types | 61 tests |
| Query Compilation | Cache + prepared stmts | 21 tests |
| Model Router | Per-task models | 220 lines tests |
| Prompt Optimizer | 40% token reduction | 52 tests |
| Dialect Registry | DB-specific SQL | 72 lines tests |
| Multi-DB Validator | Pre-flight validation | 27 tests |
| ER Diagrams (Phase 7) | Schema visualization | React Flow + Dagre |
| Data Lineage (Phase 11) | Column-level lineage, impact analysis, query patterns | 185 tests (116 BE + 69 FE) |
| Lineage Intelligence (Phase 12) | LLM-powered lineage explanations, schema health, impact advisor | 151 tests |
| CSV & Excel Files (Phase 13) | File upload, DuckDB queries, cross-source JOINs | 50+ tests |
| LLM Usage Monitoring (Phase 16) | Token/cost tracking, dashboard, per-session stats | 9 API endpoints |
| Docker Containerization (Phase 23) | Compose profiles, Nginx proxy, security hardened, Ollama retry, CTE lineage | Deployment guide |
| Table Sorting | Click-to-sort columns, smart type detection | 24 tests |
| Migration Toolkit (Phase 20) | Schema diff, migration planner, script generator, data migration | 98 tests |
| Performance Guru (Phase 22) | EXPLAIN plan analysis, LLM insights, index suggestions, query rewrites, 4 dialects | 77 tests |
| NoSQL Expansion (Phase 14) | MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch — native query gen, schema inference, error classification, frontend integration, mixed SQL+NoSQL chat | 127 tests |
| Security & Auth (Phase 21) | JWT auth (bcrypt + python-jose), resource ownership (owner_id on 5 tables), per-user rate limiting, audit logging, REQUIRE_AUTH feature flag | 61 tests |
| Edit Mode & DML (Phase 18) | DML generator/validator/executor, inline cell editing, add/delete rows, preview mode, per-connection write permissions, 5 API endpoints | 40 tests |
| LLM Provider Expansion (Phase 15) | 8 providers (Ollama, OpenAI, Azure OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM), provider abstraction + registry, data security enforcement (Local/Frontier), per-task routing with fallback chains, Fernet-encrypted API keys, frontend provider management UI | 220 tests |
| Multi-Provider Monitoring (Phase 17) | Native token extraction for 6 provider formats, user-managed model pricing (CRUD), cost summary with daily breakdown, provider comparison by agent type, unpriced model detection, ModelPricingManager UI | 29 tests |

**Total Tests**: 2100+ passing

---

## Upcoming Phases Summary

| Phase | Feature | Dependencies | Est. Effort | Priority |
|-------|---------|--------------|-------------|----------|
| **Phase 21** | Security & Auth Foundation | None | ~2,200 lines | ✅ **COMPLETE** |
| **Phase 15** | LLM Provider Expansion | Phase 21 ✅ | ~4,000 lines | ✅ **COMPLETE** |
| **Phase 20** | Migration Toolkit | Phase 11✅ + 12✅ | ~5,676 lines | ✅ **COMPLETE** |
| **Phase 18** | Edit Mode & DML Operations | Phase 21 ✅ | ~2,450 lines | ✅ **COMPLETE** |
| **Phase 22** | Performance Guru (EXPLAIN) | None | ~3,282 lines | ✅ **COMPLETE** |
| **Phase 17** | Multi-Provider Monitoring | Phase 15✅ + 16✅ | ~1,373 lines | ✅ **COMPLETE** |
| **Phase 19** | Data Insights Enhancement | None | ~1,800 lines | ✅ **COMPLETE** |
| **Phase 23** | Docker Containerization | None | ~200 lines config | ✅ **COMPLETE** |
| **Phase 24** | Observability & Monitoring | Phase 23 ✅ | ~1,300 lines | ✅ **COMPLETE** |
| **Phase 24.7** | Admin & Observability UI | Phase 21 ✅ + Phase 24 ✅ | ~3,465 lines (4 PRs) | ✅ **COMPLETE** |
| **Phase 24.8** | Auth Hardening (A/B/C/D1/D3) | Phase 21 ✅ + Phase 24.7 ✅ | ~1,400 lines + 4 migrations | ✅ **COMPLETE** (D2 deferred, needs Redis) |
| **Phase 14** | NoSQL Database Expansion | None | ~6,000 lines | ✅ **COMPLETE** |

---

## Source Documents

- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Core roadmap
- [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md) - Visualization features
- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - LLM optimization features
- [DATA_LINGEAGE_PLAN.md](DATA_LINGEAGE_PLAN.md) - Data Lineage & Impact Analysis plan (Phase 11)
- [LINEAGE_INTELLIGENCE_PLAN.md](LINEAGE_INTELLIGENCE_PLAN.md) - LLM-Powered Lineage Intelligence (Phase 12)
- [CSV_EXCEL_SUPPORT_PLAN.md](CSV_EXCEL_SUPPORT_PLAN.md) - CSV & Excel File Support (Phase 13) ✅
- [NOSQL_EXPANSION_PLAN.md](NOSQL_EXPANSION_PLAN.md) - NoSQL Database Expansion (Phase 14)
- [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) - LLM Provider Expansion (Phase 15) ✅
- [LLM_USAGE_MONITORING_PLAN.md](LLM_USAGE_MONITORING_PLAN.md) - LLM Usage Monitoring (Phase 16) ✅
- [MULTI_PROVIDER_MONITORING_INTEGRATION.md](MULTI_PROVIDER_MONITORING_INTEGRATION.md) - Multi-Provider Monitoring (Phase 17) ✅
- [PHASE_18_EDIT_MODE_FEATURE_IMP_PLAN.md](PHASE_18_EDIT_MODE_FEATURE_IMP_PLAN.md) - Edit Mode & DML Operations (Phase 18) ✅
- [DATA_INSIGHTS_ENHANCEMENT_PLAN.md](DATA_INSIGHTS_ENHANCEMENT_PLAN.md) - Data Insights Enhancement (Phase 19)
- [MIGRATION_TOOLKIT_PROPOSAL.md](MIGRATION_TOOLKIT_PROPOSAL.md) - Database Migration Toolkit (Phase 20)
- [DOCKER_CONTAINERIZATION_PLAN.md](DOCKER_CONTAINERIZATION_PLAN.md) - Docker Containerization (Phase 23)
- [Phase 24_Observability_&_Monitoring.md](Phase%2024_Observability_%26_Monitoring.md) - Observability backend (Phase 24) ✅
- [PHASE_24_Observability_&_Monitoring_UI_PLAN.md](PHASE_24_Observability_%26_Monitoring_UI_PLAN.md) - Admin & Observability UI (Phase 24.7) ✅
- [PASSWORD_AUTH_HARDENING_PLAN.md](PASSWORD_AUTH_HARDENING_PLAN.md) - Auth Hardening (Phase 24.8) ✅ A/B/C/D1/D3, ⏳ D2 deferred
- [FEATURE_SUGGESTIONS_BRAINSTORM.md](FEATURE_SUGGESTIONS_BRAINSTORM.md) - Innovation pipeline ideas
- [ROADMAP_FEEDBACK.md](ROADMAP_FEEDBACK.md) - PM review & strategic recommendations

---

**Updated**: April 26, 2026
- **Phase 17 ✅ COMPLETE**: Multi-Provider Monitoring
- **Phase 15 ✅ COMPLETE**: LLM Provider Expansion
  - 15.1: Provider Abstraction — BaseLLMProvider ABC, DataLocality enum, ProviderRegistry, TrackedLLMClient wrapper
  - 15.2: OpenAI-Compatible Providers — OpenAI, LM Studio, vLLM via shared httpx base class
  - 15.3: Azure OpenAI + Anthropic — deployment-based URLs, Messages API with content blocks
  - 15.4: Enhanced Model Router + DB + API — ProviderConfigService with Fernet encryption, 8 REST endpoints, execute_with_fallback()
  - 15.5: Google Vertex AI + AWS Bedrock — REST/ADC for Vertex, boto3 Converse API for Bedrock
  - 15.6: Frontend UI — Local/Frontier toggle, provider cards, config modals, per-task routing grid, ModelSelect with locality badges
  - 15.7: Caller Migration — all 16 callers migrated from get_ollama_client() to get_llm_client()
  - 220 tests | 8 API endpoints | ~4,000 lines across 21 new files + 31 modified

- **Phase 18 ✅ COMPLETE**: Edit Mode & DML Operations
  - 18.1: DML Generator — parameterized INSERT/UPDATE/DELETE with multi-dialect support
  - 18.2: DML Validator — safety checks (require WHERE clause, row limits, allowed tables)
  - 18.3: DML Executor — transaction-wrapped execution with rollback on error
  - 18.1-18.3 Backend: ~640 lines across generator, validator, executor, models, constants
  - API: 5 endpoints (preview, execute, get/update permissions, table-info)
  - Frontend: EditableQueryResults, EditableCell, AddRowForm, DeleteConfirmation, ChangesSummaryBar, DMLPreviewPanel, EditModeToggle, EditModeWrapper (~1,070 lines)
  - Hooks: useChangeTracker, useEditMode, useDMLExecution
  - Per-connection write permissions with INSERT/UPDATE/DELETE toggles and allowed_tables
  - ConnectionWritePermission model + Alembic migration
  - 40 tests (generator, validator, executor)
- **Phase 22 ✅ COMPLETE**: Performance Guru
  - 22.1: Explain Analyzer — deterministic EXPLAIN plan parser for PostgreSQL, MySQL, SQLite, DuckDB
  - 22.2: Explain Interpreter — LLM-powered plan interpretation with tiered prompts (compact/standard/enhanced)
  - 22.3: Performance API — 2 endpoints (analyze with LLM, explain-only without)
  - Frontend: PerformancePanel, ExecutionPlanTree (collapsible nodes), PerformanceInsightsPanel (bottlenecks, index suggestions, query rewrites)
  - Safety: SQL validation blocks DDL/DML and multi-statement queries, EXPLAIN ANALYZE requires opt-in
  - Deterministic fallback on LLM timeout/error, SQLite short-circuit (no LLM needed)
  - 77 tests, 2 API endpoints, ~3,282 lines
- **Phase 20 ✅ COMPLETE**: Database Migration Toolkit
  - 20.1: Schema diff engine (visual DB-to-DB comparison, drift analysis, fingerprinting)
  - 20.2: Migration planner (topological sort with existing FKs, data-loss detection, LLM enrichment)
  - 20.3: Script generator (up.sql/down.sql/verify.sql, multi-dialect, SQLite recreate with unchanged columns)
  - 20.4: Data migration assistant (staging table pattern, batched INSERT SELECT, validation queries)
  - SQL injection protection (`_escape_literal`), N+1 fix (`selectinload`), `SchemaDiff.from_dict()` DRY helper
  - 98 tests, 13 API endpoints, ~5,676 lines
- **Phase 19 ✅ COMPLETE**: Data Insights Enhancement
  - 19.1: Tiered narrative prompts (compact/standard/enhanced by model size, 40% token savings)
  - 19.2: Analytics caching (two-tier: local TTLCache + optional Redis, 24hr TTL)
  - 19.3: Multi-source data quality insights (null rates, duplicates, freshness, coverage gaps)
  - 19.4: Chart intelligence enhancements (adaptive scoring presets, column interest scoring, context-aware insights)
  - 19.5: Parallel analysis pipeline (asyncio.gather for stats/anomalies/correlations, early exit for small datasets)
  - 108 tests (92 backend + 16 frontend)
- **Phase 23 ✅ COMPLETE**: Docker Containerization with security hardening
  - Multi-stage Dockerfiles (backend + frontend), Compose profiles (ollama, full)
  - Nginx reverse proxy with CSP headers, non-root containers, least-privilege Postgres
  - Ollama retry logic (tenacity), prompts.py refactored into package
  - CTE support added to SQL lineage parser
- **Phase 24 ✅ COMPLETE**: Observability & Monitoring (structlog, Prometheus, OpenTelemetry, Docker observability profile)
- **Phase 24.7 ✅ COMPLETE**: Admin & Observability UI (4 PRs)
  - PR1: X-Request-ID exposed via CORS, axios response interceptor populates `useLastRequestStore`, header `LastRequestBadge` shows short id and copies the full id + traceparent
  - PR2: Admin tab scaffolding (`AdminPanel`), `AuditLogViewer` with paginated server-side filters and JSON drawer, `auditApi.ts`, `audit.py` adds list/me/facets endpoints
  - PR3: Observability section in `SettingsPanel` with deep-links (Prometheus / Jaeger / Grafana), `SystemHealthPanel` Health sub-tab replacing the demo (live `/health`, observability gates, last-request widget, recent queries + audit), `JAEGER_UI_URL`/`GRAFANA_URL`/`METRICS_PUBLIC_URL` settings exposed via `/api/settings`
  - PR4: `admin_users.py` with list/create/update/reset-password/deactivate, `UserManagement.tsx` with role toggle / disable / reset, `CreateUserModal`, `adminUsersApi.ts`, self-lockout protection on the backend, every action audit-logged
  - Plus: removed 1,133-LOC `ObservabilityDemo.tsx` mock, introduced `ADMIN_UI_ENABLED` kill-switch (router mount + frontend tab/section gating)
- **Phase 24.8 ✅ A/B/C/D1/D3 COMPLETE**: Auth Hardening (toggleable per-deployment)
  - **Phase A — Token versioning**: `users.password_version` column (alembic `4f9a1c8b2e3d`), JWT `pv` claim stamped only when `AUTH_TOKEN_VERSIONING_ENABLED=True`, `get_current_user` rejects stale `pv` (legacy tokens with no claim accepted so flipping the flag is non-destructive). `bump_password_version()` helper called on password change, admin reset, and conditionally on logout / deactivate (`AUTH_INVALIDATE_TOKENS_ON_LOGOUT`, `AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE`). Change-password endpoint returns a fresh `TokenResponse` so the caller stays signed in while every other device is evicted.
  - **Phase B — Rate limit + lockout**: `_UserKeyedRateLimiter` for change-password (`AUTH_RATE_LIMIT_CHANGE_PASSWORD`, `AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE`), `LoginAttemptTracker` for username-keyed login lockout (`AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED`, `AUTH_LOGIN_LOCKOUT_THRESHOLD`, `AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS`). Tracker is case-insensitive so casing can't dodge it; unknown usernames count too (defeats enumeration via lockout-vs-401). `account_locked` / `account_unlocked` audit events. In-process — multi-worker deployments swap in a Redis backend.
  - **Phase C — One-shot reset tokens**: `password_reset_tokens` table (alembic `5e2b7a9d4c8f`), `AUTH_PASSWORD_RESET_MODE` 3-way switch (`temp_password` | `reset_token` | `both`), `POST /api/auth/redeem-reset` walks outstanding tokens via bcrypt comparison, frontend `/reset?token=…` redemption screen short-circuits the rest of the gating. Admin reset modal conditionally renders password OR redemption URL OR both. `AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES` and `AUTH_PASSWORD_RESET_BASE_URL` configurable.
  - **Phase D1 — Password history**: `password_history` table (alembic `6a3c5f8e7b1d`), `AUTH_PASSWORD_HISTORY_DEPTH` (0 = disabled). Reuse against current or last N hashes returns 400 from both `change-password` and `redeem-reset`. Trimmed on insert so the table stays bounded.
  - **Phase D3 — Admin quorum**: `count_active_admins()` + `_enforce_admin_quorum()` helper. When `AUTH_REQUIRE_ADMIN_QUORUM=True`, refuses any demote/deactivate that would drop the active-admin count to 0. Layered with the existing self-edit protection.
  - **Plumbed everywhere**: 13 new `AUTH_*` settings, `Settings.check_auth_hardening()` startup validator, `SystemSettingsResponse` mirror, frontend `AuthHardeningConfig` type, Admin → Health "Auth hardening" panel with live gates and inline warnings (e.g. `reset_token` mode + missing base URL).
  - 4 migrations, 2 new endpoints (`/api/auth/change-password`, `/api/auth/redeem-reset`), ~1,400 lines, 44 new tests across 6 files (`test_auth_change_password.py`, `test_auth_token_versioning.py`, `test_auth_rate_limit.py`, `test_auth_reset_tokens.py`, `test_auth_history_and_quorum.py`, `test_settings_auth_hardening.py`).
  - **⏳ Phase D2 (JWT JTI denylist on logout) — DEFERRED.** Phase A's `AUTH_INVALIDATE_TOKENS_ON_LOGOUT` covers the coarse case (logout kicks every device). D2 only matters when per-session revocation is needed and the version-bump approach is too coarse. Slot it in once Redis is part of the standard deploy story (Phase 23 `full` profile).
- Previous: Added Phase 20-22, Innovation Pipeline, promoted Security to CRITICAL
