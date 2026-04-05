# PR Review: Data Lineage & Impact Analysis

**Reviewer:** Jules (Senior Software Engineer & Product Manager)
**Branch:** `data-lineage` (compared to `main`)
**Status:** ⚠️ Partial Implementation / Needs Improvement

## 1. Overview
This PR introduces the core infrastructure for Data Lineage and Impact Analysis. It includes a SQL parser to extract lineage graphs, an impact analyzer to assess schema change risks, and a React Flow-based frontend visualization.

While the visualization and basic parsing logic are functional, the implementation falls short of the original Phase 11 plan, specifically regarding advanced analytics (heatmaps), deep lineage (CTEs), and robust impact detection.

## 2. What Works Well
*   **Frontend Visualization:** The `LineageGraph` component using React Flow is polished. It handles auto-layout (`dagre`), dark mode, and interactive node highlighting effectively. The UI integration in `LineagePanel` is clean and intuitive.
*   **Architecture:** The separation of concerns is good. `SQLLineageParser` is decoupled from the API, and the `ImpactAnalyzer` logic is isolated.
*   **Test Coverage:** Basic test coverage is strong (64 passing tests). The unit tests cover standard SQL patterns (JOINs, aggregations) well.
*   **Code Quality:** The code is well-typed (Python and TypeScript), documented, and follows the project's style guidelines.

## 3. Issues & Concerns
### 🚨 Critical: Impact Analysis Fragility
The `ImpactAnalyzer` relies on `ilike` queries (`QueryHistory.generated_sql.ilike(f"%{table_name}%")`) and string searching.
*   **Risk:** This leads to high false positives. Searching for `orders` will match `customer_orders`, `orders_backup`, or even comments containing the word "orders".
*   **Fix:** Use the `sqlparse` tokenizer to verify that the match is indeed a table identifier, or rely on a more structured parsed representation if available.

### ⚠️ Major: Shallow CTE Support
The `SQLLineageParser` treats Common Table Expressions (CTEs) as "source tables" rather than recurring into them.
*   **Impact:** If a user queries a CTE `WITH recent_orders AS (SELECT * FROM orders) ...`, the lineage shows `recent_orders` as the source, completely missing the link to the actual `orders` table. This breaks the primary value proposition of lineage (tracing back to origin).
*   **Fix:** The parser needs to register CTEs as temporary scopes and resolve their underlying tables.

### ⚠️ Major: Missing Caching
The plan specified a `QueryLineageCache` (Hybrid LRU) to cache parsed results.
*   **Current State:** Not implemented. Every request re-parses the SQL.
*   **Impact:** Performance degradation on large query histories or complex queries.

## 4. Missing Features (vs Plan)
The following components defined in `DATA_LINGEAGE_PLAN.md` are **missing**:
1.  **Query Pattern Analytics:** `src/core/query_pattern_analyzer.py` is missing. No heatmaps or usage stats.
2.  **Frontend Components:**
    *   `QueryPatternHeatmap.tsx` (Usage visualization)
    *   `ColumnLineage.tsx` (Detailed column tracing table)
    *   `QueryPathOverlay.tsx` (ER Diagram integration)
    *   `TableStatsNode.tsx` (Row counts on ERD)
3.  **Table Statistics API:** `src/api/endpoints/table_stats.py` is missing.

## 5. Future Directions & Recommendations
1.  **Refactor Parser:** Move away from regex-based column extraction in `SQLLineageParser` to a full AST traversal (possibly upgrading `sqlparse` usage or adopting `sqlglot` for better dialect support).
2.  **Implement Caching:** Add the `QueryLineageCache` model immediately to prevent CPU spikes.
3.  **Complete the Scope:** The "Analytics" portion (Heatmaps, Patterns) provides high value for the "Product Manager" persona (identifying bottlenecks). This should be prioritized for the next sprint.
4.  **Security/Privacy:** Ensure `generated_sql` in history doesn't contain PII literals before parsing/displaying in the History tab.

## 6. Conclusion
This PR establishes a **solid foundation** for visualization but is **not yet production-ready** for complex use cases due to the CTE limitation and brittle impact analysis.

**Recommendation:**
1.  **Merge** the current work as "Phase 1: Visualization Core" *after* addressing the `ilike` fragility (at least add token boundaries).
2.  **Create tickets** for "Phase 2: Deep Lineage (CTEs)" and "Phase 3: Analytics & Heatmaps".
