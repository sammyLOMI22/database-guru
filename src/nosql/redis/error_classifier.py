"""Redis error classifier - maps redis-py exceptions to ErrorType enum."""
import logging
from typing import Tuple

from src.llm.self_correcting_agent import ErrorType

logger = logging.getLogger(__name__)


def classify_error(error_message: str) -> Tuple[ErrorType, str]:
    """Classify a Redis error and return (ErrorType, hint)."""
    msg = error_message.lower()

    if "unknown command" in msg or "err unknown" in msg:
        return (
            ErrorType.SYNTAX_ERROR,
            f"Unknown Redis command. Check command spelling. Error: {error_message}",
        )

    if "wrong number of arguments" in msg or "wrong type" in msg:
        return (
            ErrorType.SYNTAX_ERROR,
            f"Wrong arguments for command. Check argument count and types. Error: {error_message}",
        )

    if "wrongtype" in msg:
        return (
            ErrorType.TYPE_MISMATCH,
            f"Key holds wrong data type. Check key type with TYPE command. Error: {error_message}",
        )

    if "noauth" in msg or "denied" in msg or "noperm" in msg:
        return (
            ErrorType.PERMISSION_DENIED,
            "Authentication or permission error.",
        )

    if "timeout" in msg or "timed out" in msg:
        return ErrorType.TIMEOUT, "Command timed out."

    return ErrorType.UNKNOWN, f"Redis error: {error_message}"
