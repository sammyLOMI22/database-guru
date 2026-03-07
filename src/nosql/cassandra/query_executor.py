"""Cassandra CQL executor - runs CQL queries via cassandra-driver in thread pool."""
import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional

from src.nosql.result_formatter import normalize_nosql_result

logger = logging.getLogger(__name__)

# CQL write keywords
_WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"}
_ALLOWED_FIRST_KEYWORDS = {"SELECT", "INSERT", "UPDATE", "DELETE", "USE"}


class CassandraQueryExecutor:
    """Execute CQL queries safely with timeout."""

    def __init__(
        self,
        session,  # cassandra-driver Session (sync)
        max_rows: int = 1000,
        timeout_seconds: int = 30,
        allow_write: bool = False,
    ):
        self.session = session
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.allow_write = allow_write

    def _validate_cql(self, cql: str) -> Optional[str]:
        """Validate CQL statement for injection risks.

        Returns an error message if invalid, None if OK.
        """
        stripped = cql.strip()
        if not stripped:
            return "Empty query"

        # Strip single-quoted string literals (handling escaped quotes '')
        without_strings = re.sub(r"'(?:[^']|'')*'", "", stripped)

        # Strip block comments
        without_comments = re.sub(r"/\*.*?\*/", "", without_strings, flags=re.DOTALL)

        # Block multi-statement injection via semicolons
        # Allow a trailing semicolon but reject multiple statements
        statements = [s.strip() for s in without_comments.split(";") if s.strip()]
        if len(statements) > 1:
            return "Multi-statement queries are not allowed (semicolons detected)"

        # Check the first keyword after stripping comments from the original
        cleaned = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL).strip()
        first_word = cleaned.split()[0].upper() if cleaned.split() else ""
        if first_word not in _ALLOWED_FIRST_KEYWORDS:
            return f"Unsupported CQL statement type: '{first_word}'. Only SELECT/INSERT/UPDATE/DELETE/USE allowed."

        return None

    async def execute(self, cql: str) -> Dict[str, Any]:
        """Execute a CQL string and return a normalized result dict."""
        # Validate for injection risks
        validation_error = self._validate_cql(cql)
        if validation_error:
            return normalize_nosql_result(
                data=[], execution_time_ms=0, error=validation_error,
            )

        # Write check on the cleaned first keyword
        cleaned = re.sub(r"/\*.*?\*/", "", cql.strip(), flags=re.DOTALL).strip()
        first_word = cleaned.split()[0].upper() if cleaned.split() else ""
        if first_word in _WRITE_KEYWORDS and not self.allow_write:
            return normalize_nosql_result(
                data=[],
                execution_time_ms=0,
                error=f"Write operation '{first_word}' not allowed. Enable allow_write.",
            )

        start_time = time.time()

        try:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._execute_sync, cql),
                timeout=self.timeout_seconds,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=result,
                execution_time_ms=elapsed_ms,
                max_rows=self.max_rows,
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms,
                error=f"CQL query timed out after {self.timeout_seconds}s",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"CQL execution error: {e}", exc_info=True)
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms, error=str(e),
            )

    def _execute_sync(self, cql: str) -> List[Dict]:
        """Execute CQL synchronously and convert ResultSet to list of dicts."""
        result_set = self.session.execute(cql)

        rows = []
        for i, row in enumerate(result_set):
            if i >= self.max_rows:
                break
            # Convert Row to dict
            rows.append(dict(row._asdict()))

        return rows
