"""DynamoDB query executor - runs PartiQL via aioboto3."""
import asyncio
import logging
import re
import time
from typing import Any, Dict, List

from src.nosql.result_formatter import normalize_nosql_result

logger = logging.getLogger(__name__)

_WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}
_ALLOWED_FIRST_KEYWORDS = {"SELECT", "INSERT", "UPDATE", "DELETE"}


class DynamoDBQueryExecutor:
    """Execute PartiQL queries against DynamoDB."""

    def __init__(
        self,
        session,  # aioboto3.Session
        region: str,
        max_rows: int = 1000,
        timeout_seconds: int = 30,
        allow_write: bool = False,
    ):
        self.session = session
        self.region = region
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.allow_write = allow_write

    def _validate_partiql(self, partiql: str) -> str | None:
        """Validate PartiQL statement for injection risks.

        Returns an error message if invalid, None if OK.
        """
        stripped = partiql.strip()
        if not stripped:
            return "Empty query"

        # Block multi-statement injection via semicolons
        # Remove single-quoted string literals (handling escaped quotes '') before checking
        without_strings = re.sub(r"'(?:[^']|'')*'", "", stripped)
        if ";" in without_strings:
            return "Multi-statement queries are not allowed (semicolons detected)"

        # Only allow known PartiQL statement types
        first_word = stripped.split()[0].upper()
        if first_word not in _ALLOWED_FIRST_KEYWORDS:
            return f"Unsupported PartiQL statement type: '{first_word}'. Only SELECT/INSERT/UPDATE/DELETE allowed."

        return None

    async def execute(self, partiql: str) -> Dict[str, Any]:
        """Execute a PartiQL string and return a normalized result."""
        # Validate for injection risks
        validation_error = self._validate_partiql(partiql)
        if validation_error:
            return normalize_nosql_result(
                data=[], execution_time_ms=0, error=validation_error,
            )

        first_word = partiql.strip().split()[0].upper()
        if first_word in _WRITE_KEYWORDS and not self.allow_write:
            return normalize_nosql_result(
                data=[], execution_time_ms=0,
                error=f"Write operation '{first_word}' not allowed.",
            )

        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._execute_partiql(partiql),
                timeout=self.timeout_seconds,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=result, execution_time_ms=elapsed_ms,
                max_rows=self.max_rows,
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms,
                error=f"Query timed out after {self.timeout_seconds}s",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"DynamoDB query error: {e}", exc_info=True)
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms, error=str(e),
            )

    async def _execute_partiql(self, partiql: str) -> List[Dict]:
        """Execute PartiQL and deserialize DynamoDB items."""
        async with self.session.client("dynamodb", region_name=self.region) as client:
            response = await client.execute_statement(
                Statement=partiql,
                Limit=self.max_rows,
            )

            items = response.get("Items", [])
            return [self._deserialize_item(item) for item in items]

    def _deserialize_item(self, item: Dict) -> Dict:
        """Convert DynamoDB typed dict to plain dict."""
        result = {}
        for key, val in item.items():
            result[key] = self._deserialize_value(val)
        return result

    def _deserialize_value(self, val: Dict) -> Any:
        """Convert a single DynamoDB typed value."""
        if "S" in val:
            return val["S"]
        if "N" in val:
            n = val["N"]
            return int(n) if "." not in n else float(n)
        if "BOOL" in val:
            return val["BOOL"]
        if "NULL" in val:
            return None
        if "L" in val:
            return [self._deserialize_value(v) for v in val["L"]]
        if "M" in val:
            return {k: self._deserialize_value(v) for k, v in val["M"].items()}
        if "SS" in val:
            return list(val["SS"])
        if "NS" in val:
            return [float(n) if "." in n else int(n) for n in val["NS"]]
        if "B" in val:
            return f"<binary {len(val['B'])} bytes>"
        return str(val)
