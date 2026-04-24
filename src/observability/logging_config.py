"""Structured logging configuration (Phase 24.1).

Centralizes structlog configuration so stdlib logging.getLogger(...) calls and
structlog.get_logger(...) calls share a single formatter pipeline. In
production this renders JSON; in development it renders a readable key=value
stream.

Safe under repeated calls — alembic's fileConfig() disables existing loggers,
so configure_logging() may be called again after migrations without creating
duplicate handlers.
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog

from src.config.settings import Settings


# Request-scoped context. Populated by RequestContextMiddleware and read by the
# structlog merge_contextvars processor on every log call.
_REQUEST_ID: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_USER_ID: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


# Sensitive keys that must never appear in log output even if code accidentally
# passes them through. Matched case-insensitively.
_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "cookies",
        "set-cookie",
        "api_key",
        "apikey",
        "api-key",
        "bearer",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "prompt",
        "sql",
        "query",
        "response_text",
        "result_rows",
    }
)

_REDACTED = "[REDACTED]"


def redact_sensitive(
    logger: Any = None,
    method_name: str = "",
    event_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """structlog processor that redacts known-sensitive keys.

    Applied to both structlog and stdlib logging paths so an accidental
    ``logger.info("x", authorization=...)`` call is still scrubbed. Signature
    matches structlog's 3-arg processor contract but also tolerates being
    called directly with just the event dict for ad-hoc use.
    """
    if event_dict is None:
        # Single-arg compatibility: redact_sensitive({"authorization": ...}).
        event_dict = logger if isinstance(logger, dict) else {}
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = _REDACTED
    return event_dict


def _inject_request_context(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Pull request_id/user_id from contextvars into every log record."""
    rid = _REQUEST_ID.get()
    if rid is not None and "request_id" not in event_dict:
        event_dict["request_id"] = rid
    uid = _USER_ID.get()
    if uid is not None and "user_id" not in event_dict:
        event_dict["user_id"] = uid
    return event_dict


def set_request_id(request_id: Optional[str]) -> None:
    _REQUEST_ID.set(request_id)


def get_request_id() -> Optional[str]:
    return _REQUEST_ID.get()


def set_user_id(user_id: Optional[str]) -> None:
    _USER_ID.set(user_id)


def get_user_id() -> Optional[str]:
    return _USER_ID.get()


_CONFIGURED = False


def configure_logging(settings: Optional[Settings] = None, *, force: bool = False) -> None:
    """Install structlog + stdlib logging pipeline.

    Called at startup and again after Alembic resets logging state. Idempotent
    unless ``force=True``.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    settings = settings or Settings()
    level_name = (getattr(settings, "LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = (getattr(settings, "LOG_FORMAT", "console") or "console").lower()

    # Shared processors: add context, redact secrets, standard timestamp/level.
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        _inject_request_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_sensitive,
    ]

    if fmt == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Install a single handler on the root stdlib logger so existing
    # logging.getLogger(...).info(...) calls flow through the same pipeline.
    root = logging.getLogger()
    # Replace any prior handler we installed; keep alien handlers off.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)
    # Re-enable any logger that alembic may have disabled on reload, and strip
    # handlers that libraries (notably SQLAlchemy) attached directly so output
    # flows through the configured pipeline once instead of being duplicated.
    for name in logging.Logger.manager.loggerDict:
        lg = logging.getLogger(name)
        lg.disabled = False
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.propagate = True

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> Any:
    """Return a structlog logger. Use this for new code that wants structured
    key=value logging. Existing ``logging.getLogger(...)`` callers continue to
    work against the same formatter pipeline.
    """
    return structlog.get_logger(name)
