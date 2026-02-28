from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional

class DatabaseDialect(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    MSSQL = "mssql"
    ORACLE = "oracle"
    MONGODB = "mongodb"
    REDIS = "redis"
    CASSANDRA = "cassandra"
    DYNAMODB = "dynamodb"
    ELASTICSEARCH = "elasticsearch"

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
    DatabaseDialect.ORACLE: DialectRules(
        current_timestamp="SYSDATE",  # Oracle SYSDATE returns date+time; SYSTIMESTAMP for sub-second
        date_diff="SYSDATE - INTERVAL '{n}' {unit}",  # Interval literal arithmetic
        date_format="TO_CHAR({col}, '{format}')",  # TO_CHAR for date formatting
        concat="||",  # Operator-based concatenation (same as PostgreSQL)
        substring="SUBSTR({col}, {start}, {len})",  # SUBSTR (not SUBSTRING)
        string_length="LENGTH({col})",
        case_insensitive="LIKE",  # Case-sensitive by default; use UPPER(col) LIKE UPPER(val)
        limit_syntax="FETCH FIRST {n} ROWS ONLY",  # Oracle 12c+; older: ROWNUM <= n
        offset_syntax="OFFSET {n} ROWS",  # Oracle 12c+ pagination
        true_value="1",  # No native boolean — use NUMBER(1): 1/0
        false_value="0",  # No native boolean — use NUMBER(1): 1/0
        null_safe_equals="IS NOT DISTINCT FROM",  # Use DECODE(a, b, 1, 0) = 1 in older Oracle
        coalesce="COALESCE({args})",  # NVL(a, b) for two args; COALESCE for multiple
        cast_syntax="CAST({expr} AS {type})",
        json_extract="JSON_VALUE({col}, '$.{key}')",  # Oracle 12.2+
        json_array="JSON_ARRAY({args})",  # Oracle 21c+; use JSON_ARRAYAGG for older
        array_contains="",  # Not supported natively (use nested tables or VARRAYs)
        array_length="",   # Not supported natively
    ),
    DatabaseDialect.MSSQL: DialectRules(
        current_timestamp="GETDATE()",  # SQL Server timestamp function
        date_diff="DATEADD({unit}, -{n}, GETDATE())",  # DATEADD function
        date_format="FORMAT({col}, '{format}')",  # FORMAT function (SQL Server 2012+)
        concat="+ ",  # String concatenation with + operator (requires CAST for non-strings)
        substring="SUBSTRING({col}, {start}, {len})",
        string_length="LEN({col})",  # LEN excludes trailing spaces (DATALENGTH for bytes)
        case_insensitive="LIKE",  # Case sensitivity depends on collation (default CI)
        limit_syntax="TOP {n}",  # SELECT TOP n, not LIMIT (pre-SQL Server 2012)
        offset_syntax="OFFSET {n} ROWS FETCH NEXT {n} ROWS ONLY",  # SQL Server 2012+
        true_value="1",  # No native boolean — uses BIT (0/1)
        false_value="0",  # No native boolean — uses BIT (0/1)
        null_safe_equals="IS NOT DISTINCT FROM",  # Not natively supported; use ISNULL(a,'') = ISNULL(b,'')
        coalesce="COALESCE({args})",
        cast_syntax="CAST({expr} AS {type})",
        json_extract="JSON_VALUE({col}, '$.{key}')",  # JSON_VALUE returns scalar
        json_array="JSON_QUERY({col}, '$')",  # JSON_QUERY returns JSON fragment
        array_contains="",  # Not supported natively
        array_length="",  # Not supported natively
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
        DatabaseDialect.ORACLE: """
DATABASE: Oracle
- Use double quotes for case-sensitive identifiers; unquoted identifiers are UPPERCASED
- No boolean type — use NUMBER(1) with 1/0 or CHAR(1) with 'Y'/'N'
- Date math: SYSDATE - INTERVAL '7' DAY or ADD_MONTHS(SYSDATE, -1)
- String concat: || operator
- Pagination: FETCH FIRST n ROWS ONLY (12c+) or WHERE ROWNUM <= n (older)
- No LIMIT — use FETCH FIRST or ROWNUM
- Use VARCHAR2 (not VARCHAR), NUMBER (not numeric), CLOB (not text)
- FROM DUAL for expressions without a table: SELECT SYSDATE FROM DUAL
- JSON: JSON_VALUE(col, '$.key') for scalars (12.2+)
""",
        DatabaseDialect.MSSQL: """
DATABASE: SQL Server (T-SQL)
- Use square brackets for identifiers: [column_name]
- Boolean: BIT type with values 1/0 (no TRUE/FALSE)
- Date math: DATEADD(day, -7, GETDATE())
- String concat: + operator (cast non-strings first)
- Pagination: SELECT TOP n or OFFSET n ROWS FETCH NEXT n ROWS ONLY
- JSON: JSON_VALUE(col, '$.key') for scalars, JSON_QUERY for objects
- Use ISNULL() instead of COALESCE when checking single values
""",
        DatabaseDialect.MONGODB: """
DATABASE: MongoDB (MQL - MongoDB Query Language)
- Queries use MQL, NOT SQL
- Collections are equivalent to SQL tables
- Documents are equivalent to SQL rows
- Fields are equivalent to SQL columns
- Use aggregation pipelines for GROUP BY, JOIN ($lookup), and complex transformations
- Pipeline stages: $match, $group, $sort, $limit, $project, $lookup, $unwind, $count
- Filter operators: $eq, $gt, $gte, $lt, $lte, $ne, $in, $nin, $regex, $exists
- Logical operators: $and, $or, $not, $nor
- Array operators: $elemMatch, $all, $size
- Aggregation accumulators: $sum, $avg, $min, $max, $first, $last, $push, $addToSet
- Date handling: use ISODate strings for comparisons
- Return ONLY valid JSON with keys: operation, collection, query, pipeline, sort, limit
""",
        DatabaseDialect.REDIS: """
DATABASE: Redis (Key-Value Store)
- Queries use Redis commands, NOT SQL
- Data is organized by keys with typed values (string, hash, list, set, sorted set)
- Key patterns group related data (e.g., user:*, session:*, order:*)
- Common read commands: GET, HGETALL, LRANGE, SMEMBERS, ZRANGE
- Common write commands: SET, HSET, LPUSH, SADD, ZADD
- Pattern scanning: SCAN with MATCH pattern
- Return ONLY valid JSON with keys: command, args, data_type, is_write
""",
        DatabaseDialect.CASSANDRA: """
DATABASE: Apache Cassandra (CQL - Cassandra Query Language)
- CQL is SQL-like but with NoSQL constraints
- Must query by partition key (or use ALLOW FILTERING)
- No JOIN, no subquery, limited GROUP BY
- Time-series optimized: use clustering columns for range queries
- Common: SELECT, INSERT, UPDATE, DELETE
- Aggregations: COUNT, SUM, AVG, MIN, MAX (limited)
""",
        DatabaseDialect.DYNAMODB: """
DATABASE: Amazon DynamoDB (PartiQL / Native API)
- PartiQL provides SQL-like syntax for DynamoDB
- Must specify partition key in WHERE clause
- Sort key enables range queries within a partition
- No JOIN, limited filtering on non-key attributes
- Global Secondary Indexes (GSI) allow alternative query patterns
""",
        DatabaseDialect.ELASTICSEARCH: """
DATABASE: Elasticsearch (Query DSL)
- Queries use JSON Query DSL, NOT SQL
- Indices are equivalent to SQL tables
- Documents are equivalent to SQL rows
- Fields are equivalent to SQL columns
- Use "query" for filtering, "aggs" for aggregations, "sort" for ordering
- Query types: match, term, range, bool (must/should/must_not)
- Aggregation types: terms, date_histogram, avg, sum, min, max, cardinality
- Return ONLY valid JSON with keys: index, query, aggs, sort, size
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
    elif "mssql" in normalized or "sqlserver" in normalized or "sql server" in normalized or "microsoft" in normalized:
        return DatabaseDialect.MSSQL
    elif "oracle" in normalized or "ora" == normalized:
        return DatabaseDialect.ORACLE
    elif "mongo" in normalized:
        return DatabaseDialect.MONGODB
    elif "redis" in normalized:
        return DatabaseDialect.REDIS
    elif "cassandra" in normalized:
        return DatabaseDialect.CASSANDRA
    elif "dynamo" in normalized:
        return DatabaseDialect.DYNAMODB
    elif "elastic" in normalized or "opensearch" in normalized:
        return DatabaseDialect.ELASTICSEARCH
    else:
        # Default to SQLite if unknown, as it's the safest lowest common denominator
        return DatabaseDialect.SQLITE
