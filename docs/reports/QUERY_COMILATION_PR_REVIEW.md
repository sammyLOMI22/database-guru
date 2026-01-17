# PR Review: Query Compilation & ER Diagram Improvements

## Summary
This PR introduces a robust `QueryCompiler` to normalize and cache SQL execution plans, significantly improving performance for recurring queries by bypassing the planning phase. It also includes substantial enhancements to the Frontend ER Diagram visualization, specifically around relationship cardinality and search usability.

## 🌟 What's Done Well

### Backend: Query Compiler
*   **Robust Normalization**: Moving from regex to `sqlparse` is a strong architectural decision. It correctly handles complex cases like escaped quotes (`'O''Reilly'`), scientific notation (`1e10`), and nested structures that regex often fails on.
*   **Thread-Safe Singleton**: The implementation correctly uses `threading.Lock` in `__new__` to ensure thread safety for the singleton instance, which is crucial for a shared cache in a multi-threaded environment (e.g., FastAPI).
*   **Efficient Caching**: Using `OrderedDict` for the LRU cache allows for O(1) operations. The logic for hit/miss/eviction tracking is clean and provides valuable observability via the new `/compiled-stats` endpoint.
*   **Safe Integration**: The integration into `SQLExecutor` is conservative and safe. It only attempts to compile `SELECT` queries that don't already have parameters, ensuring it doesn't interfere with complex queries or manual parameterization.

### Frontend: ER Diagram
*   **Intelligent Cardinality**: The `determineCardinality` function in `erDiagramUtils.ts` is a great improvement. Checking for unique constraints and primary keys on FK columns allows for distinguishing 1:1 relationships from 1:N, which is often missed in simple visualizers.
*   **Search Usability**: The highlighting logic in `applySearchFilter` correctly highlights both the matching nodes *and* their connected edges/neighbors, making it much easier to understand dependencies in large schemas.

## ⚠️ Issues & Observations

### 1. CTE Support (WITH clauses)
In `src/core/executor.py`, the compilation is triggered only if the SQL starts with `SELECT`:
```python
if params is None and sql.strip().upper().startswith("SELECT"):
```
**Issue**: This skips Common Table Expressions (CTEs) starting with `WITH`. Since `sqlparse` can handle CTEs, the compiler is capable of normalizing them, but the executor prevents it.
**Recommendation**: Use `sqlparse` to detect the statement type or simply relax the check to include `WITH` if the compiler supports it.

### 2. Singleton Initialization Pattern
The `QueryCompiler` uses `__new__` for initialization and `__init__` is empty (`pass`).
```python
def __init__(self, max_cache_size: int = 1000):
    pass
```
**Observation**: In Python, `__init__` is called every time `QueryCompiler()` is invoked, even if `__new__` returns an existing instance. Since `__init__` is empty, this works correctly (no re-initialization). However, relying on `__new__` for all initialization is a bit non-standard for simple classes, though acceptable for singletons. Just a note to maintainers to keep `__init__` empty.

### 3. Array Literals in Normalization
The `QueryCompiler` explicitly preserves array literals (e.g., `['a', 'b']`) to avoid binding issues with certain drivers.
**Observation**: This is a pragmatic choice, but it means queries with identical structure but different array values (e.g., `tags @> ['a']` vs `tags @> ['b']`) will not share a cache entry. This is a documented limitation but worth noting for future optimization (perhaps normalizing the array content itself if the driver allows).

## 💡 Future Improvements

1.  **Expand Compiler Scope**: Update the executor trigger to support `WITH`, `INSERT ... RETURNING`, and other query types that could benefit from plan caching.
2.  **Persistence**: As noted in the docs, moving the cache to Redis would allow it to survive application restarts and be shared across multiple worker processes.
3.  **Advanced Stats**: The current moving average for execution time is a simple cumulative average. Switching to an Exponential Moving Average (EMA) would better reflect recent database performance changes.
4.  **Frontend Visualization**: Expose the "Compiled" status in the query results UI (e.g., a small lightning bolt icon) so users know when their query hit the cache.

## Conclusion
**Status**: **Approved** ✅

The changes are high-quality, well-tested, and address previous robustness concerns. The added observability and ER diagram improvements are significant value-adds.