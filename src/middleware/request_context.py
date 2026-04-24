"""Request-context middleware (Phase 24.1).

Assigns a request_id to every incoming request (from the X-Request-ID header
if a client supplied one, otherwise a fresh uuid4) and binds it into a
contextvar so every structlog call made during the request carries it. Also
reflects the id back on the response as X-Request-ID to aid correlation.

user_id is bound only when the rate-limit middleware already decoded a valid
JWT for this request — we never re-parse auth headers here.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import Settings
from src.observability import metrics
from src.observability.logging_config import (
    get_logger,
    set_request_id,
    set_user_id,
)


_REQUEST_ID_HEADER = "x-request-id"
_MAX_HEADER_LEN = 128

logger = get_logger(__name__)


def _sanitize_request_id(value: Optional[str]) -> Optional[str]:
    """Accept only short printable IDs from clients. Reject anything weird."""
    if not value:
        return None
    value = value.strip()
    if not value or len(value) > _MAX_HEADER_LEN:
        return None
    if not all(ch.isalnum() or ch in ("-", "_") for ch in value):
        return None
    return value


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request_id + optional user_id to the structlog context."""

    def __init__(self, app, settings: Optional[Settings] = None):
        super().__init__(app)
        s = settings or Settings()
        self._include_request_id = bool(
            getattr(s, "LOG_INCLUDE_REQUEST_ID", True)
        )
        self._include_user_id = bool(
            getattr(s, "LOG_INCLUDE_USER_ID", False)
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid: Optional[str] = None
        if self._include_request_id:
            rid = (
                _sanitize_request_id(request.headers.get(_REQUEST_ID_HEADER))
                or uuid.uuid4().hex
            )
            set_request_id(rid)
            # Expose to downstream handlers that want to read it off the scope.
            request.state.request_id = rid
        else:
            set_request_id(None)

        set_user_id(None)

        start = time.perf_counter()
        status_code: int = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            if rid is not None:
                response.headers["X-Request-ID"] = rid
            # After the endpoint has run, auth dependencies may have populated
            # request.state.user_id. Bind it if the feature is enabled.
            if self._include_user_id:
                uid = getattr(request.state, "user_id", None)
                if uid is not None:
                    set_user_id(str(uid))
            return response
        finally:
            duration_s = time.perf_counter() - start
            route = _route_template(request)
            # Single terse access log line. No query strings, no bodies.
            try:
                logger.info(
                    "http_request",
                    method=request.method,
                    route=route,
                    status_code=status_code,
                    duration_ms=round(duration_s * 1000.0, 2),
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                metrics.record_http_request(
                    method=request.method,
                    route=route,
                    status_code=status_code,
                    duration_s=duration_s,
                )
            except Exception:  # noqa: BLE001
                pass
            # Clear contextvars so no value leaks to the next task on the loop.
            set_request_id(None)
            set_user_id(None)


def _route_template(request: Request) -> str:
    """Return the matched route template (e.g. ``/api/chat/{session_id}``).

    Falls back to a constant ``"unmatched"`` for paths that did not match any
    route — using ``request.url.path`` here would let an attacker explode
    metric cardinality by hitting random URLs.
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return path
    return "unmatched"
