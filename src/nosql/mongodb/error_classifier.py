"""MongoDB error classifier - maps pymongo exceptions to ErrorType enum.

Used by the MongoDB handler's retry loop to provide meaningful error hints
for self-correction.
"""
import logging
import re
from typing import Optional, Tuple

from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)

# Patterns that indicate specific error types
_FIELD_NOT_FOUND = re.compile(
    r"(path|field) '([^']+)' (doesn't exist|not found|is not)",
    re.IGNORECASE,
)
_COLLECTION_NOT_FOUND = re.compile(
    r"(collection|namespace) '?([^']+)'? (not found|does not exist)",
    re.IGNORECASE,
)
_SYNTAX_PATTERNS = [
    "unknown operator",
    "bad query",
    "invalid operator",
    "unknown top level operator",
    "unrecognized expression",
    "failed to parse",
    "invalid pipeline",
    "$match requires",
    "a]ggregation pipeline",
]
_TYPE_MISMATCH_PATTERNS = [
    "can't convert",
    "cannot apply",
    "type mismatch",
    "expected type",
    "cannot compare",
]


def classify_error(error_message: str) -> Tuple[ErrorType, str]:
    """Classify a MongoDB error and return (ErrorType, hint).

    Args:
        error_message: The error string from pymongo

    Returns:
        Tuple of (ErrorType, human-readable hint for the LLM retry prompt)
    """
    msg = error_message.lower()

    # Check for field/path not found
    match = _FIELD_NOT_FOUND.search(error_message)
    if match:
        field_name = match.group(2)
        return (
            ErrorType.COLUMN_NOT_FOUND,
            f"Field '{field_name}' does not exist. Check the schema for valid field names.",
        )

    # Check for collection not found
    match = _COLLECTION_NOT_FOUND.search(error_message)
    if match:
        coll_name = match.group(2)
        return (
            ErrorType.TABLE_NOT_FOUND,
            f"Collection '{coll_name}' not found. Check the schema for valid collection names.",
        )

    # Check for syntax errors
    for pattern in _SYNTAX_PATTERNS:
        if pattern in msg:
            return (
                ErrorType.SYNTAX_ERROR,
                f"MQL syntax error: {error_message}. Ensure operators and pipeline stages are valid.",
            )

    # Check for type mismatches
    for pattern in _TYPE_MISMATCH_PATTERNS:
        if pattern in msg:
            return (
                ErrorType.TYPE_MISMATCH,
                f"Type mismatch: {error_message}. Check field types in the schema.",
            )

    # Check for permission errors
    if "not authorized" in msg or "unauthorized" in msg:
        return (
            ErrorType.PERMISSION_DENIED,
            "Not authorized to perform this operation.",
        )

    # Check for timeout
    if "timed out" in msg or "timeout" in msg:
        return ErrorType.TIMEOUT, "Query timed out. Try simplifying the query."

    # Unknown error
    return ErrorType.UNKNOWN, f"MongoDB error: {error_message}"
