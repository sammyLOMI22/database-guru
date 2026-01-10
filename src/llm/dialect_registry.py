from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional

class DatabaseDialect(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    MONGODB = "mongodb"  # For future MQL generation

@dataclass
class DialectRules:
    """Database-specific SQL rules and syntax."""

    # Date/Time functions
    current_timestamp: str  # NOW(), CURRENT_TIMESTAMP, datetime('now')
    date_diff: str  # Syntax to subtract time from now (returns TIMESTAMP/DATETIME)
    date_format: str  # TO_CHAR, DATE_FORMAT, strftime

    # String functions
    concat: str  # ||, CONCAT(), +
    substring: str  # SUBSTRING, SUBSTR
    string_length: str  # LENGTH, LEN, CHAR_LENGTH
    case_insensitive: str  # ILIKE, LOWER() LIKE, COLLATE

    # Pagination
    limit_syntax: str  # LIMIT n, LIMIT n OFFSET m, TOP n
    offset_syntax: str  # OFFSET, SKIP

    # Boolean handling
    true_value: str  # TRUE, 1, 'true'
    false_value: str  # FALSE, 0, 'false'

    # NULL handling
    null_safe_equals: str  # IS NOT DISTINCT FROM, <=>
    coalesce: str  # COALESCE, IFNULL, NVL

    # Type casting
    cast_syntax: str  # CAST(x AS type), x::type, CONVERT()

    # JSON support
    json_extract: str  # ->, ->>, JSON_EXTRACT
    json_array: str  # JSON_BUILD_ARRAY, JSON_ARRAY

    # Array support (PostgreSQL, DuckDB)
    array_contains: str  # @>, ARRAY_CONTAINS
    array_length: str  # ARRAY_LENGTH, CARDINALITY

# Dialect configurations
# Each dialect has specific syntax for common SQL operations.
# Comments indicate non-obvious behaviors or key differences from standard SQL.
DIALECT_RULES: Dict[DatabaseDialect, DialectRules] = {
    DatabaseDialect.POSTGRESQL: DialectRules(
        current_timestamp="CURRENT_TIMESTAMP",
        date_diff="CURRENT_TIMESTAMP - INTERVAL '{n} {unit}'",  # Returns TIMESTAMP
        date_format="TO_CHAR({col}, '{format}')",
        concat="||",  # Operator-based concatenation
        substring="SUBSTRING({col} FROM {start} FOR {len})",  # Uses FROM/FOR syntax
        string_length="LENGTH({col})",
        case_insensitive="ILIKE",  # Native case-insensitive LIKE
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        true_value="TRUE",  # Native boolean type
        false_value="FALSE",  # Native boolean type
        null_safe_equals="IS NOT DISTINCT FROM",  # SQL standard null-safe comparison
        coalesce="COALESCE({args})",
        cast_syntax="{expr}::{type}",  # PostgreSQL-style cast shorthand
        json_extract="{col}->'{key}'",  # Returns JSON, ->> for text
        json_array="JSON_BUILD_ARRAY({args})",
        array_contains="{col} @> ARRAY[{val}]",  # Array containment operator
        array_length="ARRAY_LENGTH({col}, 1)",  # Second arg is dimension
    ),
    DatabaseDialect.SQLITE: DialectRules(
        current_timestamp="datetime('now')",  # SQLite uses datetime() function
        date_diff="datetime('now', '-{n} {unit}')",  # Modifier-based date math
        date_format="strftime('{format}', {col})",  # Format string first
        concat="||",  # Operator-based concatenation
        substring="SUBSTR({col}, {start}, {len})",  # SUBSTR not SUBSTRING
        string_length="LENGTH({col})",
        case_insensitive="LIKE",  # Case-insensitive for ASCII only
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        true_value="1",  # No native boolean, uses integers
        false_value="0",  # No native boolean, uses integers
        null_safe_equals="IS",  # Limited null-safe support
        coalesce="COALESCE({args})",
        cast_syntax="CAST({expr} AS {type})",
        json_extract="JSON_EXTRACT({col}, '$.{key}')",  # JSON path syntax
        json_array="JSON_ARRAY({args})",
        array_contains="",  # Not supported
        array_length="",  # Not supported
    ),
    DatabaseDialect.MYSQL: DialectRules(
        current_timestamp="NOW()",  # Function-based timestamp
        date_diff="DATE_SUB(NOW(), INTERVAL {n} {unit})",  # DATE_SUB function
        date_format="DATE_FORMAT({col}, '{format}')",
        concat="CONCAT({args})",  # Function-based concatenation
        substring="SUBSTRING({col}, {start}, {len})",
        string_length="LENGTH({col})",
        case_insensitive="LIKE",  # Case-insensitive with default collation
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        true_value="TRUE",  # Also accepts 1
        false_value="FALSE",  # Also accepts 0
        null_safe_equals="<=>",  # MySQL null-safe equals operator
        coalesce="COALESCE({args})",
        cast_syntax="CAST({expr} AS {type})",
        json_extract="{col}->'$.{key}'",  # JSON path with -> operator
        json_array="JSON_ARRAY({args})",
        array_contains="",  # Not supported natively
        array_length="JSON_LENGTH({col})",  # Works with JSON arrays
    ),
    DatabaseDialect.DUCKDB: DialectRules(
        current_timestamp="CURRENT_TIMESTAMP",
        date_diff="CURRENT_TIMESTAMP - INTERVAL '{n} {unit}'",  # Returns TIMESTAMP
        date_format="strftime({col}, '{format}')",  # Column first, format second
        concat="||",  # Operator-based concatenation
        substring="substring({col}, {start}, {len})",  # Lowercase function name
        string_length="length({col})",  # Lowercase function name
        case_insensitive="ILIKE",  # Native case-insensitive LIKE
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        true_value="TRUE",  # Native boolean type
        false_value="FALSE",  # Native boolean type
        null_safe_equals="IS NOT DISTINCT FROM",  # SQL standard null-safe comparison
        coalesce="COALESCE({args})",
        cast_syntax="CAST({expr} AS {type})",
        json_extract="{col}.{key}",  # Struct/dot notation for JSON
        json_array="list_value({args})",  # DuckDB uses lists, not JSON arrays
        array_contains="list_contains({col}, {val})",  # List containment function
        array_length="len({col})",  # Simple len() function
    ),
}

def build_dialect_context(dialect: DatabaseDialect) -> str:
    """
    Build dialect-specific prompt context.
    NOTE: Ensure descriptions here match the syntax rules defined in DIALECT_RULES above.
    """

    contexts = {
        DatabaseDialect.POSTGRESQL: """
DATABASE: PostgreSQL
- Use double quotes for identifiers: "column_name"
- Boolean: TRUE/FALSE (not 1/0)
- Date math: INTERVAL '7 days'
- String concat: || operator
- Case-insensitive: ILIKE
- Arrays: ARRAY[1,2,3], @> for contains
- JSON: column->'key', column->>'key' for text
""",
        DatabaseDialect.SQLITE: """
DATABASE: SQLite
- Identifiers: no quotes needed or use double quotes
- Boolean: 1/0 (not TRUE/FALSE)
- Date math: datetime('now', '-7 days')
- String concat: || operator
- Case-insensitive: LIKE (for ASCII)
- No arrays or advanced JSON in older versions
- Use COALESCE for NULL handling
""",
        DatabaseDialect.MYSQL: """
DATABASE: MySQL
- Use backticks for identifiers: `column_name`
- Boolean: TRUE/FALSE or 1/0
- Date math: DATE_SUB(NOW(), INTERVAL 7 DAY)
- String concat: CONCAT(a, b) function
- Case-insensitive: LIKE (default collation)
- JSON: column->'$.key', JSON_EXTRACT
""",
        DatabaseDialect.DUCKDB: """
DATABASE: DuckDB
- PostgreSQL-compatible syntax
- Boolean: TRUE/FALSE
- Date math: INTERVAL '7 days'
- String concat: || operator
- Arrays: [1, 2, 3], list_contains()
- Excellent JSON support: column.key notation
- Supports QUALIFY for window functions
""",
        DatabaseDialect.MONGODB: """
DATABASE: MongoDB
- No SQL
- Use MQL (MongoDB Query Language)
""",
    }
    return contexts.get(dialect, "")

def get_dialect_for_database_type(db_type: str) -> DatabaseDialect:
    """Map string database type to DatabaseDialect enum."""
    normalized = db_type.lower().strip()
    if "postgres" in normalized:
        return DatabaseDialect.POSTGRESQL
    elif "mysql" in normalized:
        return DatabaseDialect.MYSQL
    elif "sqlite" in normalized:
        return DatabaseDialect.SQLITE
    elif "duckdb" in normalized:
        return DatabaseDialect.DUCKDB
    elif "mongo" in normalized:
        return DatabaseDialect.MONGODB
    else:
        # Default to SQLite if unknown, as it's the safest lowest common denominator
        return DatabaseDialect.SQLITE
