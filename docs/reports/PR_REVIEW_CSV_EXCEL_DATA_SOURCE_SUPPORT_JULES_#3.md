# Technical Audit Report: Phase 13 - CSV/Excel File Integration

**Date:** October 26, 2023  
**Auditor:** Jules (Senior Software Engineer, PM, Data Architect, Data Analyst)  
**Scope:** Multi-dimensional audit of CSV/Excel integration and Lineage Intelligence.

---

## 1. Persona-Based Critique

### Senior Software Engineer
*   **DRY Violations:** Found significant duplication in DuckDB query construction and path validation between `FileSourceHandler` and `FileSourceDuckDBSession`. Logic for `read_csv_auto` is repeated, increasing maintenance risk.
*   **Architectural Inconsistency:** Database queries benefit from the `SelfCorrectingSQLAgent` (which handles retries, planning, and validation), but file-based queries in `MultiDatabaseHandler` use a basic `generate_sql` call. This makes file queries less resilient to LLM hallucinations.
*   **Logic Bug:** `SQLValidator.is_read_only` (in `sql_generator.py`) uses a regex that only looks for `SELECT`. Queries starting with `WITH` (CTEs) are valid read-only operations but may trigger "Write operations not allowed" warnings or be handled incorrectly by downstream logic.

### Project Manager
*   **Definition of Done:** Phase 13 successfully enables file querying, but the lack of self-correction for files means the feature isn't "production-hardened" compared to the database integration.
*   **Technical Debt:** Duplicated file utility logic and manual session cleanup in `ChatSession` indicate that file source ownership is scattered across the core.
*   **Innovation Potential:** The move to DuckDB is a "Win" as it allows unified SQL querying across disparate file formats. Next steps should involve NoSQL integration (MongoDB/JSON) using a similar pattern.

### Data Architect
*   **Data Lineage:** `SQLLineageParser` is currently blind to CTEs. If a query uses `WITH`, the parser identifies the CTE name as a source table and misses the actual underlying tables. This breaks lineage tracing for complex analytical queries.
*   **State Management:** `FileSourceDuckDBSession` correctly uses a singleton pattern for the in-memory DuckDB instance, ensuring efficient memory usage across requests.

### Data Analyst
*   **Data Utility:** Telemetry and history for file queries are correctly captured, enabling auditing of AI-generated insights from uploaded data.
*   **Data Integrity:** Sample values are included in prompts for file sources, which is critical for helping the LLM understand inferred types (especially for dates and categories).

---

## 2. The Review Matrix

### The Wins
*   **DuckDB Engine:** Using DuckDB for in-memory file querying is an excellent architectural choice. It provides high performance and high SQL compatibility.
*   **Parallel Execution:** `MultiDatabaseHandler` correctly uses `asyncio.gather` to introspect and query multiple sources concurrently, minimizing latency.
*   **Prompt Sanitization:** The use of XML-like delimiters and strict sanitization in `ConversationalMemoryAgent` provides strong protection against prompt injection.

### Issues & Bugs
1.  **CTE Lineage Gap:** `SQLLineageParser` cannot parse `WITH` clauses.
2.  **Incomplete Read-Only Check:** `SQLValidator` misses `WITH` queries.
3.  **No Self-Correction for Files:** `MultiDatabaseHandler` bypasses the agent loop for DuckDB queries.

### Security Concerns
*   **Prompt Injection:** Current mitigations are strong, but the `is_read_only` bug might allow a user to sneak in a destructive query if it starts with `WITH` and the secondary keyword check fails. *Recommendation: Update the regex immediately.*
*   **Local File Exposure:** Path traversal is mitigated by `validate_file_path`, but we should ensure the `uploads/` directory has strict OS-level permissions.

---

## 3. Visual Flow (Phase 13 Data Flow)

```text
[ User Question ] 
      |
      v
[ MultiDatabaseHandler ]
      |
      |--[ Combined Schema Builder ]
      |     |-- [ DB Schema ] <--- [ PostgreSQL/MySQL/SQLite ]
      |     |-- [ File Schema ] <- [ DuckDB (CSV/Excel Metadata) ]
      |
      |--[ LLM SQL Generation ]
      |     |
      |     |-- (Database Path)
      |     |    v
      |     | [ SelfCorrectingSQLAgent ] ---> [ SQL Executor ]
      |     |
      |     |-- (File Path)
      |          v
      |       [ DuckDB Execution ] <--- (MISSING SELF-CORRECTION)
      |
      v
[ Result Narrator ] ----> [ Conversational Insight ]
```

---

## 4. Action Plan (Critical Fixes)

### Priority 1: SQL Validation & Security
Update the read-only regex to support CTEs and ensure safety.
```python
# src/llm/sql_generator.py
READ_ONLY_PATTERN = re.compile(r"^\s*(SELECT|WITH)\s+", re.IGNORECASE)
```

### Priority 2: Lineage Accuracy
Enhance `SQLLineageParser` to detect and parse `WITH` clauses.
```python
# Logic Suggestion:
# 1. Detect tokens between 'WITH' and the final 'SELECT'.
# 2. Extract CTE names and their internal table references.
# 3. Filter CTE names out of the final 'tables_used' list.
# 4. Add the internal references to the lineage graph.
```

### Priority 3: Robustness (Self-Correction)
Refactor `MultiDatabaseHandler` to use the `SelfCorrectingSQLAgent` for DuckDB queries.
```python
# src/core/multi_db_handler.py
# Wrap DuckDB connection in a SQLAlchemy-compatible session (using duckdb-engine)
# and pass it to agent.execute_with_retry()
```

### Priority 4: DRY Refactoring
Move DuckDB query construction to `src/core/file_utils.py`.
```python
def get_duckdb_read_sql(file_path: str, file_type: str, sheet_name: Optional[str] = None) -> str:
    validated_path = validate_file_path(file_path, UPLOAD_DIR)
    safe_path = validated_path.replace("'", "''")
    if file_type in ('xlsx', 'xls'):
        # ... logic ...
    return f"SELECT * FROM read_csv_auto('{safe_path}', header=true)"
```
