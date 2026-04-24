"""Phase 24.1 — structured logging + request_id propagation."""
from __future__ import annotations

import json
import logging
import re
import uuid
from io import StringIO
from typing import List

import pytest

from src.config.settings import Settings
from src.observability import logging_config
from src.observability.logging_config import (
    configure_logging,
    get_logger,
    get_request_id,
    redact_sensitive,
    set_request_id,
)


def _capture_logs(monkeypatch, log_format: str = "json") -> StringIO:
    """Reconfigure logging to write to an in-memory stream and return it."""
    settings = Settings(LOG_FORMAT=log_format, LOG_LEVEL="INFO")
    configure_logging(settings, force=True)

    buf = StringIO()
    handler = logging.StreamHandler(buf)
    # Reuse the formatter the configured root handler is using so we exercise
    # the real pipeline rather than a parallel one.
    root = logging.getLogger()
    if root.handlers:
        handler.setFormatter(root.handlers[0].formatter)
    root.addHandler(handler)
    return buf


def test_json_logging_renders_valid_json(monkeypatch):
    buf = _capture_logs(monkeypatch, log_format="json")
    log = get_logger("dbguru.test")
    log.info("hello", thing="value")

    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    assert lines, "expected at least one JSON log line"
    record = json.loads(lines[-1])
    assert record["event"] == "hello"
    assert record["thing"] == "value"
    assert record["level"] == "info"
    assert "timestamp" in record


def test_console_logging_is_human_readable(monkeypatch):
    buf = _capture_logs(monkeypatch, log_format="console")
    log = get_logger("dbguru.test")
    log.info("hello_console", k=1)

    text = buf.getvalue()
    assert "hello_console" in text
    # Console formatter should not emit machine JSON for a simple line.
    assert not text.strip().startswith("{")


def test_request_id_propagates_into_log_records(monkeypatch):
    buf = _capture_logs(monkeypatch, log_format="json")
    log = get_logger("dbguru.test")
    rid = uuid.uuid4().hex
    set_request_id(rid)
    try:
        log.info("with_rid")
    finally:
        set_request_id(None)
    record = json.loads(buf.getvalue().splitlines()[-1])
    assert record["request_id"] == rid


def test_sensitive_keys_are_redacted_at_processor_level():
    out = redact_sensitive(
        {
            "authorization": "Bearer xxx",
            "password": "p4ss",
            "api_key": "abcd",
            "ok": "value",
        }
    )
    assert out["authorization"] == "[REDACTED]"
    assert out["password"] == "[REDACTED]"
    assert out["api_key"] == "[REDACTED]"
    assert out["ok"] == "value"


def test_redaction_applies_in_full_pipeline(monkeypatch):
    buf = _capture_logs(monkeypatch, log_format="json")
    log = get_logger("dbguru.test")
    log.info("call", authorization="Bearer SECRET", prompt="dont leak")
    record = json.loads(buf.getvalue().splitlines()[-1])
    assert record["authorization"] == "[REDACTED]"
    assert record["prompt"] == "[REDACTED]"


def test_stdlib_logger_calls_share_pipeline(monkeypatch):
    buf = _capture_logs(monkeypatch, log_format="json")
    set_request_id("rid-stdlib")
    try:
        logging.getLogger("legacy.module").warning("legacy %s", "ok")
    finally:
        set_request_id(None)
    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    record = json.loads(lines[-1])
    assert record["event"].startswith("legacy")
    assert record["level"] == "warning"
    assert record["request_id"] == "rid-stdlib"


def test_configure_logging_is_idempotent():
    s = Settings(LOG_FORMAT="json")
    configure_logging(s, force=True)
    handler_count = len(logging.getLogger().handlers)
    configure_logging(s)  # no force → must not duplicate
    assert len(logging.getLogger().handlers) == handler_count
