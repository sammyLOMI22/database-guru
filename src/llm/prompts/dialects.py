"""Dialect-specific SQL rules for different database engines."""

DIALECT_RULES = {
    "sqlite": """SQLITE-SPECIFIC RULES:
- Use strftime() for date formatting: strftime('%Y-%m-%d', date_column)
- Use date('now') for current date, datetime('now') for current timestamp
- Use || for string concatenation (NOT CONCAT)
- Use LIKE for case-insensitive matching (SQLite LIKE is case-insensitive for ASCII)
- Use IFNULL() instead of COALESCE() for simple null handling
- Boolean values are 0 and 1, not TRUE/FALSE
- Use substr() instead of SUBSTRING()""",

    "postgresql": """POSTGRESQL-SPECIFIC RULES:
- Use ILIKE for case-insensitive matching (NOT LIKE)
- Use NOW() or CURRENT_TIMESTAMP for current time
- Use DATE_TRUNC() for date truncation: DATE_TRUNC('month', date_column)
- Use to_char() for date formatting
- Use :: for type casting: column::text, column::integer
- Use COALESCE() for null handling
- Boolean values are TRUE/FALSE
- Use LIMIT with OFFSET for pagination""",

    "mysql": """MYSQL-SPECIFIC RULES:
- Use DATE_FORMAT() for date formatting: DATE_FORMAT(date_column, '%Y-%m-%d')
- Use NOW() for current timestamp, CURDATE() for current date
- Use CONCAT() for string concatenation
- Use IFNULL() or COALESCE() for null handling
- Use LOWER(column) = LOWER('value') for case-insensitive matching
- Use backticks for identifier quoting: `table_name`
- Use LIMIT with OFFSET for pagination""",

    "duckdb": """DUCKDB-SPECIFIC RULES:
- Similar to PostgreSQL syntax
- Use strftime() for date formatting
- Use CURRENT_DATE, CURRENT_TIMESTAMP for current time
- Use || for string concatenation
- Use ILIKE for case-insensitive matching
- Supports list and struct types natively
- Use TRY_CAST() for safe type casting""",
}


def get_dialect_rules(database_type: str) -> str:
    """Get dialect-specific rules for a database type."""
    return DIALECT_RULES.get(database_type.lower(), "")
