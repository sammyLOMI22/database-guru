# Database Guru - Master Development Roadmap

**Last Updated**: February 15, 2026
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
    │                         NOSQL EXPANSION (Phase 14) - DATA SOURCES                       │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    NOSQL DATABASE SUPPORT (Phase 14) - LOW PRIORITY (Deprioritized)      │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
    │  │ 14.1        │   │ 14.2        │   │ 14.3        │   │ 14.4        │   │ 14.5        │ │
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
    │  Prereq: None (Independent) | Priority: LOW (per PM review) | Est: 6-8 weeks | ~6,000 ln │
    │  Plan: NOSQL_EXPANSION_PLAN.md                                                           │
    │  NOTE: SQL + Files (Phase 13) covers ~90% of analytic use cases. NoSQL is niche.         │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                         LLM PROVIDER EXPANSION (Phase 15)                               │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    MULTI-PROVIDER LLM SUPPORT (Phase 15) - HIGH PRIORITY                 │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 15.1 Provider│   │ 15.2 Azure  │   │ 15.3-15.6   │   │ 15.7-15.9   │                  │
    │  │ Abstraction │──▶│ OpenAI      │──▶│ More        │──▶│ Router &    │                   │
    │  │             │   │             │   │ Providers   │   │ Frontend    │                   │
    │  │ • Base class│   │ • Enterprise│   │             │   │             │                   │
    │  │ • Registry  │   │   support   │   │ • OpenAI    │   │ • Multi-    │                   │
    │  │ • Refactor  │   │ • Deployment│   │ • Anthropic │   │   provider  │                   │
    │  │   Ollama    │   │   models    │   │ • Vertex AI │   │   routing   │                   │
    │  │             │   │ • Azure Auth│   │ • Bedrock   │   │ • Fallback  │                   │
    │  │ ~600 lines  │   │ ~500 lines  │   │ • LM Studio │   │ • Config UI │                   │
    │  └─────────────┘   └─────────────┘   │ • vLLM      │   │             │                   │
    │                                       │ ~1,700 lines│   │ ~1,200 lines│                   │
    │                                       └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: HIGH | Est: 3-4 weeks | ~3,000 lines            │
    │  Plan: LLM_PROVIDER_EXPANSION_PLAN.md                                                    │
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
    │                   MULTI-PROVIDER MONITORING (Phase 17)                                  │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │               MULTI-PROVIDER MONITORING INTEGRATION (Phase 17) - MEDIUM PRIORITY         │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 17.1 Token  │   │ 17.2 Base   │   │ 17.3 API &  │   │ 17.4 Dash-  │                   │
    │  │ Extractors  │──▶│ Provider    │──▶│ Schema      │──▶│ board       │                   │
    │  │             │   │ Updates     │   │ Updates     │   │ Widgets     │                   │
    │  │             │   │             │   │             │   │             │                   │
    │  │ • Per-      │   │ • Enrich    │   │ • /by-      │   │ • Cost by   │                   │
    │  │   provider  │   │   response  │   │   provider  │   │   provider  │                   │
    │  │   formats   │   │ • Native    │   │ • /cost-    │   │ • Provider  │                   │
    │  │ • Pricing   │   │   tokens    │   │   summary   │   │   compare   │                   │
    │  │   data      │   │ • Cost calc │   │ • Provider  │   │ • Cost      │                   │
    │  │             │   │             │   │   column    │   │   trends    │                   │
    │  │ ~300 lines  │   │ ~200 lines  │   │ ~300 lines  │   │ ~400 lines  │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: Phase 15 + Phase 16 | Priority: MEDIUM | Est: 1-2 weeks | ~1,200 lines         │
    │  Plan: MULTI_PROVIDER_MONITORING_INTEGRATION.md                                          │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    DATA INSIGHTS ENHANCEMENT (Phase 19) - NEW                           │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                 DATA INSIGHTS ENHANCEMENT (Phase 19) - MEDIUM PRIORITY                   │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
    │  │ 19.1 Small  │   │ 19.2        │   │ 19.3 Multi- │   │ 19.4 Chart  │   │ 19.5        │ │
    │  │ Model       │──▶│ Analytics   │──▶│ Source      │──▶│ Intelligence│──▶│ Parallel    │ │
    │  │ Optimization│   │ Caching     │   │ Insights    │   │ Enhance     │   │ Analysis    │ │
    │  │             │   │             │   │             │   │             │   │             │ │
    │  │ • Tiered    │   │ • Stats     │   │ • Quality   │   │ • Adaptive  │   │ • Async     │ │
    │  │   prompts   │   │   cache     │   │   metrics   │   │   weights   │   │   analysis  │ │
    │  │ • Token     │   │ • Pattern   │   │ • Gap       │   │ • Smart     │   │ • Early     │ │
    │  │   budgets   │   │   cache     │   │   analysis  │   │   columns   │   │   exit      │ │
    │  │ • 40% save  │   │ • 24hr TTL  │   │ • Freshness │   │ • Context   │   │ • 30-40%    │ │
    │  │             │   │             │   │             │   │   insights  │   │   speedup   │ │
    │  │ ~400 lines  │   │ ~350 lines  │   │ ~450 lines  │   │ ~350 lines  │   │ ~250 lines  │ │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘ │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: MEDIUM | Est: 2-3 weeks | ~1,800 lines          │
    │  Plan: DATA_INSIGHTS_ENHANCEMENT_PLAN.md                                                 │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    SECURITY & AUTH FOUNDATION (Phase 21) - CRITICAL                     │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              SECURITY & AUTH FOUNDATION (Phase 21) - CRITICAL PRIORITY                    │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 21.1 User   │   │ 21.2 Session│   │ 21.3 Rate   │   │ 21.4 Audit  │                   │
    │  │ Auth (JWT)  │──▶│ Ownership   │──▶│ Limiting    │──▶│ Logging     │                   │
    │  │             │   │             │   │             │   │             │                   │
    │  │ • JWT auth  │   │ • user_id   │   │ • Per-user  │   │ • Action    │                   │
    │  │ • Login/    │   │   on all    │   │   limits    │   │   trail     │                   │
    │  │   register  │   │   resources │   │ • Endpoint- │   │ • DML audit │                   │
    │  │ • Middleware│   │ • 403 on    │   │   specific  │   │ • LLM cost  │                   │
    │  │ • CSRF      │   │   unauth'd  │   │ • Cost      │   │   controls  │                   │
    │  │             │   │   access    │   │   controls  │   │             │                   │
    │  │ ~800 lines  │   │ ~500 lines  │   │ ~400 lines  │   │ ~500 lines  │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None | Priority: CRITICAL | Est: 2-3 weeks | ~2,200 lines                      │
    │  BLOCKS: Phase 18 (Edit Mode), Phase 15 (Enterprise LLMs need cost controls)             │
    │  Source: PM Review (ROADMAP_FEEDBACK.md) - "Cannot release DML without Auth"             │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    MIGRATION TOOLKIT (Phase 20) - HIGH PRIORITY                         │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                   DATABASE MIGRATION TOOLKIT (Phase 20) - HIGH PRIORITY                   │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 20.1 Schema │   │ 20.2 Migr.  │   │ 20.3 Script │   │ 20.4 Data   │                   │
    │  │ Diff Engine │──▶│ Planner     │──▶│ Generator   │──▶│ Migration   │                   │
    │  │             │   │             │   │             │   │ Assistant   │                   │
    │  │ • Visual    │   │ • Dependency│   │ • up.sql    │   │             │                   │
    │  │   diff      │   │   ordering  │   │ • down.sql  │   │ • INSERT    │                   │
    │  │ • Drift     │   │ • Data loss │   │ • verify.sql│   │   SELECT    │                   │
    │  │   analysis  │   │   detection │   │ • Multi-    │   │ • Batching  │                   │
    │  │ • DB vs DB  │   │ • Lock      │   │   dialect   │   │ • Validate  │                   │
    │  │ • DB vs file│   │   awareness │   │             │   │   queries   │                   │
    │  │             │   │ • LLM intent│   │             │   │             │                   │
    │  │ ~800 lines  │   │ ~700 lines  │   │ ~600 lines  │   │ ~500 lines  │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: Phase 11 (Lineage) + Phase 12 (Intelligence) | Priority: HIGH                  │
    │  Est: 3-4 weeks | ~2,600 lines                                                          │
    │  Plan: MIGRATION_TOOLKIT_PROPOSAL.md                                                     │
    │  Relates: Phase 18 (Edit Mode - DML execution), Security (DDL permissions)               │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                    PERFORMANCE GURU (Phase 22) - MEDIUM PRIORITY                        │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    DEEP EXPLAIN ANALYSIS (Phase 22) - MEDIUM PRIORITY                    │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                                     │
    │  │ 22.1 Explain│   │ 22.2 LLM    │   │ 22.3 Action │                                     │
    │  │ Analyzer    │──▶│ Interpreter │──▶│ Advisor     │                                     │
    │  │             │   │             │   │             │                                     │
    │  │ • EXPLAIN   │   │ • Parse JSON│   │ • Index     │                                     │
    │  │   ANALYZE   │   │   plans     │   │   suggest   │                                     │
    │  │ • Multi-    │   │ • Identify  │   │ • Rewrite   │                                     │
    │  │   dialect   │   │   bottleneck│   │   advice    │                                     │
    │  │ • Cost model│   │ • Disk spill│   │ • Before/   │                                     │
    │  │             │   │   detection │   │   after est │                                     │
    │  │ ~500 lines  │   │ ~400 lines  │   │ ~400 lines  │                                     │
    │  └─────────────┘   └─────────────┘   └─────────────┘                                     │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: MEDIUM | Est: 2-3 weeks | ~1,300 lines          │
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
    │                    OBSERVABILITY & MONITORING (Phase 24) - MEDIUM PRIORITY              │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │              OBSERVABILITY STACK (Phase 24) - MEDIUM PRIORITY                            │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 24.1 Struct-│   │ 24.2 Open-  │   │ 24.3 Metrics│   │ 24.4 Docker │                   │
    │  │ ured Logging│──▶│ Telemetry   │──▶│ & Dashboards│──▶│ Integration │                   │
    │  │             │   │ Tracing     │   │             │   │             │                   │
    │  │ • JSON logs │   │ • OTEL SDK  │   │ • Prometheus│   │ • Compose   │                   │
    │  │ • Request   │   │ • Span per  │   │   exporter  │   │   profile   │                   │
    │  │   context   │   │   agent call│   │ • Grafana   │   │ • Jaeger    │                   │
    │  │ • Log       │   │ • Jaeger    │   │   dashboards│   │   container │                   │
    │  │   aggregator│   │   exporter  │   │ • Alerting  │   │ • Grafana   │                   │
    │  │             │   │ • LLM spans │   │   rules     │   │   container │                   │
    │  │ ~300 lines  │   │ ~500 lines  │   │ ~400 lines  │   │ ~100 lines  │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: Phase 23 ✅ (Docker) | Priority: MEDIUM | Est: 2 weeks | ~1,300 lines          │
    │  Adds observability profile to Docker Compose                                            │
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
    │                            EDIT MODE & DML (Phase 18) - NEW                             │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                  EDIT MODE & DML OPERATIONS (Phase 18) - MEDIUM PRIORITY                 │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 18.1 Core   │   │ 18.2 API &  │   │ 18.3 Inline │   │ 18.4 NL DML │                   │
    │  │ Backend     │──▶│ Execution   │──▶│ Editing UI  │──▶│ & Polish    │                   │
    │  │             │   │             │   │             │   │             │                   │
    │  │ • Change    │   │ • DML       │   │ • Editable  │   │ • Natural   │                   │
    │  │   tracker   │   │   endpoints │   │   cells     │   │   language  │                   │
    │  │ • DML gen   │   │ • Execute   │   │ • Add row   │   │   to DML    │                   │
    │  │ • Audit log │   │   w/ Tx     │   │ • Delete    │   │ • Audit     │                   │
    │  │ • Validator │   │ • Preview   │   │ • Preview   │   │   viewer    │                   │
    │  │             │   │             │   │             │   │             │                   │
    │  │ ~1,000 lines│   │ ~800 lines  │   │ ~1,200 lines│   │ ~1,000 lines│                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: MEDIUM | Est: 4-5 weeks | ~4,000 lines          │
    │  Plan: EDIT_MODE_DML_PLAN.md                                                             │
    │                                                                                           │
    │  Key Features:                                                                           │
    │  • Inline cell editing in query results                                                  │
    │  • Add new rows with schema-aware forms                                                  │
    │  • Delete rows with confirmation                                                         │
    │  • Generate & preview INSERT/UPDATE/DELETE scripts                                       │
    │  • Transaction support with rollback                                                     │
    │  • Natural language DML ("delete inactive users")                                        │
    │  • Complete audit trail                                                                  │
    │  • Per-connection write permissions                                                      │
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
    │                    SECURITY & INFRASTRUCTURE - PROMOTED TO CRITICAL                      │
    │               (Per PM Review: Required before Phase 18 Edit Mode & Phase 15)             │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Authorization      │  │   Session Expiration │  │   Rate Limiting      │
    │   System             │  │   (TTL, cleanup)     │  │   (Per-user)         │
    │   🔴 CRITICAL        │  │   Est: 2 days        │  │   Est: 2-3 days      │
    │   Blocks Phase 18+15 │  │   MEDIUM priority    │  │   HIGH priority      │
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


    INDEPENDENT FEATURES (Can Start Anytime):
    =========================================

    ┌───────────────────────────────────────────────────────────────────┐
    │   SECURITY & AUTH FOUNDATION (Phase 21) ◀── CRITICAL             │
    │                                                                   │
    │  BLOCKS: Phase 18 (Edit Mode) + Phase 15 (Enterprise LLMs)       │
    │                                                                   │
    │  • JWT authentication + session ownership                         │
    │  • Per-user rate limiting + cost controls                         │
    │  • Audit logging (merges Phase 18 audit needs)                    │
    │  • Est: 2-3 weeks | ~2,200 lines                                 │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        LLM PROVIDER EXPANSION (Phase 15) ◀── HIGH PRIORITY        │
    │                                                                   │
    │  • Azure OpenAI, OpenAI, Anthropic, Vertex AI, Bedrock            │
    │  • Local alternatives: LM Studio, vLLM                            │
    │  • Multi-provider routing with automatic fallback                 │
    │  • Est: 3-4 weeks | Plan: LLM_PROVIDER_EXPANSION_PLAN.md          │
    │  • NOTE: Ideally after Phase 21 (Auth) for cost controls          │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        PERFORMANCE GURU (Phase 22) ◀── MEDIUM PRIORITY            │
    │                                                                   │
    │  • EXPLAIN ANALYZE interpretation via LLM                         │
    │  • Actionable index/rewrite suggestions                           │
    │  • Multi-dialect support (PG, MySQL, SQLite)                      │
    │  • Est: 2-3 weeks | ~1,300 lines                                  │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        NOSQL DATABASE EXPANSION (Phase 14) ◀── LOW (Deprioritized)│
    │                                                                   │
    │  • MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch             │
    │  • SQL + Files covers ~90% of analytic use cases                  │
    │  • Est: 6-8 weeks | Plan: NOSQL_EXPANSION_PLAN.md                 │
    └───────────────────────────────────────────────────────────────────┘


    DEPENDENT FEATURES (Requires Prerequisites):
    ============================================

    ┌───────────────────────────────────────────────────────────────────┐
    │   EDIT MODE & DML (Phase 18) ◀── HIGH PRIORITY                    │
    │                                                                   │
    │   REQUIRES: Phase 21 (Security & Auth)                            │
    │                                                                   │
    │  • Inline editing, INSERT/UPDATE/DELETE, NL DML                   │
    │  • Simulation Mode: dry-run in transaction, show diff, rollback   │
    │  • Undo Button: time-travel rollback for Guru actions             │
    │  • Est: 4-5 weeks | Plan: EDIT_MODE_DML_PLAN.md                   │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │   MULTI-PROVIDER MONITORING (Phase 17) ◀── MEDIUM PRIORITY        │
    │                                                                   │
    │   REQUIRES: Phase 15 (Providers) + Phase 16 ✅ (Monitoring)       │
    │                                                                   │
    │  • Native token counts from OpenAI, Anthropic, Google, etc.       │
    │  • Accurate cost tracking per provider/model                      │
    │  • Provider performance comparison dashboard                      │
    │  • Est: 1-2 weeks | Plan: MULTI_PROVIDER_MONITORING_INTEGRATION.md│
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │   MIGRATION TOOLKIT (Phase 20) ◀── HIGH PRIORITY                  │
    │                                                                   │
    │   REQUIRES: Phase 11 ✅ (Lineage) + Phase 12 ✅ (Intelligence)    │
    │                                                                   │
    │  • Schema Diff (visual DB-to-DB comparison)                       │
    │  • Migration Planner (dependency-aware, data-loss detection)      │
    │  • Script Generator (up.sql / down.sql / verify.sql)              │
    │  • Data Migration Assistant (batching, validation)                │
    │  • Est: 3-4 weeks | Plan: MIGRATION_TOOLKIT_PROPOSAL.md           │
    └───────────────────────────────────────────────────────────────────┘

            ┌─────────────────┐          ┌─────────────────┐
            │   Phase 15      │          │   Phase 16 ✅   │
            │   Provider      │          │   Usage         │
            │   Expansion     │          │   Monitoring    │
            └────────┬────────┘          └────────┬────────┘
                     │                            │
                     └──────────┬─────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │     Phase 17        │
                     │   Multi-Provider    │
                     │     Monitoring      │
                     └─────────────────────┘

            ┌─────────────────┐
            │   Phase 21      │
            │   Security &    │
            │   Auth (CRIT)   │
            └────────┬────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
    ┌─────────────┐  ┌─────────────┐
    │  Phase 18   │  │  Phase 15   │
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
              │   Phase 20      │
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

## Recommended Next Steps (Updated Feb 14, 2026)

> **Strategic Direction** (per PM Review): Focus on "depth and safety" before "width expansion".
> Stabilize the foundation (Security/Auth) to support powerful features (Edit Mode, Enterprise LLMs).

### Priority 1: Security & Auth Foundation (Phase 21) - CRITICAL
**Why**: Prerequisite for Edit Mode (DML) and Enterprise LLM cost controls. Cannot release DELETE/UPDATE without Auth.
- **21.1 User Auth (JWT)**: Login/register, middleware, CSRF protection
- **21.2 Session Ownership**: `user_id` on all resources, 403 on unauthorized access
- **21.3 Rate Limiting**: Per-user limits, endpoint-specific, cost controls
- **21.4 Audit Logging**: Action trail, DML audit (merged from Phase 18), LLM cost controls
- Est: 2-3 weeks | ~2,200 lines
- **Blocks**: Phase 18 (Edit Mode), Phase 15 (Enterprise LLMs need cost controls)

### Priority 2: LLM Provider Expansion (Phase 15) - HIGH
**Why**: Enterprise integration and model flexibility - users can leverage cloud LLMs
- **15.1 Provider Abstraction**: Unified interface, registry, refactor Ollama
- **15.2 Azure OpenAI**: Enterprise-first cloud provider with deployment support
- **15.3-15.6 Additional Providers**: OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM
- **15.7-15.9 Enhanced Routing**: Multi-provider routing, fallback chains, frontend config UI
- See: [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md)
- Unlocks Phase 17 (Multi-Provider Monitoring) since Phase 16 is now complete

### Priority 3: Migration Toolkit (Phase 20) - HIGH
**Why**: Moves Database Guru from "Read-Only" analysis to "DevOps Companion" for database engineering
- **20.1 Schema Diff**: Visual comparison between databases or schema files, drift analysis
- **20.2 Migration Planner**: AI-agent that plans safe steps (dependency ordering, data-loss detection, lock awareness)
- **20.3 Script Generator**: Auto-generate `up.sql`, `down.sql`, `verify.sql` (multi-dialect)
- **20.4 Data Migration Assistant**: INSERT INTO SELECT, batching, validation queries
- See: [MIGRATION_TOOLKIT_PROPOSAL.md](MIGRATION_TOOLKIT_PROPOSAL.md)
- Dependencies met: Phase 11 ✅ + Phase 12 ✅

### Priority 4: Edit Mode & DML (Phase 18) - HIGH (blocked by Phase 21)
**Why**: High user value - inline editing, natural language DML
- Inline cell editing, add/delete rows, generate & preview scripts
- **Simulation Mode** (PM idea): Dry-run in transaction, show diff, rollback before commit
- **Undo Button** (PM idea): Time-travel rollback for actions taken by Guru
- Transaction support, natural language DML, audit trail
- See: [EDIT_MODE_DML_PLAN.md](EDIT_MODE_DML_PLAN.md)

### Priority 5: Performance Guru (Phase 22) - MEDIUM
**Why**: Reading raw EXPLAIN plans is hard; LLM is perfect for this translation layer
- Run `EXPLAIN ANALYZE` for slow queries, parse JSON execution plans
- LLM interprets: seq scans, disk spills, join costs
- Actionable advice: "Create INDEX ON users(email) to change Seq Scan to Index Scan"
- Multi-dialect support (PostgreSQL, MySQL, SQLite)
- Source: [FEATURE_SUGGESTIONS_BRAINSTORM.md](FEATURE_SUGGESTIONS_BRAINSTORM.md)

### Priority 6: Multi-Provider Monitoring (Phase 17) - MEDIUM
**Why**: Extend monitoring to all LLM providers with accurate cost tracking
- **Prerequisite**: Phase 15 (Providers) + Phase 16 ✅ (Monitoring)
- Native token extraction from OpenAI, Anthropic, Google formats
- Accurate cost tracking per provider/model, comparison dashboard
- See: [MULTI_PROVIDER_MONITORING_INTEGRATION.md](MULTI_PROVIDER_MONITORING_INTEGRATION.md)

### Priority 7: Data Insights Enhancement (Phase 19) - MEDIUM
**Why**: Multi-source insights, analytics caching, parallel analysis
- Small model optimization, analytics caching, multi-source insights
- **Metric Trees** (PM idea): Auto-decompose metrics (Revenue -> Region -> Product)
- **Business Glossary** (PM idea): Define "Churn", "Active User" for consistent LLM definitions
- See: [DATA_INSIGHTS_ENHANCEMENT_PLAN.md](DATA_INSIGHTS_ENHANCEMENT_PLAN.md)

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
- **Phase 23** ✅: Docker Containerization (Compose profiles, security hardened, least-privilege Postgres, Ollama retry, prompts refactor, CTE lineage support)
- **Table Sorting** ✅: Click-to-sort with smart type detection
- Plus 10+ earlier phases (see Quick Reference below)

### Deprioritized
- **NoSQL Expansion (Phase 14)**: Moved to LOW. SQL + Files covers ~90% of analytic use cases per PM review.

---

## Summary by Category

| Category | Features | Status | Total Effort |
|----------|----------|--------|--------------|
| **Visualization** | ER Diagrams, Data Lineage | Phase 7 ✅, Phase 11 ✅ | COMPLETE |
| **LLM Intelligence** | Lineage Narrator, Impact Advisor, Schema Health, Pattern Intel, Lineage Chat | **Phase 12 ✅ COMPLETE** | ~11,266 lines |
| **Data Sources** | CSV & Excel File Support | **Phase 13 ✅ COMPLETE** | ~2,500 lines |
| **LLM Monitoring** | Token usage tracking, dashboard, inline stats | **Phase 16 ✅ COMPLETE** | ~1,500 lines |
| **Security & Auth** | JWT auth, session ownership, rate limiting, audit logging | **Phase 21 - CRITICAL** | ~2,200 lines |
| **LLM Integration** | Azure OpenAI, OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM | **Phase 15 - HIGH** | ~3,000 lines |
| **Migration Toolkit** | Schema diff, migration planner, script gen, data migration | **Phase 20 - HIGH** (deps met) | ~2,600 lines |
| **Edit Mode & DML** | Inline editing, INSERT/UPDATE/DELETE, simulation mode, undo | **Phase 18 - HIGH** (needs 21) | ~4,000 lines |
| **Performance Guru** | EXPLAIN analysis, LLM interpretation, index suggestions | **Phase 22 - MEDIUM** | ~1,300 lines |
| **Multi-Provider Monitoring** | Native tokens, cost tracking, provider comparison | **Phase 17 - MEDIUM** (needs 15+16✅) | ~1,200 lines |
| **Data Insights** | Multi-source insights, metric trees, business glossary | **Phase 19 - MEDIUM** | ~1,800 lines |
| **NoSQL Expansion** | MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch | **Phase 14 - LOW** (deprioritized) | ~6,000 lines |
| **Table UX** | Sorting ✅, Resizing, Export | Sorting complete | ~400 lines remaining |
| **Insight Quality** | Preprocessing, Pattern Learning | Not started | ~1,200 lines |
| **Performance** | Streaming Results | Future | ~1,500 lines |
| **Docker Containerization** | Docker Compose, Nginx proxy, BYO LLM, profiles (ollama/full) | **Phase 23 ✅ COMPLETE** | ~200 lines config |
| **Observability** | Structured logging, OpenTelemetry tracing, Prometheus/Grafana | **Phase 24 - MEDIUM** | ~1,300 lines |
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

**Total Tests**: 1000+ passing

---

## Upcoming Phases Summary

| Phase | Feature | Dependencies | Est. Effort | Priority |
|-------|---------|--------------|-------------|----------|
| **Phase 21** | Security & Auth Foundation | None | ~2,200 lines | **CRITICAL** |
| **Phase 15** | LLM Provider Expansion | Ideally after 21 | ~3,000 lines | HIGH |
| **Phase 20** | Migration Toolkit | Phase 11✅ + 12✅ | ~2,600 lines | HIGH |
| **Phase 18** | Edit Mode & DML Operations | Phase 21 | ~4,000 lines | HIGH |
| **Phase 22** | Performance Guru (EXPLAIN) | None | ~1,300 lines | MEDIUM |
| **Phase 17** | Multi-Provider Monitoring | Phase 15 + 16✅ | ~1,200 lines | MEDIUM |
| **Phase 19** | Data Insights Enhancement | None | ~1,800 lines | MEDIUM |
| **Phase 23** | Docker Containerization | None | ~200 lines config | ✅ **COMPLETE** |
| **Phase 24** | Observability (OpenTelemetry) | Phase 23 ✅ | ~1,300 lines | MEDIUM |
| **Phase 14** | NoSQL Database Expansion | None | ~6,000 lines | LOW |

---

## Source Documents

- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Core roadmap
- [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md) - Visualization features
- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - LLM optimization features
- [DATA_LINGEAGE_PLAN.md](DATA_LINGEAGE_PLAN.md) - Data Lineage & Impact Analysis plan (Phase 11)
- [LINEAGE_INTELLIGENCE_PLAN.md](LINEAGE_INTELLIGENCE_PLAN.md) - LLM-Powered Lineage Intelligence (Phase 12)
- [CSV_EXCEL_SUPPORT_PLAN.md](CSV_EXCEL_SUPPORT_PLAN.md) - CSV & Excel File Support (Phase 13) ✅
- [NOSQL_EXPANSION_PLAN.md](NOSQL_EXPANSION_PLAN.md) - NoSQL Database Expansion (Phase 14)
- [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) - LLM Provider Expansion (Phase 15)
- [LLM_USAGE_MONITORING_PLAN.md](LLM_USAGE_MONITORING_PLAN.md) - LLM Usage Monitoring (Phase 16) ✅
- [MULTI_PROVIDER_MONITORING_INTEGRATION.md](MULTI_PROVIDER_MONITORING_INTEGRATION.md) - Multi-Provider Monitoring (Phase 17)
- [EDIT_MODE_DML_PLAN.md](EDIT_MODE_DML_PLAN.md) - Edit Mode & DML Operations (Phase 18)
- [DATA_INSIGHTS_ENHANCEMENT_PLAN.md](DATA_INSIGHTS_ENHANCEMENT_PLAN.md) - Data Insights Enhancement (Phase 19)
- [MIGRATION_TOOLKIT_PROPOSAL.md](MIGRATION_TOOLKIT_PROPOSAL.md) - Database Migration Toolkit (Phase 20)
- [DOCKER_CONTAINERIZATION_PLAN.md](DOCKER_CONTAINERIZATION_PLAN.md) - Docker Containerization (Phase 23)
- [FEATURE_SUGGESTIONS_BRAINSTORM.md](FEATURE_SUGGESTIONS_BRAINSTORM.md) - Innovation pipeline ideas
- [ROADMAP_FEEDBACK.md](ROADMAP_FEEDBACK.md) - PM review & strategic recommendations

---

**Updated**: February 15, 2026
- **Phase 23 ✅ COMPLETE**: Docker Containerization with security hardening
  - Multi-stage Dockerfiles (backend + frontend), Compose profiles (ollama, full)
  - Nginx reverse proxy with CSP headers, non-root containers, least-privilege Postgres
  - Ollama retry logic (tenacity), prompts.py refactored into package
  - CTE support added to SQL lineage parser
- **Phase 24 NEW**: Observability & Monitoring (OpenTelemetry, Prometheus, Grafana)
- Previous: Added Phase 20-22, Innovation Pipeline, promoted Security to CRITICAL
