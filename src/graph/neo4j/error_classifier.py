"""Map ``neo4j`` driver exceptions into UX-friendly categories (Phase 25.3).

The driver raises a handful of exception classes with code strings like
``Neo.ClientError.Schema.SyntaxError``. We translate those into a small
set of categories the frontend can render with consistent messages
without leaking the raw driver string (which can embed URIs or stack
traces).

``classify_error(exc)`` always returns a :class:`ClassifiedError`. It
never re-raises — callers should pass the original exception straight
through to ``logger.exception`` for the server-side trace, then surface
``classified.user_message`` to the API consumer.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class GraphErrorCategory(str, Enum):
    SYNTAX = "syntax"
    UNKNOWN_LABEL = "unknown_label"
    UNKNOWN_PROPERTY = "unknown_property"
    UNKNOWN_REL_TYPE = "unknown_rel_type"
    AUTH = "auth"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    CONSTRAINT_VIOLATION = "constraint_violation"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedError:
    category: GraphErrorCategory
    user_message: str
    code: Optional[str] = None  # Neo4j status code if available, e.g. ``Neo.ClientError.Schema.SyntaxError``
    hint: Optional[str] = None  # Optional next-step hint shown under the message


# ── Code → category map ───────────────────────────────────────────────────


# Anchored exact match against the Neo4j status code string.
_CODE_MAP = {
    "Neo.ClientError.Statement.SyntaxError": (
        GraphErrorCategory.SYNTAX,
        "Cypher syntax error.",
        "Check parentheses, missing commas, and clause order (MATCH → WHERE → RETURN).",
    ),
    "Neo.ClientError.Statement.SemanticError": (
        GraphErrorCategory.SYNTAX,
        "Cypher semantic error.",
        "The query parses but doesn't make sense — usually a misnamed function or aggregation outside RETURN.",
    ),
    "Neo.ClientError.Statement.ParameterMissing": (
        GraphErrorCategory.SYNTAX,
        "A required parameter is missing.",
        "Pass the parameter via the request body or inline the value.",
    ),
    "Neo.ClientError.Security.Unauthorized": (
        GraphErrorCategory.AUTH,
        "Authentication failed.",
        "Confirm the username and password on the connection settings.",
    ),
    "Neo.ClientError.Security.Forbidden": (
        GraphErrorCategory.PERMISSION,
        "Your Neo4j user is not allowed to run this query.",
        "Ask a database admin for read access to the labels involved.",
    ),
    "Neo.ClientError.Schema.ConstraintValidationFailed": (
        GraphErrorCategory.CONSTRAINT_VIOLATION,
        "The query violates a schema constraint.",
        None,
    ),
    "Neo.ClientError.Procedure.ProcedureNotFound": (
        GraphErrorCategory.SYNTAX,
        "The procedure is not installed on this Neo4j instance.",
        "Verify the procedure name and the database version.",
    ),
    "Neo.TransientError.Network.CommunicationError": (
        GraphErrorCategory.CONNECTION,
        "Lost the connection to Neo4j.",
        "Check the URI and that the server is reachable.",
    ),
}

# Match Cypher warnings the driver returns as exceptions referencing
# missing labels/properties. The driver wraps these in slightly different
# code strings across 5.x versions, so we also pattern-match the message.
_LABEL_PATTERN = re.compile(
    r"(?:label|missing label|unknown label):?\s*[`']?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
_PROPERTY_PATTERN = re.compile(
    r"(?:property|missing property|unknown property|no such property):?\s*[`']?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
_RELTYPE_PATTERN = re.compile(
    r"(?:relationship type|missing relationship type|unknown relationship type):?\s*[`']?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def _extract_code(exc: BaseException) -> Optional[str]:
    """Pull the ``code`` attribute the neo4j driver attaches when known."""
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        return code
    return None


def classify_error(exc: BaseException) -> ClassifiedError:
    """Return a :class:`ClassifiedError` for any exception bubbling up
    from the driver.

    The function is total — even unrecognised exceptions get a sensible
    UNKNOWN category so the caller can render a generic message.
    """
    # 1) Concrete asyncio / Python types take precedence.
    if isinstance(exc, asyncio.TimeoutError):
        return ClassifiedError(
            category=GraphErrorCategory.TIMEOUT,
            user_message="Query timed out before Neo4j responded.",
            hint="Add a tighter LIMIT, narrow the MATCH pattern, or raise GRAPH_QUERY_TIMEOUT_MS.",
        )

    code = _extract_code(exc)
    if code and code in _CODE_MAP:
        category, msg, hint = _CODE_MAP[code]
        return ClassifiedError(category=category, user_message=msg, code=code, hint=hint)

    # 2) Class-name based heuristics for exceptions we don't import to
    #    avoid a hard dependency on the neo4j module here.
    cls_name = type(exc).__name__
    text = str(exc) or ""

    if cls_name in {"AuthError", "AuthenticationRateLimit"}:
        return ClassifiedError(
            category=GraphErrorCategory.AUTH,
            user_message="Authentication failed.",
            code=code,
            hint="Double-check the connection's username and password.",
        )
    if cls_name in {"ServiceUnavailable", "SessionExpired", "ConfigurationError", "DriverError"}:
        return ClassifiedError(
            category=GraphErrorCategory.CONNECTION,
            user_message="Could not reach the Neo4j server.",
            code=code,
            hint="Verify the Bolt URI scheme (bolt:// vs neo4j+s://) and that the host is reachable.",
        )

    # 3) Schema warnings — try to extract the missing identifier so the
    #    UI can surface "Did you mean ...?".
    if "warning" in cls_name.lower() or "ClientNotification" in cls_name:
        match = _LABEL_PATTERN.search(text)
        if match:
            return ClassifiedError(
                category=GraphErrorCategory.UNKNOWN_LABEL,
                user_message=f"Unknown label: {match.group(1)}.",
                code=code,
                hint="Open the Schema tab to see the labels Neo4j actually has.",
            )
        match = _RELTYPE_PATTERN.search(text)
        if match:
            return ClassifiedError(
                category=GraphErrorCategory.UNKNOWN_REL_TYPE,
                user_message=f"Unknown relationship type: {match.group(1)}.",
                code=code,
            )
        match = _PROPERTY_PATTERN.search(text)
        if match:
            return ClassifiedError(
                category=GraphErrorCategory.UNKNOWN_PROPERTY,
                user_message=f"Unknown property: {match.group(1)}.",
                code=code,
            )

    # 4) Fall-through.
    return ClassifiedError(
        category=GraphErrorCategory.UNKNOWN,
        user_message="Neo4j rejected the query.",
        code=code,
        hint="Check the server logs for the full error.",
    )


__all__ = [
    "ClassifiedError",
    "GraphErrorCategory",
    "classify_error",
]
