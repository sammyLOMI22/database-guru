# PR Review: Data Lineage & Impact Analysis

**Review Status:** PASS (with recommendations)
**Branch:** `data-lineage`
**Reviewer:** Antigravity

## Overview

The `data-lineage` branch introduces robust data lineage and impact analysis features. This implementation allows users to visualize how data flows from source tables through transformations to output columns, and provides a critical safety check for schema modifications via impact analysis.

## Key Findings

### 1. Robust Visualization (React Flow)
The `LineageGraph` implementation using React Flow is impressive. It correctly visualizes:
- **Source Tables** as input nodes.
- **Source Columns** as intermediate containment nodes.
- **Transformation Nodes** for aggregations (SUM, COUNT, etc.) and expressions (CASE, arithmetic).
- **Output Columns** as the final result nodes.
The use of `dagre` for auto-layout provides clear, directed data flow from left to right.

### 2. Backend Parser (Fragility)
The `SQLLineageParser` is primarily regex-based for certain granular extractions (like expressions and function arguments). While it handles common cases well, it may be fragile for:
- Highly nested subqueries.
- Custom database-specific functions.
- Complex string escaping within CASE statements.
> [!TIP]
> Consider augmenting the regex logic with a more robust AST-based approach using `sql-parser-cst` or advanced `sqlparse` visitor patterns in the future.

### 3. Impact Analysis Limitations
The `ImpactAnalyzer` uses string-based `ilike` searches in the database followed by string position detection in Python.
- **Risk:** Simple string matching might flag "customers" when "customer_orders" is the actual table.
- **Recommendation:** Use a proper SQL tokenizer/parser for impact detection to ensure exact object matching.

### 4. Database Caching Missing
The implementation plan mentioned a `QueryLineageCache` model for hybrid LRU caching (caching after the second access). This model is **not yet implemented** in `src/database/models.py`, which may impact performance for frequent lineage requests on large query histories.

### 5. Frontend State Management
Switching between sub-tabs (Explore, History, Impact) within the Lineage panel resets the state of the active visualization. This is because components are unmounted. 
> [!NOTE]
> I have implemented a fix for this by using conditional rendering (`display: hidden`) instead of unmounting the components.

## Code Quality & Documentation
- **Tests**: Excellent coverage. 44 backend lineage tests and 20 impact analyzer tests are passing.
- **Styling**: Glassmorphism and theme consistency are well-maintained. Light/Dark mode transitions are smooth.
- **API**: Endpoints are clean and follow established patterns.

## Recommended Next Steps
1. **Implement `QueryLineageCache`**: Add the database model and integration logic to speed up repeated lineage requests.
2. **Refine Subquery Support**: Enhance `_is_subquery` to handle nested CTEs or complex JOIN subqueries.
3. **AST-based Impact Analysis**: Replace `LIKE` queries with a more precise SQL indexing or parsing strategy.

---
**Conclusion:** The feature is extremely valuable and visually polished. It is safe to merge after addressing the frontend state reset issue.
