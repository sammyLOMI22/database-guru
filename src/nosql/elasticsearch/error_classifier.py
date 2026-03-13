"""Elasticsearch error classifier."""
import logging
from typing import Tuple

from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)


def classify_error(error_message: str) -> Tuple[ErrorType, str]:
    msg = error_message.lower()

    if "index_not_found" in msg or "no such index" in msg:
        return ErrorType.TABLE_NOT_FOUND, f"Index not found. Check index name. Error: {error_message}"

    if "unknown field" in msg or "no mapping found" in msg:
        return ErrorType.COLUMN_NOT_FOUND, f"Field not found. Check field names. Error: {error_message}"

    if "parsing_exception" in msg or "query_shard_exception" in msg:
        return ErrorType.SYNTAX_ERROR, f"Query DSL syntax error. Error: {error_message}"

    if "illegal_argument" in msg or "search_phase_execution" in msg:
        return ErrorType.TYPE_MISMATCH, f"Type/argument error. Error: {error_message}"

    if "security_exception" in msg or "unauthorized" in msg:
        return ErrorType.PERMISSION_DENIED, "Permission denied."

    if "timeout" in msg:
        return ErrorType.TIMEOUT, "Query timed out."

    return ErrorType.UNKNOWN, f"Elasticsearch error: {error_message}"
