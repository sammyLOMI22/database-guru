# PR Review: Database Dialect Support

## Summary
**Status**: ✅ **APPROVED with Suggestions**

This branch introduces a robust `DialectRegistry` and related infrastructure to support multiple SQL dialects (PostgreSQL, MySQL, SQLite, DuckDB). This is a crucial foundational change for ensuring correct SQL generation across different database backends.

## 1. Code Review

### `src/llm/dialect_registry.py`
- **Architecture**: The use of `Enum` for `DatabaseDialect` and `dataclass` for `DialectRules` is excellent. It provides a structured and type-safe way to define dialect-specific syntax.
- **Completeness**: Major dialects (PostgreSQL, MySQL, SQLite, DuckDB) are well-covered. `MongoDB` is included as a placeholder for future MQL support.
- **Rules Coverage**: The `DialectRules` dataclass covers key areas where SQL syntax diverges:
    - Date/Time functions (`current_timestamp`, `date_diff`, etc.)
    - String manipulation (`concat`, `substring`)
    - JSON handling (`json_extract`, `json_array`)
    - Case sensitivity and boolean values.
- **Correctness**:
    - SQLite: Correctly uses `datetime('now')` and notes ASCII-only case insensitivity for `LIKE`.
    - DuckDB: Correctly leverages its Postgres compatibility (`::` cast, `ILIKE`).
    - MySQL: Correctly uses `CONCAT()` and `DATE_SUB()`.

### `src/llm/query_templates.py`
- **Integration**: The `TemplateEngine` now correctly imports and uses `DatabaseDialect` and `DialectRules` to format SQL queries.
- **Dialect Awareness**:
    - `_format_date_filter`: Correctly branches for SQLite, MySQL, and Postgres/DuckDB.
    - `_format_boolean`: Correctly handles `TRUE`/`FALSE` vs `1`/`0`.
    - `_format_case_insensitive_match`: Correctly distinguishes between `ILIKE` and `LOWER() LIKE`.

### `src/llm/sql_generator.py` & `src/llm/prompts.py`
- **Observation**: `src/llm/sql_generator.py` currently uses `get_dialect_rules` from `src/llm/prompts.py` (lines 128-130), which accesses a dictionary `DIALECT_RULES` defined in `prompts.py` (lines 92-125).
- **Inconsistency**: There is now a `DIALECT_RULES` in `prompts.py` (strings for LLM) and a `DIALECT_RULES` in `dialect_registry.py` (objects for code).
- **Missed Integration**: `src/llm/dialect_registry.py` includes a `build_dialect_context` function that generates similar LLM instructions, but it is not currently used by the `SQLGenerator`.
    - `prompts.py` rules emphasize date truncation and pagination.
    - `dialect_registry.py` rules emphasize arrays and JSON.

## 2. Testing
- **Unit Tests**: `tests/test_dialect_registry.py` verifies:
    - All dialects have defined rules.
    - Specific syntax checks for each dialect (e.g., SQLite uses `datetime`, Postgres uses `INTERVAL`).
    - Context building strings contain expected dialect names and keywords.
    - Database type string mapping works as expected (including fallbacks).
- **Execution**: All tests in `tests/test_dialect_registry.py` passed successfully.

## 3. Suggestions & Notes
1.  **Consolidate Dialect Sources**:
    - Consider migrating `src/llm/prompts.py` to use `src/llm/dialect_registry.py` for its prompt generation.
    - Merge the context strings from `prompts.py` (which have good details on date truncation/pagination) into `dialect_registry.py`'s `build_dialect_context`.
    - Eventually deprecate the `DIALECT_RULES` dictionary in `prompts.py` to have a Single Source of Truth.
2.  **SQLite JSON**: The registry uses `JSON_EXTRACT` for SQLite. Ensure that the SQLite version in the environment supports the JSON1 extension (it usually does in modern Python/SQLite versions).
3.  **DuckDB Casting**: The registry uses `CAST(x AS type)` for DuckDB, which is standard and safe, though DuckDB also supports `::`.

## 4. Conclusion
The implementation is clean, well-tested, and correctly integrated into the query template engine. It significantly improves the system's ability to generate valid SQL for different backends. The identified duplication in `prompts.py` is a technical debt item that should be addressed in a follow-up refactor but does not block this feature.

**Recommendation**: **MERGE** ✅
