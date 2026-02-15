# Visual Data Flow & Lineage

## 1. High-Level Data Flow (User to Insight)

```mermaid
graph TD
    User[User] -->|Natural Language Query| UI[Frontend: Chat Interface]
    UI -->|POST /api/chat| API[Backend: Chat Router]
    
    subgraph "Reasoning Engine"
        API -->|Retrieve Context| Mem[Conversational Memory Service]
        Mem -->|Fetch History| DB[(App Database)]
        API -->|Construct Prompt| Prompt[Prompt Builder]
        Prompt -->|Sanitized Prompt| LLM_Client[Ollama Client]
        LLM_Client -->|Generate SQL| LLM[Ollama API (Container)]
    end
    
    subgraph "Execution Engine"
        LLM -->|Raw SQL| Parser[SQL Lineage Parser]
        Parser -->|Extract Lineage| LineageGraph[Lineage Graph Model]
        Parser -->|Validate SQL| Validator[Query Validator]
        Validator -->|Execute| TargetDB[(Target Database: Postgres/DuckDB/SQLite)]
        TargetDB -->|Result Rows| Validator
    end
    
    subgraph "Narrative Engine"
        Validator -->|Results + Metadata| Narrator[Result Narrator Service]
        Narrator -->|Analyze Statistics| Stats[Statistical Analyzer]
        Stats -->|Enriched Context| LLM_Client
        LLM_Client -->|Generate Narrative| LLM
        LLM -->|Natural Language Answer| Narrator
    end
    
    Narrator -->|JSON Response| UI
    UI -->|Render Chart/Table| User
```

## 2. Data Lineage Logic (SQL Parsing)

When a query is generated, the `SQLLineageParser` extracts the flow:

```text
[Source Tables] 
      |
      +--- [Filter/Join Logic] (WHERE, ON)
      |
      v
[Transformations] (Aggregations, Functions, Expressions)
      |
      v
[Output Columns]
```

**Example Lineage Flow:**

*   **Input SQL:** `SELECT department, COUNT(*) as count FROM employees JOIN depts ON employees.dept_id = depts.id GROUP BY department`
*   **Trace:**
    1.  **Sources:** `employees` (table), `depts` (table)
    2.  **Joins:** `employees.dept_id` <-> `depts.id`
    3.  **Transformation:** `COUNT(*)` (Aggregation)
    4.  **Output:** `department` (Direct from `depts.name`?), `count` (Calculated)

## 3. Docker Deployment Flow

```mermaid
graph TD
    Ext[External Network] -->|Port 3000| Nginx[Nginx Proxy]
    
    subgraph "Docker Network (dbguru)"
        Nginx -->|/api/*| Backend[Backend Service]
        Nginx -->|/*| Frontend[Frontend Static]
        
        Backend -->|SQL| Postgres[Postgres DB (Full Profile)]
        Backend -->|Cache| Redis[Redis Cache (Full Profile)]
        Backend -->|Inference| Ollama[Ollama LLM]
    end
    
    Backend -.->|Default| SQLite[(SQLite File)]
```
