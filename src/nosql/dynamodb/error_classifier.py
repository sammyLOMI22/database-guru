"""DynamoDB error classifier."""
import logging
from typing import Tuple

from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)


def classify_error(error_message: str) -> Tuple[ErrorType, str]:
    msg = error_message.lower()

    if "resourcenotfoundexception" in msg or "table" in msg and "not found" in msg:
        return ErrorType.TABLE_NOT_FOUND, f"Table not found. Check table name. Error: {error_message}"

    if "validationexception" in msg:
        if "key" in msg:
            return ErrorType.COLUMN_NOT_FOUND, f"Key attribute issue. Error: {error_message}"
        return ErrorType.SYNTAX_ERROR, f"Validation error. Error: {error_message}"

    if "partiql" in msg and "syntax" in msg:
        return ErrorType.SYNTAX_ERROR, f"PartiQL syntax error. Error: {error_message}"

    if "accessdenied" in msg or "not authorized" in msg:
        return ErrorType.PERMISSION_DENIED, "AWS permission denied."

    if "timeout" in msg or "timed out" in msg:
        return ErrorType.TIMEOUT, "Query timed out."

    return ErrorType.UNKNOWN, f"DynamoDB error: {error_message}"
