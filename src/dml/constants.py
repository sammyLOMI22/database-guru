"""Shared constants for the DML module (Phase 18)."""
import re

# Safe SQL identifiers: letters, digits, underscores.
# Supports optional schema qualification (e.g. "public.users", "dbo.orders").
# Used by both the generator and validator to prevent injection.
SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?$")

# NoSQL identifiers allow dots, dashes, and colons
# (e.g. MongoDB collections, ES indices, Redis colon-delimited keys like "user:1").
NOSQL_SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-:]*$")

# Supported SQL dialects for DML generation
SUPPORTED_DIALECTS = frozenset({"postgresql", "sqlite", "duckdb", "oracle", "mysql", "mssql"})

# NoSQL database types
NOSQL_TYPES = frozenset({"mongodb", "redis", "cassandra", "dynamodb", "elasticsearch"})
