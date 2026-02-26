"""Tests for shared SQL identifier quoting and escaping helpers."""

import pytest
from src.migration.sql_helpers import quote_identifier, escape_literal
from src.llm.dialect_registry import DatabaseDialect


class TestQuoteIdentifier:
    def test_postgresql_double_quotes(self):
        assert quote_identifier("users", DatabaseDialect.POSTGRESQL) == '"users"'

    def test_postgresql_escapes_embedded_quote(self):
        assert quote_identifier('foo"bar', DatabaseDialect.POSTGRESQL) == '"foo""bar"'

    def test_mysql_backticks(self):
        assert quote_identifier("users", DatabaseDialect.MYSQL) == "`users`"

    def test_mysql_escapes_embedded_backtick(self):
        assert quote_identifier("foo`bar", DatabaseDialect.MYSQL) == "`foo``bar`"

    def test_mssql_brackets(self):
        assert quote_identifier("users", DatabaseDialect.MSSQL) == "[users]"

    def test_mssql_escapes_embedded_bracket(self):
        assert quote_identifier("foo]bar", DatabaseDialect.MSSQL) == "[foo]]bar]"

    def test_sqlite_double_quotes(self):
        assert quote_identifier("t", DatabaseDialect.SQLITE) == '"t"'

    def test_oracle_double_quotes(self):
        assert quote_identifier("t", DatabaseDialect.ORACLE) == '"t"'

    def test_oracle_escapes_embedded_quote(self):
        assert quote_identifier('col"x', DatabaseDialect.ORACLE) == '"col""x"'


class TestEscapeLiteral:
    def test_no_quotes(self):
        assert escape_literal("hello") == "hello"

    def test_single_quote_escaped(self):
        assert escape_literal("O'Brien") == "O''Brien"

    def test_multiple_quotes(self):
        assert escape_literal("it's a 'test'") == "it''s a ''test''"

    def test_empty_string(self):
        assert escape_literal("") == ""
