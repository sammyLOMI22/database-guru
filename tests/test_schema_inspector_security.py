"""Tests for schema_inspector SQL injection prevention."""

import pytest
from src.core.schema_inspector import _safe_identifier


class TestSafeIdentifier:
    """Verify _safe_identifier rejects injection patterns."""

    def test_valid_simple(self):
        assert _safe_identifier("users") == "users"

    def test_valid_underscore(self):
        assert _safe_identifier("_private_table") == "_private_table"

    def test_valid_with_numbers(self):
        assert _safe_identifier("table123") == "table123"

    def test_valid_with_dollar(self):
        assert _safe_identifier("pg$temp") == "pg$temp"

    def test_valid_uppercase(self):
        assert _safe_identifier("MyTable") == "MyTable"

    def test_rejects_semicolon_injection(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("users; DROP TABLE users--")

    def test_rejects_single_quote(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("users' OR '1'='1")

    def test_rejects_double_quote(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier('table"name')

    def test_rejects_space(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("table name")

    def test_rejects_dash(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("table-name")

    def test_rejects_dot(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("schema.table")

    def test_rejects_parentheses(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("func()")

    def test_rejects_backslash(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("table\\name")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("")

    def test_rejects_starts_with_number(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("123table")

    def test_rejects_comment_injection(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("users--comment")

    def test_rejects_union_injection(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("users UNION SELECT")

    def test_rejects_newline(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("table\nname")

    def test_rejects_tab(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("table\tname")

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError, match="Unsafe SQL identifier"):
            _safe_identifier("table\x00name")
