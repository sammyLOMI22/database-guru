"""Cassandra error classifier - maps cassandra-driver exceptions to ErrorType."""
import logging
from typing import Tuple

from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)


def classify_error(error_message: str) -> Tuple[ErrorType, str]:
    """Classify a Cassandra CQL error."""
    msg = error_message.lower()

    if "unconfigured table" in msg or "table" in msg and "not found" in msg:
        return ErrorType.TABLE_NOT_FOUND, f"Table not found. Check schema. Error: {error_message}"

    if "undefined column" in msg or "unknown column" in msg:
        return ErrorType.COLUMN_NOT_FOUND, f"Column not found. Check column names. Error: {error_message}"

    if "syntax error" in msg or "mismatched input" in msg or "no viable alternative" in msg:
        return ErrorType.SYNTAX_ERROR, f"CQL syntax error. Error: {error_message}"

    if "cannot execute" in msg and "filtering" in msg:
        return (
            ErrorType.SYNTAX_ERROR,
            "Query requires ALLOW FILTERING or must include partition key in WHERE clause.",
        )

    if "type error" in msg or "cannot assign" in msg:
        return ErrorType.TYPE_MISMATCH, f"Type mismatch. Error: {error_message}"

    if "unauthorized" in msg or "permission" in msg:
        return ErrorType.PERMISSION_DENIED, "Permission denied."

    if "timeout" in msg:
        return ErrorType.TIMEOUT, "Query timed out."

    return ErrorType.UNKNOWN, f"Cassandra error: {error_message}"
