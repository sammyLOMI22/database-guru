"""Shared constants for the DML module (Phase 18)."""
import re

# Only allow safe SQL identifiers (letters, digits, underscores).
# Used by both the generator and validator to prevent injection.
SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Supported SQL dialects for DML generation
SUPPORTED_DIALECTS = frozenset({"postgresql", "sqlite", "duckdb", "oracle", "mysql", "mssql"})
