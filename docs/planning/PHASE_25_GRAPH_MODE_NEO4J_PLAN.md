# Phase 25 — Graph Mode (Neo4j) Implementation Plan

**Status**: Planning
**Branch**: `phase-25-graph-mode-Neo4J`
**Spec**: [database_guru_graph_database_support_spec.md](./database_guru_graph_database_support_spec.md)
**Priority**: HIGH (next major DB-type expansion after Phase 14 NoSQL)
**Estimated Effort**: ~5,500 LOC (backend ~2,800 / frontend ~2,400 / tests ~300 fixtures + ~120 test cases)
**Est. Duration**: 5–6 weeks across 6 sub-phases (25.1 → 25.6), each shippable independently

---

## 1. Goals

Add Neo4j as a first-class database type so users can:

1. Save, test, edit, soft-delete Neo4j connections from the existing Connections UI.
2. Introspect graph schema (labels, relationship types, patterns, properties, indexes, constraints) and cache it.
3. Ask graph questions in natural language → Cypher → execute → render results as **table / JSON / graph**.
4. Run hand-written Cypher in a dedicated **Query Lab** with safety classification (read-only by default, dangerous patterns blocked).
5. Visually explore the graph (start label → filter → expand → traversal depth), with truncation guards.
6. Receive rule-based + AI-generated **modeling and index advice**.

Non-goals for MVP (matches spec §3 exclusions): Neptune/Memgraph/ArangoDB/JanusGraph/Gremlin, GraphQL generation, automatic graph migrations, multi-user collaboration, full analytics algorithms (PageRank, community detection), relational-to-graph ETL.

---

## 2. Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Connection persistence | **Reuse `DatabaseConnection`** with `database_type='neo4j'` | Inherits encryption (`password_encrypted`), soft-delete (`is_deleted`), owner FK, audit hooks, Admin UI; matches Phase 14 NoSQL pattern. Diverges from spec §9's separate `graph_connections` table — see §3.1 for how spec fields are mapped. |
| UI surface | **Hybrid**: Neo4j in chat (NL → Cypher, render as graph/table/JSON) **AND** dedicated **Graph** tab (Schema / Visual Explorer / Query Lab / Guru Advice) | Chat reuses existing pipeline; the Graph tab is the only place that fits Cytoscape canvas, depth/traversal controls, and modeling advisor cards. |
| Visualization library | **Cytoscape.js** | Spec's recommendation; purpose-built; cose/fcose layouts handle dense graphs; truncation cap (200 nodes / 500 edges default) prevents WebGL/perf cliffs. |
| Backend module layout | `src/graph/` mirroring `src/nosql/` (adapter / handler / pool / generator / executor / schema_inspector / error_classifier) | Same shape engineers already know; future graph providers (Memgraph, Neptune) drop in alongside `neo4j/`. |
| Dialect | Add `DatabaseDialect.NEO4J = "neo4j"` to `src/llm/dialect_registry.py` | Routes prompts/templates correctly; NoSQL enums already bypass SQL-only rules. |
| Driver | Official `neo4j` Python driver (async) | Bolt protocol, server-side timeouts, parameterized queries. |
| Query safety | New `GraphQuerySafetyService` returning `read_only | write | admin | dangerous | unknown` (spec §12) | Reuses pattern from `src/dml/dml_validator.py` philosophy: classify before execute; MVP blocks anything not `read_only`. |
| Read-only enforcement | Two layers: (a) safety classifier in app, (b) Neo4j session opened with `default_access_mode=READ` when `read_only=True` on connection | Defense in depth; even if classifier misses, driver refuses writes. |

---

## 3. Backend Design

### 3.1 Data model — extending existing tables

**`database_connections`** (no schema change required for MVP — all Neo4j fields fit existing columns):

| Existing column | Neo4j usage |
|---|---|
| `database_type` | `'neo4j'` |
| `host` | Full Bolt URI (e.g. `bolt://localhost:7687` or `neo4j+s://x.databases.neo4j.io`) |
| `port` | Nullable (URI carries it) |
| `database_name` | Neo4j database name (default `'neo4j'`) |
| `username` | Neo4j user |
| `password_encrypted` | Encrypted password (existing Fernet layer) |
| `schema_cache` | Cached normalized `GraphSchema` JSON |
| `schema_updated_at` | Last introspection timestamp |

**New optional columns on `database_connections`** (single Alembic migration):

```python
# Migration: add_neo4j_connection_flags.py
op.add_column('database_connections', sa.Column('encrypted', sa.Boolean(), nullable=True))       # Bolt TLS
op.add_column('database_connections', sa.Column('read_only', sa.Boolean(), nullable=False, server_default='true'))
```

Both are NULL/no-op for non-graph rows. `read_only` defaults to `true` per spec §5.1.

**New table `graph_query_history`** (spec §9, mirrors `query_history` semantics):

```python
class GraphQueryHistory(Base):
    __tablename__ = "graph_query_history"
    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cypher = Column(Text, nullable=False)
    params_json = Column(JSON, nullable=True)
    status = Column(String(20))                   # success | error | blocked
    safety_level = Column(String(20))             # read_only | write | admin | dangerous | unknown
    duration_ms = Column(Integer, nullable=True)
    record_count = Column(Integer, nullable=True)
    truncated = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
```

**`saved_graph_queries`** (spec §9): defer to Phase 25.3 only if user-facing "Save query" button ships in MVP; otherwise drop to Phase 26.

### 3.2 Module layout

```text
src/graph/
  __init__.py
  base.py                      # GraphAdapter Protocol — provider-agnostic
  router.py                    # is_graph(db_type) + execute_graph_query() — mirrors src/nosql/router.py
  result_formatter.py          # Neo4j Record → unified {records, graph_viz, table_columns}
  safety/
    classifier.py              # cypher → GraphQuerySafetyLevel; uses regex + tokenizer
    rules.py                   # DANGEROUS_KEYWORDS, ALLOWED_PROCEDURES
  schema/
    normalizer.py              # raw introspection rows → GraphSchema dataclass
    advisor_rules.py           # Phase 25.6 rule-based checks (missing index, overloaded label, etc.)
  neo4j/
    __init__.py
    handler.py                 # GraphAdapter impl; orchestrates connect/introspect/execute
    driver_pool.py             # async neo4j.AsyncGraphDatabase.driver pool keyed by connection_id
    schema_inspector.py        # CALL db.labels(), db.relationshipTypes(), schema.nodeTypeProperties, etc.
    cypher_generator.py        # NL → Cypher via LLM with schema context (extends model_router pattern)
    cypher_explainer.py        # Cypher → plain-English explanation
    query_executor.py          # parameterized exec with timeout, READ/WRITE mode, record cap
    error_classifier.py        # Neo4j error codes → ErrorType (mirrors src/nosql/mongodb/error_classifier.py)
```

### 3.3 GraphSchema dataclass (spec §5.3 in Python)

```python
# src/graph/schema/normalizer.py
@dataclass
class GraphProperty:
    name: str
    types: List[str]          # ["String"], ["Integer", "Null"]
    indexed: bool = False
    nullable: Optional[bool] = None
    sample_values: Optional[List[Any]] = None

@dataclass
class GraphNodeLabel:
    name: str
    estimated_count: Optional[int] = None
    properties: List[GraphProperty] = field(default_factory=list)

@dataclass
class GraphRelationshipType:
    name: str
    estimated_count: Optional[int] = None
    properties: List[GraphProperty] = field(default_factory=list)

@dataclass
class GraphRelationshipPattern:
    source_labels: List[str]
    relationship_type: str
    target_labels: List[str]
    estimated_count: Optional[int] = None

@dataclass
class GraphIndex:
    name: str
    entity_type: Literal["NODE", "RELATIONSHIP"]
    labels_or_types: List[str]
    properties: List[str]
    type: Optional[str] = None        # BTREE, RANGE, TEXT, POINT, FULLTEXT, LOOKUP
    state: Optional[str] = None       # ONLINE, POPULATING, FAILED

@dataclass
class GraphConstraint:
    name: str
    entity_type: Literal["NODE", "RELATIONSHIP"]
    labels_or_types: List[str]
    properties: List[str]
    type: str                         # UNIQUENESS, NODE_KEY, NODE_PROPERTY_EXISTENCE, etc.

@dataclass
class GraphSchema:
    provider: str                     # "neo4j"
    database_name: str
    labels: List[GraphNodeLabel]
    relationships: List[GraphRelationshipType]
    patterns: List[GraphRelationshipPattern]
    indexes: List[GraphIndex]
    constraints: List[GraphConstraint]
    collected_at: datetime
    warnings: List[str] = field(default_factory=list)   # "sampling incomplete", etc.
```

Same shape serializes 1:1 to the spec's TypeScript interface (camelCase via Pydantic alias).

### 3.4 Introspection queries (spec §5.2)

Run in parallel via `asyncio.gather` for fast introspection:

```cypher
-- 1. Labels
CALL db.labels() YIELD label

-- 2. Relationship types
CALL db.relationshipTypes() YIELD relationshipType

-- 3. Node properties + types
CALL db.schema.nodeTypeProperties()
YIELD nodeType, propertyName, propertyTypes, mandatory

-- 4. Rel properties + types
CALL db.schema.relTypeProperties()
YIELD relType, propertyName, propertyTypes, mandatory

-- 5. Indexes
SHOW INDEXES YIELD name, entityType, labelsOrTypes, properties, type, state

-- 6. Constraints
SHOW CONSTRAINTS YIELD name, entityType, labelsOrTypes, properties, type

-- 7. Approximate label counts (sampled)
MATCH (n:`<label>`) RETURN count(n) AS c                  -- per-label, capped by ${MAX_LABELS_TO_COUNT}=100

-- 8. Relationship pattern discovery (sampled, spec §5.2)
MATCH (a)-[r]->(b)
WITH labels(a) AS sa, type(r) AS rt, labels(b) AS tb, count(*) AS c
RETURN sa, rt, tb, c
ORDER BY c DESC
LIMIT 100
```

Sampling guards (in `schema_inspector.py`):
- Skip count queries on any label where `db.stats.retrieve('GRAPH COUNTS')` estimates > 10M nodes.
- Per-query timeout: 5s (configurable via `GRAPH_INTROSPECTION_TIMEOUT_MS`).
- Append warning to `GraphSchema.warnings` rather than failing the whole introspection.

### 3.5 Cypher safety classifier (spec §12)

```python
# src/graph/safety/classifier.py
class GraphQuerySafetyLevel(str, Enum):
    READ_ONLY = "read_only"
    WRITE     = "write"
    ADMIN     = "admin"
    DANGEROUS = "dangerous"
    UNKNOWN   = "unknown"

DANGEROUS_KEYWORDS = {
    "CREATE", "MERGE", "DELETE", "DETACH DELETE", "REMOVE", "SET", "DROP",
    "LOAD CSV", "CALL dbms", "CALL apoc.cypher.runWrite", "CALL apoc.periodic",
    "USING PERIODIC COMMIT",
}
ALLOWED_PROCEDURES = {
    "db.labels", "db.relationshipTypes", "db.schema.nodeTypeProperties",
    "db.schema.relTypeProperties", "db.indexes", "db.constraints",
    "db.schema.visualization", "apoc.meta.schema",   # opt-in only
}

def classify(cypher: str) -> GraphQuerySafetyLevel: ...
```

Algorithm:
1. Strip string literals + `/* */` and `//` comments to avoid keyword false-positives.
2. Tokenize uppercased.
3. If any `DANGEROUS_KEYWORDS` matches → `WRITE` / `DANGEROUS` per table in spec §12.
4. If `CALL` present, ensure the FQN is in `ALLOWED_PROCEDURES` else `ADMIN`.
5. If parse fails (sentinel: empty result + unbalanced parens) → `UNKNOWN`.
6. Else → `READ_ONLY`.

MVP behavior: `READ_ONLY` → allow; everything else → 400 with `blocked_reason` payload. Frontend renders the reason + the spec §13 plain-English explanation.

### 3.6 Cypher generation (spec §5.5)

`src/graph/neo4j/cypher_generator.py` — same shape as `src/nosql/mongodb/mql_generator.py`:

```python
async def generate_cypher(
    prompt: str,
    schema: GraphSchema,
    read_only: bool = True,
    *,
    model_router: ModelRouter,
    usage_tracker: LLMUsageTracker,
) -> GeneratedCypher:
    """
    Returns: cypher (str), explanation (str), assumptions (List[str]),
             unknown_labels (List[str]), safety_level (GraphQuerySafetyLevel),
             estimated_cost (Optional[str])
    """
```

- Builds compact AI context packet per spec §5.5 (≤ 1500 tokens): only label names, rel types, top 20 patterns, indexed properties. **Never includes** node/edge data samples or passwords.
- Routes via `ModelRouter` task type `cypher_generation` (new in `TaskType` enum).
- Always appends `LIMIT 100` to generated reads unless the prompt explicitly asks otherwise.
- Tracks usage via `LLMUsageTracker.track_call(agent='cypher_generator', ...)`.
- Validates output through `classify()` and `unknown_labels` check before returning.

### 3.7 Result formatter (graph viz contract — spec §5.6)

`src/graph/result_formatter.py` walks Neo4j records and detects `Node` / `Relationship` / `Path` objects:

```python
def to_graph_viz(records: list[Record], *, max_nodes=200, max_edges=500) -> GraphVisualizationData:
    """
    Returns:
      nodes: [{id, labels, properties, displayName}]
      edges: [{id, source, target, type, properties}]
      truncated: bool
      warnings: List[str]
    """
```

Also returns `table_columns + table_rows` when records are scalar (e.g. `RETURN count(n)`).

### 3.8 Driver pool & connection lifecycle

`src/graph/neo4j/driver_pool.py`:
- Module-level dict `{connection_id: AsyncDriver}` lazily populated.
- `driver = AsyncGraphDatabase.driver(uri, auth=(user, pwd), encrypted=...)`.
- Session created per query with `default_access_mode=READ` when connection `read_only=True`.
- Driver closed on `delete_connection()` (extends existing `DatabaseConnection` cleanup) and on app shutdown.
- Each call wrapped in `asyncio.wait_for(..., timeout=query_timeout_ms / 1000)`.

### 3.9 Multi-DB Handler integration

Extend `src/core/multi_db_handler.py`:
- `_introspect_single_database()` already branches via `is_nosql()`. Add `is_graph()` branch above that → calls `src.graph.neo4j.schema_inspector.introspect()`.
- Result normalized to `GraphSchema` and stored in `DatabaseConnection.schema_cache`.
- Chat path: when **active connection set includes a graph DB**, the natural-language pipeline routes through `src.graph.router.execute_graph_query()` instead of SQL/NoSQL paths.
- Mixed SQL+Graph in one chat session: emit a separator block per connection in results, like existing multi-DB rendering.

---

## 4. API Surface

All under `src/api/endpoints/graph.py`, gated by existing auth dependencies. Mounted in `src/main.py` next to NoSQL routes.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/api/graph/connections/test` | Test Bolt connect (no save) | user |
| GET  | `/api/graph/connections/{id}/schema` | Cached schema JSON | user |
| POST | `/api/graph/connections/{id}/introspect` | Force fresh introspection | user (write-perm check) |
| POST | `/api/graph/connections/{id}/query` | Run Cypher; returns `{records, graph_viz, table, safety_level, truncated, warnings}` | user |
| POST | `/api/graph/connections/{id}/explore` | Expand from node(s) — wraps server-controlled Cypher for visual explorer | user |
| POST | `/api/graph/connections/{id}/ai/generate-cypher` | NL → Cypher + explanation | user |
| POST | `/api/graph/connections/{id}/ai/explain-cypher` | Cypher → plain-English | user |
| POST | `/api/graph/connections/{id}/ai/modeling-advice` | Rule-based + AI recommendations | user |
| GET  | `/api/graph/connections/{id}/history` | Paginated query history | user |

**Existing endpoints already cover connection CRUD** via `src/api/endpoints/connections.py` — Neo4j just goes through `database_type='neo4j'`. The new POST `/api/graph/connections/test` is a thin wrapper that calls `Neo4jAdapter.test_connection()` without writing to DB.

Pydantic schemas added to `src/models/schemas.py`: `GraphConnectionTest`, `GraphQueryRequest`, `GraphQueryResult`, `GraphVizNode`, `GraphVizEdge`, `GraphSchemaResponse`, `GeneratedCypherResponse`, `CypherExplanationResponse`, `GraphModelingAdvice`.

---

## 5. Frontend Design

### 5.1 Connection modal additions

`frontend/src/components/DatabaseConnectionModal.tsx`:
- Add **Neo4j** to the DB-type picker (12th option after the 11 from Phase 14).
- New conditional form layout when `database_type === 'neo4j'`:
  - `name` (text)
  - `uri` (text, placeholder `bolt://localhost:7687`)
  - `username` (text, default `neo4j`)
  - `password` (password)
  - `database_name` (text, default `neo4j`)
  - `encrypted` (toggle, off by default for local)
  - `read_only` (toggle, **on** by default — matches spec §5.1)
- "Test connection" button hits POST `/api/graph/connections/test`.
- Error messages map to spec §13 cases (auth failed, unreachable, unknown DB, TLS mismatch).

### 5.2 Graph tab (sidebar entry)

New top-level tab **"Graph"** in `frontend/src/components/Sidebar.tsx`, visible only when the user has at least one active Neo4j connection (or always visible with empty state). Inside, sub-tabs:

```
Graph
  ├── Overview        — GraphOverview.tsx
  ├── Schema          — GraphSchemaExplorer.tsx
  ├── Visual          — GraphVisualExplorer.tsx
  ├── Query Lab       — CypherQueryLab.tsx
  └── Guru Advice     — GraphAdvicePanel.tsx
```

New files under `frontend/src/components/graph/`:

| File | Purpose | Est. LOC |
|---|---|---|
| `GraphOverview.tsx` | DB summary card: provider, last-introspected, counts, top patterns, AI-generated summary blurb. | 180 |
| `GraphSchemaExplorer.tsx` | Tabbed view: Labels / Rel Types / Patterns / Indexes / Constraints. Click label → property table. | 320 |
| `GraphVisualExplorer.tsx` | Left panel (start label, property filter, rel filter, direction, depth, node limit). Center: Cytoscape canvas. Right: selected node/edge details + AI subgraph explanation. | 600 |
| `CypherQueryLab.tsx` | Monaco editor (cypher language def), NL prompt box, Generate/Run/Explain buttons, results tabs (Table/JSON/Graph). | 480 |
| `GraphAdvicePanel.tsx` | Cards: missing-index, overloaded label, event-as-rel, orphan nodes, performance warnings. Each card has Why + Suggested fix. | 240 |
| `GraphCanvas.tsx` | Cytoscape wrapper component, layouts (cose, dagre, fcose), zoom/pan/pin controls. Used by VisualExplorer + Query Lab graph view. | 300 |
| `useGraphSchema.ts` | TanStack Query hook for schema fetch + invalidation. | 60 |
| `graphApi.ts` | Axios wrapper for all `/api/graph/*` endpoints. | 140 |

### 5.3 Chat integration (hybrid mode)

`frontend/src/components/ChatInterface.tsx`:
- When the active connection set includes a graph DB, the NL pipeline already routes server-side. UI changes:
  - **Result rendering**: detect `graph_viz` in response payload → add a "Graph" tab next to the existing Table/JSON tabs, rendered via `GraphCanvas.tsx`.
  - **Safety badge**: show `safety_level` chip on each Cypher result (read-only/blocked).
  - **Generated query block**: render Cypher with Monaco read-only viewer instead of the SQL syntax highlighter when `query_language === 'cypher'`.

### 5.4 Library additions

```jsonc
// frontend/package.json
"dependencies": {
  "cytoscape": "^3.30.0",
  "cytoscape-fcose": "^2.2.0",
  "cytoscape-dagre": "^2.5.0",
  "@types/cytoscape": "^3.21.0",
  "monaco-editor": "<existing>",          // already in for SQL — register cypher language def
  "monaco-cypher": "^0.5.0"               // syntax + keywords
}
```

Bundle size impact: ~420KB gzip — load Cytoscape lazily via dynamic `import()` only when the Graph tab opens.

---

## 6. AI Layer Integration

### 6.1 ModelRouter

Add to `src/llm/model_router.py` `TaskType` enum:
- `CYPHER_GENERATION`
- `CYPHER_EXPLANATION`
- `GRAPH_MODELING_ADVICE`
- `GRAPH_SCHEMA_SUMMARY`

Default routes: same primary model as `SQL_GENERATION`; fallback chain unchanged. Allow per-task override in `model_router_config` table (already user-editable via Admin UI).

### 6.2 Prompt templates

New file `src/llm/prompts/graph_prompts.py`:
- `CYPHER_GENERATION_PROMPT` — embeds compact schema packet (spec §5.5 JSON).
- `CYPHER_EXPLANATION_PROMPT` — explains start node, traversal, filters, aggregations, perf notes.
- `GRAPH_MODELING_ADVICE_PROMPT` — takes rule-based findings + schema, asks LLM for prose suggestions.
- `GRAPH_SCHEMA_SUMMARY_PROMPT` — 2–3 sentence overview of the graph.

Each template has a small-model tier (Phase 19 narrative-tier pattern) so local Ollama works.

### 6.3 Usage tracking

`LLMUsageTracker` already supports any agent name. Register agent types: `cypher_generator`, `cypher_explainer`, `graph_advisor`, `graph_schema_summarizer`. Tokens flow into existing `llm_usage` table — no schema changes.

---

## 7. Observability

Reuses Phase 24 instrumentation:
- structlog: every graph endpoint emits `event='graph.query'`, `safety_level`, `duration_ms`, `record_count`, `truncated`.
- Prometheus counters: `graph_queries_total{status,safety_level}`, `graph_blocked_queries_total`, `graph_introspection_duration_seconds`, `graph_visualization_truncated_total`.
- OTEL spans wrap `Neo4jAdapter.execute()` and `schema_inspector.introspect()`.
- **Never log**: passwords, full URIs with credentials, query result data (only counts).

New gauge: `graph_active_drivers` (pool size) — flushed on shutdown.

---

## 8. Sub-Phases & Deliverables

Each sub-phase = one PR, mergeable independently. Test counts are minimums.

### Phase 25.1 — Foundation (Connection + Driver) — ~500 LOC, ~8 tests

Files:
- `src/graph/__init__.py`, `src/graph/base.py`
- `src/graph/neo4j/driver_pool.py`
- `src/graph/neo4j/handler.py` (test_connection only)
- `src/api/endpoints/graph.py` (POST `/test`)
- Alembic migration: add `encrypted`, `read_only` columns
- Frontend: add Neo4j to `DatabaseConnectionModal.tsx`
- Add `neo4j` to `requirements.txt`
- Docker Compose: add `neo4j:5-community` service (matches spec §16)

Deliverable: User can save and successfully test a Neo4j connection. Passwords encrypted at rest.

Tests:
- `tests/graph/test_neo4j_connection.py` — connect success/fail, auth fail, TLS mismatch, read-only mode.

### Phase 25.2 — Schema Introspection + Overview UI — ~800 LOC, ~15 tests

Files:
- `src/graph/neo4j/schema_inspector.py`
- `src/graph/schema/normalizer.py`
- `src/api/endpoints/graph.py` (GET `/schema`, POST `/introspect`)
- `src/core/multi_db_handler.py` — `is_graph()` branch
- Frontend: `GraphOverview.tsx`, `GraphSchemaExplorer.tsx`, `useGraphSchema.ts`, `graphApi.ts`
- Sidebar entry, Graph tab scaffolding

Deliverable: User sees labels, rel types, patterns, indexes, constraints, counts, top patterns, AI summary card.

Tests:
- `tests/graph/test_schema_introspection.py` — sampled vs full, partial-failure warnings, empty graph.
- `tests/graph/test_schema_normalizer.py` — Neo4j rows → GraphSchema mapping.
- Frontend vitest: `GraphSchemaExplorer` renders + filter state.

### Phase 25.3 — Cypher Query Lab — ~900 LOC, ~20 tests

Files:
- `src/graph/safety/classifier.py`, `src/graph/safety/rules.py`
- `src/graph/neo4j/query_executor.py`, `src/graph/result_formatter.py`
- `src/graph/neo4j/error_classifier.py`
- `src/api/endpoints/graph.py` (POST `/query`, GET `/history`)
- `src/database/models.py`: `GraphQueryHistory` + migration
- Frontend: `CypherQueryLab.tsx`, Monaco Cypher language registration
- Result tabs Table/JSON/Graph (graph tab placeholder until 25.5)

Deliverable: User runs hand-written Cypher safely; writes blocked; errors explained.

Tests:
- `tests/graph/test_safety_classifier.py` — 30+ Cypher snippets across all 5 safety levels.
- `tests/graph/test_query_executor.py` — timeout, record cap, READ mode enforcement, error mapping.
- `tests/graph/test_graph_endpoints.py` — query API auth/rate-limit/blocked-status.
- Integration test against Docker Neo4j (marked `@pytest.mark.integration`).

### Phase 25.4 — AI Cypher Generation + Explanation — ~800 LOC, ~18 tests

Files:
- `src/graph/neo4j/cypher_generator.py`, `src/graph/neo4j/cypher_explainer.py`
- `src/llm/prompts/graph_prompts.py`
- `src/llm/model_router.py` — new `TaskType` entries
- `src/llm/dialect_registry.py` — `DatabaseDialect.NEO4J`
- `src/api/endpoints/graph.py` (POST `/ai/generate-cypher`, `/ai/explain-cypher`)
- Frontend: NL prompt input + Generate/Explain buttons in `CypherQueryLab.tsx`
- Chat integration: graph queries flow through this generator when active connection is Neo4j

Deliverable: User types "show users who purchased from same category twice" → Cypher + explanation appear; ad-hoc Cypher gets plain-English explanation.

Tests:
- `tests/graph/test_cypher_generator.py` — mocked LLM, schema context packet, `unknown_labels` detection, `LIMIT` injection.
- `tests/graph/test_cypher_explainer.py` — explanation includes start node, filters, perf notes.
- Chat-pipeline integration test: NL → Cypher → execute → table response.

### Phase 25.5 — Visual Graph Explorer — ~1,400 LOC, ~12 tests

Files:
- Frontend: `GraphCanvas.tsx`, `GraphVisualExplorer.tsx`
- `src/api/endpoints/graph.py` (POST `/explore` — bounded expand)
- `src/graph/neo4j/query_executor.py` — `expand_from_node()` helper
- Lazy-load Cytoscape bundle

Deliverable: User selects label → expands node → traverses 1–3 hops with depth/limit/type filters; graph result tab in Query Lab also renders here.

Tests:
- `tests/graph/test_explore_endpoint.py` — depth cap, node cap, type filter.
- Frontend vitest: expand control state, truncation banner, node-click property panel.
- Visual smoke test: render 200 nodes / 500 edges within 1.5s on M-series local.

### Phase 25.6 — Guru Advice (Modeling + Index Recommendations) — ~700 LOC, ~14 tests

Files:
- `src/graph/schema/advisor_rules.py` — implements spec §11 rules
- LLM-generated explanations per rule trigger
- `src/api/endpoints/graph.py` (POST `/ai/modeling-advice`)
- Frontend: `GraphAdvicePanel.tsx`

Rules implemented (per spec §11):
- `MissingIndexOnLookupProperty` (id / email / slug / sku / externalId)
- `OverloadedNodeLabel` (>15 unique properties with no clear cluster)
- `RelationshipWithTooManyProperties` (>6 properties on a single rel type)
- `InconsistentRelationshipDirection`
- `OrphanNodes` (label with >0 nodes and 0 relationships)
- `HighDegreeNode` (sampled hub detection — spec §10.7 example card)

Deliverable: Guru Advice tab shows ranked cards with Why + Suggested Fix.

Tests:
- `tests/graph/test_advisor_rules.py` — fixture graphs that trigger each rule + negative cases.
- Frontend vitest: card sorting + dismissal.

---

## 9. Test Strategy

### Unit
- Safety classifier: every entry in spec §12 table + 10 tricky cases (keywords in string literals, comments).
- Schema normalizer: handles Neo4j 5.x procedure result shape variations.
- Result formatter: nodes / relationships / paths / scalars / mixed.
- Cypher generator: schema-context size cap, `LIMIT` injection, `unknown_labels` detection.

### Integration (`@pytest.mark.integration`)
- Spin up `neo4j:5-community` via `tests/conftest.py` testcontainers fixture or docker-compose.
- Run seed Cypher from spec §17.
- Cover: introspection accuracy, query exec, safety blocking, error mapping, visual data conversion.

### Frontend
- Vitest unit tests for: `GraphSchemaExplorer` filter, `CypherQueryLab` Generate flow, `GraphVisualExplorer` expand state, `GraphCanvas` truncation banner.
- Playwright E2E (defer to Phase 25.7 if budget tight): create connection → introspect → run Cypher → see graph viz.

### Manual test plan
New doc `docs/guides/testing/PHASE_25_GRAPH_MODE_TESTING.md` covering the spec §20 DoD as a checklist.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Cytoscape bundle bloat (~420KB gzip) | Dynamic import — only when Graph tab opens; users without graph DBs pay nothing. |
| Expensive `count(*)` on multi-million-node labels during introspection | Per-label timeout (5s) + skip if `db.stats` estimates exceed `GRAPH_INTROSPECTION_COUNT_CAP=10M`; warning appended to schema. |
| Safety classifier regex misses obfuscated writes | Defense in depth: also open Neo4j session with `default_access_mode=READ` when `read_only=True`. Driver itself refuses writes. |
| LLM hallucinates non-existent labels in generated Cypher | `unknown_labels` check before returning — if mismatch, ask for clarification per spec §5.5 instead of executing. |
| Driver pool leaks on connection deletion | Hook `delete_connection()` to close + remove driver from pool; idle-eviction at 30 min. |
| Phase 14 NoSQL chat assumes `is_nosql()` switch — graph might be misrouted | Add `is_graph()` and put it **above** `is_nosql()` branch (since `database_type='neo4j'` isn't in either set today). Single-line ordering risk; covered by `test_multi_db_handler_routing.py`. |
| Encryption: Neo4j Aura uses `neo4j+s://` with required TLS | URI scheme `neo4j+s` / `bolt+s` auto-enables `encrypted=True` in driver, even if toggle is off. Handler normalizes. |
| Apache APOC procedures usage | Default deny. Add `GRAPH_ALLOW_APOC=False` env flag; gate per-allowed procedure list, not blanket allow. |

---

## 11. Configuration

New env vars in `src/config/settings.py` (all defaults safe + opt-in where security-sensitive):

| Var | Default | Purpose |
|---|---|---|
| `GRAPH_MODE_ENABLED` | `True` | Master toggle |
| `GRAPH_DEFAULT_READ_ONLY` | `True` | Force read_only on new graph connections |
| `GRAPH_QUERY_TIMEOUT_MS` | `10000` | Server-side query timeout |
| `GRAPH_INTROSPECTION_TIMEOUT_MS` | `30000` | Whole-introspection cap |
| `GRAPH_INTROSPECTION_COUNT_CAP` | `10_000_000` | Skip exact count for labels larger than this |
| `GRAPH_MAX_RECORDS` | `1000` | Hard cap on records returned per query |
| `GRAPH_MAX_VIZ_NODES` | `200` | Visualization node cap |
| `GRAPH_MAX_VIZ_EDGES` | `500` | Visualization edge cap |
| `GRAPH_ALLOW_APOC` | `False` | Permit `apoc.*` calls in safety classifier |
| `GRAPH_ALLOW_WRITES` | `False` | Post-MVP: permit classified `write` queries with confirmation |

All surface read-only via `/api/settings` and render in Admin → Health → Graph Mode panel.

---

## 12. Docs

Files to add or update:

| Path | Action |
|---|---|
| `docs/guides/GRAPH_MODE_USER_GUIDE.md` | New — Connection setup, schema explorer, Cypher lab, visual explorer, advisor cards. |
| `docs/guides/testing/PHASE_25_GRAPH_MODE_TESTING.md` | New — Manual test plan tied to spec §20 DoD. |
| `docs/technical/CYPHER_SAFETY.md` | New — Classifier rules, why blocked, escape hatches. |
| `CLAUDE.md` | Update — Add `Neo4j Adapter`, `Graph Schema Service`, `Cypher Safety` rows to the agents table; add `Graph` to supported databases; add Phase 25 env vars. |
| `docs/planning/MASTER_ROADMAP.md` | Update — Add Phase 25 block; mark sub-phases as they ship. |
| `docs/guides/DOCKER_DEPLOYMENT_GUIDE.md` | Update — Add `neo4j` service block + optional `graph` profile. |

---

## 13. MVP Definition of Done (mirrors spec §20)

- [ ] User creates and tests a Neo4j connection via existing modal.
- [ ] Connection is soft-deletable and credentials are encrypted at rest.
- [ ] User introspects schema and sees labels, rel types, patterns, properties, indexes, constraints.
- [ ] User runs read-only Cypher in Query Lab; results render as table, JSON, and graph.
- [ ] Dangerous writes are blocked; error message matches spec §13 style.
- [ ] User generates Cypher from natural-language prompt using schema context.
- [ ] User receives Cypher explanation for any pasted query.
- [ ] User visually explores graph from a starting label with depth/filter controls.
- [ ] User sees at least 4 of the spec §11 advisor cards on a non-trivial graph.
- [ ] Docker Compose stands up Neo4j + Database Guru + seed data per spec §16/§17.
- [ ] Coverage: ≥85 backend tests passing + integration suite green against `neo4j:5-community`.

---

## 14. Open Questions (deferrals from spec §23)

| Q | Recommendation for this MVP |
|---|---|
| Should write queries ever be allowed? | **No for MVP.** Add `GRAPH_ALLOW_WRITES` flag (default off) for post-MVP confirmation flow. |
| Local-only LLM support for sensitive graphs? | **Already covered** — uses existing `DATA_SECURITY_LEVEL='local_only'` + Ollama path. |
| Optimize viz for debugging vs analytics? | **Debugging.** Truncation caps at 200/500. Analytics view is a Phase 26+ feature. |
| Saved prompt templates in Query Lab? | **Defer.** `saved_graph_queries` table exists in spec §9 — implement in Phase 25.7 if user demand emerges. |
| Team-shared connections? | **Already covered** by existing `owner_id` + admin-managed connections; no changes needed. |
| Relational-to-graph advisor? | **Out of MVP scope** — captured in Phase 26 backlog. |

---

## 15. Rough Sequencing & Calendar

| Sub-phase | Calendar | Blocking next? |
|---|---|---|
| 25.1 Foundation | Week 1 | Yes — all later phases need driver pool. |
| 25.2 Schema | Week 2 | Yes — AI generation needs schema context. |
| 25.3 Query Lab | Week 3 | No (visual explorer is parallelizable). |
| 25.4 AI Cypher | Week 3–4 (parallel with 25.5) | No. |
| 25.5 Visual Explorer | Week 4–5 (parallel with 25.4) | No. |
| 25.6 Guru Advice | Week 6 | — |

Each PR runs through `/ultrareview` before merge (matches established workflow).
