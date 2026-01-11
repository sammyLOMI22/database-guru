# PR Review: Database Dialect Support

**Branch:** `database-dial-support`
**Status:** Approve with Minor Changes

## Summary
This PR implements dialect-aware SQL generation for the `TemplateEngine`, supporting PostgreSQL, MySQL, SQLite, and DuckDB. It introduces a `DialectRules` registry and integrates it into the template matching flow to handle database-specific syntax for booleans, dates, and string matching.

## ✅ Strengths
- **Clean Architecture:** The `DialectRules` dataclass provides a structured way to handle syntax variations.
- **Improved Accuracy:** Bypasses LLM with more reliable, dialect-correct SQL for common patterns.
- **Strong Testing:** Comprehensive test suite covering all supported dialects.

## ⚠️ Issues to Address

### 1. Missing Newlines at EOF
The following files are missing a trailing newline:
- `src/llm/dialect_registry.py`
- `tests/test_dialect_registry.py`

### 2. Unused Helper Methods
`_format_case_insensitive_match` and `_format_date_filter` in `src/llm/query_templates.py` are well-implemented and tested but are currently not used by any template patterns. 
- **Suggestion:** Integrate these into the `TemplateEngine.try_match` patterns or mark them for future use.

### 3. Weak Test Assertion
In `tests/test_query_templates.py` (around line 746-747):
```python
if match:
    assert "O''Malley" in match.sql or "O\\'Malley" in match.sql or "O'Malley" not in match.sql
```
This assertion is too permissive. It can pass even if the match is `None`. 
- **Suggestion:** Tighten to `assert match is not None` before checking the SQL content.

### 4. Boolean Detection Scope
The `_is_boolean_value` method treats "enabled"/"disabled" and "yes"/"no" as booleans. While helpful, this might cause false positives if these are used as literal strings in non-boolean columns.

## 💡 Recommendations
- **Observability:** Add the detected `dialect` to the `TemplateMatch` metadata for easier debugging.
- **MariaDB Support:** Add explicit mapping for MariaDB, even if it currently defaults to MySQL rules.
