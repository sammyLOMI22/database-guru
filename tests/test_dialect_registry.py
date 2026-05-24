"""
Tests for Dialect Registry (Phase 3.1)
"""
import pytest
from src.llm.dialect_registry import (
    DatabaseDialect,
    DialectRules,
    DIALECT_RULES,
    build_dialect_context,
    get_dialect_for_database_type
)

class TestDialectRegistry:
    """Test dialect registry functionality."""

    def test_all_dialects_have_rules(self):
        """Ensure all SQL dialects have rules defined."""
        nosql_dialects = {
            DatabaseDialect.MONGODB,
            DatabaseDialect.REDIS,
            DatabaseDialect.CASSANDRA,
            DatabaseDialect.DYNAMODB,
            DatabaseDialect.ELASTICSEARCH,
            DatabaseDialect.NEO4J,
        }
        for dialect in DatabaseDialect:
            if dialect in nosql_dialects:
                continue  # NoSQL dialects don't have SQL rules
            assert dialect in DIALECT_RULES
            assert isinstance(DIALECT_RULES[dialect], DialectRules)

    def test_postgres_rules(self):
        """Verify PostgreSQL specific rules."""
        rules = DIALECT_RULES[DatabaseDialect.POSTGRESQL]
        assert rules.true_value == "TRUE"
        assert "CURRENT_TIMESTAMP - INTERVAL" in rules.date_diff
        assert "ILIKE" in rules.case_insensitive
        assert "||" in rules.concat

    def test_sqlite_rules(self):
        """Verify SQLite specific rules."""
        rules = DIALECT_RULES[DatabaseDialect.SQLITE]
        assert rules.true_value == "1"
        assert "datetime" in rules.date_diff
        assert "LIKE" in rules.case_insensitive  # ASCII only
        assert "||" in rules.concat

    def test_mysql_rules(self):
        """Verify MySQL specific rules."""
        rules = DIALECT_RULES[DatabaseDialect.MYSQL]
        assert rules.true_value == "TRUE"
        assert "DATE_SUB" in rules.date_diff
        assert "CONCAT" in rules.concat

    def test_duckdb_rules(self):
        """Verify DuckDB specific rules."""
        rules = DIALECT_RULES[DatabaseDialect.DUCKDB]
        assert rules.true_value == "TRUE"
        assert "list_contains" in rules.array_contains
        assert "||" in rules.concat

    def test_context_building(self):
        """Test dialect context generation."""
        ctx = build_dialect_context(DatabaseDialect.POSTGRESQL)
        assert "PostgreSQL" in ctx
        assert "ILIKE" in ctx
        assert "INTERVAL" in ctx

        ctx_sqlite = build_dialect_context(DatabaseDialect.SQLITE)
        assert "SQLite" in ctx_sqlite
        assert "datetime" in ctx_sqlite

    def test_db_type_mapping(self):
        """Test mapping string types to enum."""
        assert get_dialect_for_database_type("postgresql") == DatabaseDialect.POSTGRESQL
        assert get_dialect_for_database_type("postgres") == DatabaseDialect.POSTGRESQL
        assert get_dialect_for_database_type("mysql") == DatabaseDialect.MYSQL
        assert get_dialect_for_database_type("sqlite") == DatabaseDialect.SQLITE
        assert get_dialect_for_database_type("duckdb") == DatabaseDialect.DUCKDB
        assert get_dialect_for_database_type("unknown") == DatabaseDialect.SQLITE  # Default
