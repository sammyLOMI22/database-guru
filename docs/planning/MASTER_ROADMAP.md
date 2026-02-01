# Database Guru - Master Development Roadmap

**Last Updated**: February 1, 2026
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

    ┌──────────────────────┐  ┌──────────────────────┐
    │   Data Lineage       │  │ Lineage Intelligence │
    │   (Phase 11)         │  │   (Phase 12)         │
    │   185 tests passing  │  │   151 tests passing  │
    │   ✅ COMPLETE        │  │   ✅ COMPLETE        │
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
    │                          DATA SOURCE EXPANSION (Phase 13) - NEW                         │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                      CSV & EXCEL FILE SUPPORT (Phase 13) - HIGH PRIORITY                 │
    │                                                                                           │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                   │
    │  │ 13.1 Core   │   │ 13.2 DuckDB │   │ 13.3 Cross- │   │ 13.4 Frontend│                  │
    │  │ Backend     │──▶│ Integration │──▶│ Source      │──▶│ UI          │                   │
    │  │             │   │             │   │ Queries     │   │             │                   │
    │  │ • File      │   │ • Virtual   │   │             │   │ • Upload    │                   │
    │  │   upload    │   │   tables    │   │ • DB + File │   │   modal     │                   │
    │  │ • Schema    │   │ • CSV/Excel │   │   JOINs     │   │ • Data      │                   │
    │  │   inference │   │   parsing   │   │ • Result    │   │   sources   │                   │
    │  │ • Storage   │   │ • Query     │   │   merging   │   │   panel     │                   │
    │  │             │   │   execution │   │             │   │ • Preview   │                   │
    │  │ ~5 days     │   │ ~5 days     │   │ ~5 days     │   │ ~5 days     │                   │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                   │
    │                                                                                           │
    │  Prereq: None (Independent) | Priority: HIGH | Est: 3-4 weeks | ~2,500 lines            │
    │  Plan: CSV_EXCEL_SUPPORT_PLAN.md                                                         │
    └───────────────────────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                         NOSQL EXPANSION (Phase 14) - DATA SOURCES                       │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                    NOSQL DATABASE SUPPORT (Phase 14) - MEDIUM PRIORITY                   │
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
    │  Prereq: None (Independent) | Priority: MEDIUM | Est: 6-8 weeks | ~6,000 lines          │
    │  Plan: NOSQL_EXPANSION_PLAN.md                                                           │
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
    │                              SECURITY & INFRASTRUCTURE                                   │
    │                                  (Lower Priority)                                        │
    └─────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
    │   Authorization      │  │   Session Expiration │  │   Rate Limiting      │
    │   System             │  │   (TTL, cleanup)     │  │   (Per-user)         │
    │   CRITICAL but       │  │   Est: 2 days        │  │   Est: 2-3 days      │
    │   user deferred      │  │   MEDIUM priority    │  │   LOW priority       │
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


    INDEPENDENT FEATURES (Can Start Anytime):
    =========================================

    ┌───────────────────────────────────────────────────────────────────┐
    │        CSV & EXCEL FILE SUPPORT (Phase 13) ◀── HIGH PRIORITY      │
    │                                                                   │
    │  • Upload CSV/Excel as data sources                               │
    │  • Query files alongside databases                                │
    │  • Cross-source JOINs (file + DB)                                 │
    │  • Est: 3-4 weeks | Plan: CSV_EXCEL_SUPPORT_PLAN.md               │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        NOSQL DATABASE EXPANSION (Phase 14) ◀── MEDIUM PRIORITY    │
    │                                                                   │
    │  • MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch             │
    │  • Schema inference for schema-less databases                     │
    │  • Natural language to native query languages                     │
    │  • Est: 6-8 weeks | Plan: NOSQL_EXPANSION_PLAN.md                 │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        LLM PROVIDER EXPANSION (Phase 15) ◀── HIGH PRIORITY        │
    │                                                                   │
    │  • Azure OpenAI, OpenAI, Anthropic, Vertex AI, Bedrock            │
    │  • Local alternatives: LM Studio, vLLM                            │
    │  • Multi-provider routing with automatic fallback                 │
    │  • Est: 3-4 weeks | Plan: LLM_PROVIDER_EXPANSION_PLAN.md          │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │        LLM USAGE MONITORING (Phase 16) ◀── MEDIUM PRIORITY        │
    │                                                                   │
    │  • Track token usage across all 23+ agents                        │
    │  • Dashboard with charts and per-agent analytics                  │
    │  • Inline chat usage display per message/session                  │
    │  • Est: 2 weeks | Plan: LLM_USAGE_MONITORING_PLAN.md              │
    └───────────────────────────────────────────────────────────────────┘


    DEPENDENT FEATURES (Requires Prerequisites):
    ============================================

    ┌───────────────────────────────────────────────────────────────────┐
    │   MULTI-PROVIDER MONITORING (Phase 17) ◀── MEDIUM PRIORITY        │
    │                                                                   │
    │   REQUIRES: Phase 15 (Providers) + Phase 16 (Monitoring)          │
    │                                                                   │
    │  • Native token counts from OpenAI, Anthropic, Google, etc.       │
    │  • Accurate cost tracking per provider/model                      │
    │  • Provider performance comparison dashboard                      │
    │  • Est: 1-2 weeks | Plan: MULTI_PROVIDER_MONITORING_INTEGRATION.md│
    └───────────────────────────────────────────────────────────────────┘

            ┌─────────────────┐          ┌─────────────────┐
            │   Phase 15      │          │   Phase 16      │
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
```

---

## Recommended Next Steps

### Priority 1: Lineage Intelligence Phase 12 ✅ COMPLETE
**Status**: All 5 sub-phases implemented (151 tests passing, ~11,266 lines)
- **12.1 Lineage Narrator** ✅: Natural language explanations of data lineage graphs
- **12.2 Impact Advisor** ✅: Migration plans, SQL patches, risk explanations
- **12.3 Schema Health Analyzer** ✅: Database design quality scoring with index suggestions
- **12.4 Pattern Intelligence** ✅: Query anti-pattern detection and optimization suggestions
- **12.5 Lineage Conversation Agent** ✅: Multi-turn Q&A about schema/lineage
- New shared utility: `src/lineage/llm_utils.py` for JSON extraction
- See: [LINEAGE_INTELLIGENCE_USER_GUIDE.md](../guides/LINEAGE_INTELLIGENCE_USER_GUIDE.md)

### Priority 2: Table Sorting ✅ COMPLETE
**Status**: Implemented with reusable hook and accessible component
- Click column header to sort (asc/desc toggle)
- Smart type detection (numbers, dates, strings)
- Keyboard accessible (Enter/Space to sort)
- Visual indicators with Lucide icons
- Integrated into QueryResults, MultiDatabaseResults, StreamingQueryResults

### Priority 4: CSV & Excel File Support (Phase 13) - NEW
**Why**: Major capability expansion - users can analyze spreadsheets alongside databases
- **13.1 Core Backend**: File upload, storage, schema inference
- **13.2 DuckDB Integration**: Virtual tables, CSV/Excel parsing, query execution
- **13.3 Cross-Source Queries**: Database + File JOINs, result merging
- **13.4 Frontend UI**: Upload modal, unified data sources panel, file preview
- See: [CSV_EXCEL_SUPPORT_PLAN.md](CSV_EXCEL_SUPPORT_PLAN.md) for full implementation details

**Key Use Cases**:
- Upload sales.csv and query it with natural language
- JOIN uploaded prospects.xlsx with production CRM database
- Combine multiple spreadsheets into a single analysis

**Technical Approach**: Leverages existing DuckDB integration for file queries

### Priority 5: NoSQL Database Expansion (Phase 14) - NEW
**Why**: Extend natural language querying to document, key-value, wide-column, and search databases
- **14.1 MongoDB**: MQL generation, aggregation pipelines, schema inference
- **14.2 Redis**: Command generation for all data types, RediSearch
- **14.3 Cassandra**: CQL generation with partition-key awareness
- **14.4 DynamoDB**: PartiQL and boto3 API, GSI optimization
- **14.5 Elasticsearch**: Query DSL with aggregations and highlighting
- See: [NOSQL_EXPANSION_PLAN.md](NOSQL_EXPANSION_PLAN.md) for full implementation details

**Key Use Cases**:
- Natural language queries for MongoDB collections
- Unified interface across all NoSQL database types
- Schema inference for schema-less databases

**Technical Approach**: Database-specific query generators with unified interface

### Priority 6: LLM Provider Expansion (Phase 15) - NEW
**Why**: Enterprise integration and model flexibility - users can leverage cloud LLMs
- **15.1 Provider Abstraction**: Unified interface, registry, refactor Ollama
- **15.2 Azure OpenAI**: Enterprise-first cloud provider with deployment support
- **15.3-15.6 Additional Providers**: OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM
- **15.7-15.9 Enhanced Routing**: Multi-provider routing, fallback chains, frontend config UI
- See: [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) for full implementation details

**Key Use Cases**:
- Connect to existing Azure OpenAI infrastructure
- Use GPT-4 or Claude for complex queries, Ollama for simple ones
- Automatic fallback when primary provider is unavailable
- Cost optimization by routing cheaper tasks to cheaper providers

**Technical Approach**: Abstract provider interface with pluggable implementations

### Priority 7: LLM Usage Monitoring (Phase 16) - NEW
**Why**: Visibility into LLM resource consumption across all agents
- **16.1 Core Infrastructure**: LLMUsage table, tracker service, API endpoints
- **16.2 Agent Integration**: Update SQL Generator, Result Narrator, Query Planning, Lineage agents
- **16.3 Dashboard Frontend**: Stats cards, time series charts, agent breakdown, recent calls table
- **16.4 Inline Chat Stats**: Per-message token display, session totals, collapsible detail view
- See: [LLM_USAGE_MONITORING_PLAN.md](LLM_USAGE_MONITORING_PLAN.md) for full implementation details

**Key Use Cases**:
- Track which agents consume the most tokens
- View usage per chat session
- Dashboard showing usage trends over time
- Debug and optimize LLM calls

**Technical Approach**: Centralized tracker service with database persistence

### Priority 8: Multi-Provider Monitoring Integration (Phase 17) - NEW
**Why**: Extend monitoring to all LLM providers with accurate cost tracking
- **Prerequisite**: Requires BOTH Phase 15 (Provider Expansion) AND Phase 16 (Usage Monitoring)
- **17.1 Token Extractors**: Provider-specific token extraction (OpenAI, Anthropic, Google formats)
- **17.2 Provider Updates**: Enrich responses with native token counts and costs
- **17.3 API & Schema**: Add provider column, cost endpoints, comparison APIs
- **17.4 Dashboard Widgets**: Cost by provider chart, provider comparison table, cost trends
- See: [MULTI_PROVIDER_MONITORING_INTEGRATION.md](MULTI_PROVIDER_MONITORING_INTEGRATION.md) for full details

**Key Use Cases**:
- Compare costs across providers (OpenAI vs Anthropic vs Ollama)
- Track actual spend with real provider pricing
- Optimize routing based on cost/performance data
- Provider performance comparison by task type

**Technical Approach**: Provider-specific token extractors feeding unified monitoring system

---

## Summary by Category

| Category | Features | Status | Total Effort |
|----------|----------|--------|--------------|
| **Visualization** | ER Diagrams, Data Lineage | Phase 7 ✅, Phase 11 ✅ | COMPLETE |
| **LLM Intelligence** | Lineage Narrator, Impact Advisor, Schema Health, Pattern Intel, Lineage Chat | **Phase 12 ✅ COMPLETE** | ~11,266 lines |
| **Data Sources** | CSV & Excel File Support | **Phase 13 - PLANNED** | ~2,500 lines |
| **NoSQL Expansion** | MongoDB, Redis, Cassandra, DynamoDB, Elasticsearch | **Phase 14 - PLANNED** | ~6,000 lines |
| **LLM Integration** | Azure OpenAI, OpenAI, Anthropic, Vertex AI, Bedrock, LM Studio, vLLM | **Phase 15 - PLANNED** | ~3,000 lines |
| **LLM Monitoring** | Token usage tracking, dashboard, inline stats (Ollama) | **Phase 16 - PLANNED** | ~1,500 lines |
| **Multi-Provider Monitoring** | Native tokens, cost tracking, provider comparison | **Phase 17 - PLANNED** (needs 15+16) | ~1,200 lines |
| **Edit Mode & DML** | Inline editing, INSERT/UPDATE/DELETE, natural language DML | **Phase 18 - PLANNED** | ~4,000 lines |
| **Insight Quality** | Preprocessing, Pattern Learning | Not started | ~1,200 lines |
| **Table UX** | Sorting ✅, Resizing, Export | Sorting complete | ~400 lines remaining |
| **Performance** | Streaming Results | Future | ~1,500 lines |
| **Security** | Auth, Rate Limiting | Deferred | ~2,000 lines |

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
| Table Sorting | Click-to-sort columns, smart type detection | 24 tests |

**Total Tests**: 950+ passing

---

## Upcoming Phases Summary

| Phase | Feature | Dependencies | Est. Effort | Priority |
|-------|---------|--------------|-------------|----------|
| **Phase 13** | CSV & Excel File Support | None | ~2,500 lines | HIGH |
| **Phase 14** | NoSQL Database Expansion | None | ~6,000 lines | MEDIUM |
| **Phase 15** | LLM Provider Expansion | None | ~3,000 lines | HIGH |
| **Phase 16** | LLM Usage Monitoring | None | ~1,500 lines | MEDIUM |
| **Phase 17** | Multi-Provider Monitoring | Phase 15 + 16 | ~1,200 lines | MEDIUM |
| **Phase 18** | Edit Mode & DML Operations | None | ~4,000 lines | MEDIUM |
| **Phase 19** | Data Insights Enhancement | None | ~1,800 lines | MEDIUM |

---

## Source Documents

- [FUTURE_PLANS.md](FUTURE_PLANS.md) - Core roadmap
- [ADVANCED_VISUALIZATION_PHASE2_PLAN.md](ADVANCED_VISUALIZATION_PHASE2_PLAN.md) - Visualization features
- [SMALL_MODEL_OPTIMIZATION_PHASE2.md](SMALL_MODEL_OPTIMIZATION_PHASE2.md) - LLM optimization features
- [DATA_LINGEAGE_PLAN.md](DATA_LINGEAGE_PLAN.md) - Data Lineage & Impact Analysis plan (Phase 11)
- [LINEAGE_INTELLIGENCE_PLAN.md](LINEAGE_INTELLIGENCE_PLAN.md) - LLM-Powered Lineage Intelligence (Phase 12)
- [CSV_EXCEL_SUPPORT_PLAN.md](CSV_EXCEL_SUPPORT_PLAN.md) - CSV & Excel File Support (Phase 13)
- [NOSQL_EXPANSION_PLAN.md](NOSQL_EXPANSION_PLAN.md) - NoSQL Database Expansion (Phase 14)
- [LLM_PROVIDER_EXPANSION_PLAN.md](LLM_PROVIDER_EXPANSION_PLAN.md) - LLM Provider Expansion (Phase 15)
- [LLM_USAGE_MONITORING_PLAN.md](LLM_USAGE_MONITORING_PLAN.md) - LLM Usage Monitoring (Phase 16)
- [MULTI_PROVIDER_MONITORING_INTEGRATION.md](MULTI_PROVIDER_MONITORING_INTEGRATION.md) - Multi-Provider Monitoring (Phase 17)
- [EDIT_MODE_DML_PLAN.md](EDIT_MODE_DML_PLAN.md) - Edit Mode & DML Operations (Phase 18)
- [DATA_INSIGHTS_ENHANCEMENT_PLAN.md](DATA_INSIGHTS_ENHANCEMENT_PLAN.md) - Data Insights Enhancement (Phase 19)

---

**Updated**: February 1, 2026 (Added Phase 19: Data Insights Enhancement for multi-source insights and charts)
