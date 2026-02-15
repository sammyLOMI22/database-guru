# Visual Flow: Data, SQL, and Agents

## 1. High-Level Data Flow (Production Docker Environment)

```mermaid
graph TD
    User((User)) ── HTTP/3000 ──► Nginx{Nginx Proxy}

    subgraph "Docker Stack (dbguru)"
        Nginx ── Proxy API ──► Backend[Backend API]
        Nginx ── Static ──► Frontend[Frontend Assets]

        Backend ── SQLAlchemy ──► Postgres[(Metadata DB)]
        Backend ── Redis Protocol ──► Redis[(Cache)]
        Backend ── REST API ──► Ollama[Ollama LLM]

        Backend ── Connector ──► TargetDB[(Target User DB)]
    end

    subgraph "Volumes"
        Postgres ── Persistence ──► Vol1[(postgres-data)]
        Ollama ── Models ──► Vol2[(ollama-models)]
        Backend ── Files ──► Vol3[(dbguru-data)]
    end
```

## 2. SQL Generation & Validation Pipeline

1.  **Request:** User sends question + session_id.
2.  **Context Retrieval:** `ConversationalMemoryAgent` fetches last N messages from Postgres.
3.  **Schema Introspection:** `SchemaInspector` fetches current schema (cached or live) from Target DB.
4.  **Prompt Composition:** `PromptBuilder` combines:
    *   `SYSTEM_PROMPT` (Rules/Safety)
    *   `DIALECT_RULES` (Postgres/SQLite/DuckDB)
    *   `SCHEMA_DATA` (Tables/Columns/FKs)
    *   `FEW_SHOT_EXAMPLES` (Pattern matching)
    *   `INTENT_INSTRUCTIONS` (Aggregation vs Lookup)
5.  **Inference:** `OllamaClient` calls Ollama container.
6.  **Lineage Extraction:** `SQLLineageParser` runs on generated SQL.
7.  **Safety Check:** `QueryValidator` verifies read-only status and schema alignment.
8.  **Execution:** `SQLExecutor` runs query on Target DB.

## 3. Agentic Flow (Self-Correction & Narrative)

```mermaid
sequence_flow
    User -> Agent: "Show me sales by region"
    Agent -> LLM: Generate SQL
    LLM -> Agent: SELECT region, total FROM sales
    Agent -> TargetDB: Execute
    TargetDB -> Agent: ERROR: column "total" does not exist
    Agent -> LLM: "Fix this SQL. Error was..."
    LLM -> Agent: SELECT region, amount FROM sales
    Agent -> TargetDB: Execute
    TargetDB -> Agent: [Results Data]
    Agent -> Lineage: Parse Flow
    Agent -> Narrator: Analyze Results
    Narrator -> LLM: "Summarize these statistics..."
    LLM -> Narrator: "Sales are highest in West region..."
    Narrator -> User: Answer + Data + SQL + Lineage Graph
```

## 4. Lineage Logic Flow

```text
SQL: WITH dept_avg AS (SELECT dept_id, AVG(salary) as avg_sal FROM emps GROUP BY dept_id)
     SELECT name, avg_sal FROM depts JOIN dept_avg ON depts.id = dept_avg.dept_id

Trace:
1. Identify CTE "dept_avg":
   - Source: emps (table)
   - Columns: dept_id, salary
   - Transformation: AVG (Aggregation)
2. Identify Main Query:
   - Source: depts (table), dept_avg (CTE)
   - Join: depts.id <-> dept_avg.dept_id
3. Resolve Lineage:
   - Output "name" <── [Direct] <── depts.name
   - Output "avg_sal" <── [Aggregation] <── emps.salary
```
