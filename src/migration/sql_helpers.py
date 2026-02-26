"""Shared SQL identifier quoting and literal escaping helpers for migration generators."""

from src.llm.dialect_registry import DatabaseDialect


def quote_identifier(identifier: str, dialect: DatabaseDialect) -> str:
    """Quote a SQL identifier based on dialect, escaping embedded delimiters."""
    if dialect == DatabaseDialect.MYSQL:
        return f"`{identifier.replace('`', '``')}`"
    if dialect == DatabaseDialect.MSSQL:
        return f"[{identifier.replace(']', ']]')}]"
    # PostgreSQL, SQLite, DuckDB, Oracle all use ANSI double quotes
    return f'"{identifier.replace(chr(34), chr(34)*2)}"'


def escape_literal(value: str) -> str:
    """Escape a string for use in a SQL string literal (single quotes)."""
    return value.replace("'", "''")
