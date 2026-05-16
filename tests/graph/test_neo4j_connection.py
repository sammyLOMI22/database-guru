"""Unit tests for Phase 25.1 — Neo4j connection layer.

Covers:
* :class:`Neo4jGraphAdapter.test_connection` happy path
* Authentication failure
* Service unavailable / unreachable host
* Timeout
* Driver configuration error
* URI sanitization in logs (no credential leakage)
* ``uri_scheme_forces_tls`` detection — neo4j+s / bolt+s skip the
  ``encrypted=`` kwarg so the driver doesn't raise ConfigurationError.
* ``ConnectionTester._test_neo4j`` thin wrapper.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from neo4j.exceptions import (
    AuthError,
    ConfigurationError,
    DatabaseUnavailable,
    ServiceUnavailable,
)

from src.graph.base import GraphProvider
from src.graph.neo4j.driver_pool import (
    build_driver,
    sanitize_uri_for_log,
    uri_scheme_forces_tls,
)
from src.graph.neo4j.handler import Neo4jGraphAdapter


# ── URI helpers ──────────────────────────────────────────────────────────


class TestUriHelpers:
    @pytest.mark.parametrize(
        "uri,expected",
        [
            ("bolt://localhost:7687", False),
            ("neo4j://localhost", False),
            ("neo4j+s://x.databases.neo4j.io", True),
            ("neo4j+ssc://example.com", True),
            ("bolt+s://example.com", True),
            ("bolt+ssc://example.com", True),
            ("BOLT+S://EXAMPLE.COM", True),  # case-insensitive
            ("", False),
            (None, False),
        ],
    )
    def test_uri_scheme_forces_tls(self, uri, expected):
        assert uri_scheme_forces_tls(uri) is expected

    def test_sanitize_uri_strips_credentials(self):
        sanitized = sanitize_uri_for_log("bolt://neo4j:supersecret@host:7687")
        assert "supersecret" not in sanitized
        assert "neo4j" not in sanitized.split("@")[0]
        assert "host:7687" in sanitized

    def test_sanitize_uri_no_creds_returns_as_is(self):
        assert sanitize_uri_for_log("bolt://host:7687") == "bolt://host:7687"

    def test_sanitize_uri_empty(self):
        assert sanitize_uri_for_log("") == ""


# ── build_driver ─────────────────────────────────────────────────────────


class TestBuildDriver:
    def test_rejects_empty_uri(self):
        with pytest.raises(ValueError, match="URI is required"):
            build_driver("", "neo4j", "pw")

    def test_rejects_whitespace_uri(self):
        with pytest.raises(ValueError, match="URI is required"):
            build_driver("   ", "neo4j", "pw")

    def test_passes_encrypted_for_plain_scheme(self):
        with patch("src.graph.neo4j.driver_pool.AsyncGraphDatabase") as mock_db:
            build_driver("bolt://localhost:7687", "neo4j", "pw", encrypted=True)
            kwargs = mock_db.driver.call_args.kwargs
            assert kwargs["encrypted"] is True
            assert kwargs["auth"] == ("neo4j", "pw")

    def test_omits_encrypted_kwarg_for_secure_scheme(self):
        """neo4j+s URIs already encode TLS; passing encrypted= raises ConfigurationError."""
        with patch("src.graph.neo4j.driver_pool.AsyncGraphDatabase") as mock_db:
            build_driver("neo4j+s://example.com", "neo4j", "pw", encrypted=False)
            kwargs = mock_db.driver.call_args.kwargs
            assert "encrypted" not in kwargs


# ── Adapter.test_connection ─────────────────────────────────────────────


def _make_mock_driver(*, version="5.18.0", edition="community"):
    """Build a mock AsyncDriver whose verify_connectivity + session both succeed."""
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock(return_value=None)
    driver.close = AsyncMock(return_value=None)

    # Async context-manager session that yields a result with a single record.
    record = {"name": "Neo4j Kernel", "versions": [version], "edition": edition}
    mock_record = MagicMock()
    mock_record.get.side_effect = lambda k: record[k]

    result_obj = MagicMock()
    result_obj.single = AsyncMock(return_value=mock_record)

    session = MagicMock()
    session.run = AsyncMock(return_value=result_obj)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    driver.session = MagicMock(return_value=session)
    return driver


class TestNeo4jAdapterTestConnection:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        driver = _make_mock_driver(version="5.18.1", edition="enterprise")
        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="password",
                database_name="neo4j",
            )
        assert result.success is True
        assert result.provider == GraphProvider.NEO4J.value
        assert result.server_version == "5.18.1"
        assert result.edition == "enterprise"
        assert result.database_name == "neo4j"
        assert result.latency_ms is not None and result.latency_ms >= 0
        # Driver should be closed exactly once (the connection-test path never pools).
        driver.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auth_failure(self):
        driver = _make_mock_driver()
        driver.verify_connectivity = AsyncMock(
            side_effect=AuthError("Unauthorized")
        )
        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="wrong",
            )
        assert result.success is False
        assert result.error_code == "authentication_failed"
        assert "Authentication failed" in result.message
        driver.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_database_unavailable(self):
        """DatabaseUnavailable is NOT a subclass of ServiceUnavailable in 5.x —
        verify we map it to a dedicated error_code instead of unknown_error."""
        driver = _make_mock_driver()
        driver.verify_connectivity = AsyncMock(
            side_effect=DatabaseUnavailable("Database 'missing' is unavailable")
        )
        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="pw",
                database_name="missing",
            )
        assert result.success is False
        assert result.error_code == "database_unavailable"
        assert "missing" in result.message
        assert result.database_name == "missing"

    @pytest.mark.asyncio
    async def test_details_raw_is_sanitized(self):
        """ConnectionTestResult.details['raw'] must not leak credentialed URIs.

        Phase 25.2 will return ConnectionTestResult.to_dict() directly to the
        client, so the raw exception text needs sanitizing at the source.
        """
        driver = _make_mock_driver()
        driver.verify_connectivity = AsyncMock(
            side_effect=ServiceUnavailable(
                "Could not connect to bolt://neo4j:supersecret@host:7687"
            )
        )
        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://host:7687",
                username="neo4j",
                password="pw",
            )
        # The driver embedded a credentialed URI in its message — make sure it
        # never leaks through the result payload.
        raw = result.details.get("raw", "")
        assert "supersecret" not in raw
        assert "supersecret" not in result.message

    @pytest.mark.asyncio
    async def test_encrypted_threaded_to_build_driver(self):
        """The UI's TLS toggle must reach build_driver — the old code dropped it."""
        captured = {}

        def fake_build(*args, **kwargs):
            captured.update(kwargs)
            driver = _make_mock_driver()
            return driver

        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", side_effect=fake_build):
            result = await adapter.test_connection(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="pw",
                encrypted=True,
            )
        assert result.success is True
        assert captured.get("encrypted") is True

    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        driver = _make_mock_driver()
        driver.verify_connectivity = AsyncMock(
            side_effect=ServiceUnavailable("Could not resolve address")
        )
        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://offline.invalid:7687",
                username="neo4j",
                password="pw",
            )
        assert result.success is False
        assert result.error_code == "service_unavailable"
        assert "Could not reach database" in result.message
        # Sanitized URI should not embed the password — even though we never supplied one.
        assert "pw" not in result.message

    @pytest.mark.asyncio
    async def test_timeout(self):
        driver = _make_mock_driver()

        async def never_returns():
            await asyncio.sleep(10)

        driver.verify_connectivity = AsyncMock(side_effect=never_returns)
        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://slow.example.com:7687",
                username="neo4j",
                password="pw",
                timeout_ms=200,
            )
        assert result.success is False
        assert result.error_code == "timeout"
        assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_configuration_error(self):
        adapter = Neo4jGraphAdapter()
        with patch(
            "src.graph.neo4j.handler.build_driver",
            side_effect=ConfigurationError("cannot combine +s with encrypted="),
        ):
            result = await adapter.test_connection(
                uri="neo4j+s://example.com",
                username="neo4j",
                password="pw",
                encrypted=True,
            )
        assert result.success is False
        assert result.error_code == "configuration_error"
        assert "configuration" in result.message.lower()

    @pytest.mark.asyncio
    async def test_metadata_probe_failure_is_non_fatal(self):
        """If we can connect but `dbms.components` is denied, still report success."""
        driver = _make_mock_driver()
        bad_session = MagicMock()
        bad_session.run = AsyncMock(side_effect=Exception("permission denied"))
        bad_session.__aenter__ = AsyncMock(return_value=bad_session)
        bad_session.__aexit__ = AsyncMock(return_value=None)
        driver.session = MagicMock(return_value=bad_session)

        adapter = Neo4jGraphAdapter()
        with patch("src.graph.neo4j.handler.build_driver", return_value=driver):
            result = await adapter.test_connection(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="pw",
            )
        assert result.success is True
        # Metadata fields are simply absent.
        assert result.server_version is None
        assert result.edition is None

    @pytest.mark.asyncio
    async def test_empty_uri_short_circuits(self):
        adapter = Neo4jGraphAdapter()
        result = await adapter.test_connection(
            uri="",
            username="neo4j",
            password="pw",
        )
        assert result.success is False
        assert result.error_code == "invalid_uri"

    @pytest.mark.asyncio
    async def test_empty_username_short_circuits(self):
        adapter = Neo4jGraphAdapter()
        result = await adapter.test_connection(
            uri="bolt://localhost:7687",
            username="",
            password="pw",
        )
        assert result.success is False
        assert result.error_code == "invalid_credentials"


# ── ConnectionTester thin wrapper ───────────────────────────────────────


class TestConnectionTesterNeo4j:
    @pytest.mark.asyncio
    async def test_routes_through_adapter(self):
        from src.core.connection_tester import ConnectionTester

        tester = ConnectionTester()

        async def fake_test(*args, **kwargs):
            from src.graph.base import ConnectionTestResult

            return ConnectionTestResult(
                success=True,
                provider="neo4j",
                message="Connection successful",
                server_version="5.18.0",
                edition="community",
            )

        with patch(
            "src.graph.neo4j.handler.Neo4jGraphAdapter.test_connection",
            side_effect=fake_test,
        ):
            result = await tester.test_connection(
                database_type="neo4j",
                host="bolt://localhost:7687",
                port=0,
                database_name="neo4j",
                username="neo4j",
                password="pw",
            )
        assert result["success"] is True
        assert result["server_version"] == "5.18.0"
        assert result["edition"] == "community"

    @pytest.mark.asyncio
    async def test_missing_host_returns_helpful_error(self):
        """Empty host must short-circuit *after* the import-success branch.

        We don't assert on the exact ImportError message because CI may or
        may not have the optional ``neo4j`` driver installed; both outcomes
        are valid as long as the test_connection call surfaces a clear,
        actionable error.
        """
        from src.core.connection_tester import ConnectionTester

        tester = ConnectionTester()
        result = await tester.test_connection(
            database_type="neo4j",
            host="",
            port=0,
            database_name="neo4j",
            username="neo4j",
            password="pw",
        )
        assert result["success"] is False
        # Either the URI-required message (driver installed) or the
        # install-needed message (driver missing) is acceptable here.
        assert any(
            phrase in result["message"]
            for phrase in ("URI is required", "Neo4j support not installed")
        )

    @pytest.mark.asyncio
    async def test_encrypted_flag_threads_through(self):
        from src.core.connection_tester import ConnectionTester

        tester = ConnectionTester()
        captured = {}

        async def fake_test(self, **kwargs):
            captured.update(kwargs)
            from src.graph.base import ConnectionTestResult

            return ConnectionTestResult(success=True, provider="neo4j", message="ok")

        with patch(
            "src.graph.neo4j.handler.Neo4jGraphAdapter.test_connection",
            fake_test,
        ):
            await tester.test_connection(
                database_type="neo4j",
                host="bolt://localhost:7687",
                port=0,
                database_name="neo4j",
                username="neo4j",
                password="pw",
                encrypted=True,
            )
        assert captured.get("encrypted") is True


# ── _sanitize_error regex — broader scheme matching for Phase 25 ────────


class TestSanitizeErrorScheme:
    def test_neo4j_plus_s_uri_is_fully_redacted(self):
        from src.core.connection_tester import _sanitize_error

        leaky = Exception("Failed at neo4j+s://user:pwd@x.databases.neo4j.io:7687/db")
        out = _sanitize_error(leaky)
        # No password, no scheme prefix should leak.
        assert "pwd" not in out
        assert "user" not in out
        assert "neo4j+s" not in out
        assert "<connection-uri-redacted>" in out

    def test_bolt_plus_ssc_uri_is_fully_redacted(self):
        from src.core.connection_tester import _sanitize_error

        leaky = Exception("Bolt+ssc handshake to bolt+ssc://creds@host:7687 failed")
        out = _sanitize_error(leaky)
        assert "creds" not in out
        assert "bolt+ssc" not in out


# ── GRAPH_MODE_ENABLED kill-switch ──────────────────────────────────────


class TestGraphModeKillSwitch:
    def test_create_endpoint_helper_blocks_when_disabled(self):
        """Operators expect GRAPH_MODE_ENABLED=False to actually reject neo4j."""
        from fastapi import HTTPException
        from src.api.endpoints.connections import _ensure_graph_mode_enabled

        class FakeSettings:
            GRAPH_MODE_ENABLED = False

        with pytest.raises(HTTPException) as exc:
            _ensure_graph_mode_enabled("neo4j", FakeSettings())  # type: ignore[arg-type]
        assert exc.value.status_code == 400
        assert "GRAPH_MODE_ENABLED" in exc.value.detail

    def test_create_endpoint_helper_allows_when_enabled(self):
        from src.api.endpoints.connections import _ensure_graph_mode_enabled

        class FakeSettings:
            GRAPH_MODE_ENABLED = True

        # Should not raise.
        _ensure_graph_mode_enabled("neo4j", FakeSettings())  # type: ignore[arg-type]

    def test_kill_switch_does_not_affect_non_graph_types(self):
        from src.api.endpoints.connections import _ensure_graph_mode_enabled

        class FakeSettings:
            GRAPH_MODE_ENABLED = False

        # Postgres/MongoDB/etc. should still pass through.
        for db_type in ("postgresql", "mysql", "mongodb", "redis"):
            _ensure_graph_mode_enabled(db_type, FakeSettings())  # type: ignore[arg-type]


# ── Read-only column semantics (Phase 25.1 fix) ─────────────────────────


class TestReadOnlyResolver:
    def test_resolve_returns_none_for_non_graph(self):
        from src.api.endpoints.connections import (
            ConnectionCreate,
            _resolve_read_only,
        )

        c = ConnectionCreate(name="x", database_type="postgresql", host="h", database_name="d")
        assert _resolve_read_only(c) is None

    def test_resolve_defaults_true_for_neo4j_without_explicit(self):
        from src.api.endpoints.connections import (
            ConnectionCreate,
            _resolve_read_only,
        )

        c = ConnectionCreate(
            name="x",
            database_type="neo4j",
            host="bolt://localhost:7687",
            username="neo4j",
            password="pw",
        )
        assert _resolve_read_only(c) is True

    def test_resolve_honours_explicit_false_for_neo4j(self):
        from src.api.endpoints.connections import (
            ConnectionCreate,
            _resolve_read_only,
        )

        c = ConnectionCreate(
            name="x",
            database_type="neo4j",
            host="bolt://localhost:7687",
            username="neo4j",
            password="pw",
            read_only=False,
        )
        assert _resolve_read_only(c) is False


# ── Driver pool concurrency (Phase 25.1 fix) ────────────────────────────


class TestDriverPoolLocking:
    @pytest.mark.asyncio
    async def test_concurrent_get_creates_one_driver(self):
        """Two coroutines racing on the same connection_id must share a driver.

        Previously the pool read ``_drivers.get`` outside any lock, so both
        callers could miss the cache, both call ``build_driver``, and one
        driver would silently leak (overwritten in the dict without close).
        """
        from src.graph.neo4j.driver_pool import Neo4jDriverPool

        build_count = 0

        def fake_build(*args, **kwargs):
            nonlocal build_count
            build_count += 1
            d = MagicMock()
            d.close = AsyncMock()
            return d

        pool = Neo4jDriverPool()
        with patch("src.graph.neo4j.driver_pool.build_driver", side_effect=fake_build):
            results = await asyncio.gather(
                pool.get(42, "bolt://localhost:7687", "neo4j", "pw"),
                pool.get(42, "bolt://localhost:7687", "neo4j", "pw"),
                pool.get(42, "bolt://localhost:7687", "neo4j", "pw"),
            )

        assert build_count == 1
        # All callers got the same driver instance.
        assert results[0] is results[1] is results[2]
        await pool.close_all()


# ── Integration skeleton — opt-in via NEO4J_TEST_URI env var ────────────


import os  # noqa: E402  (kept here so the marker file stays self-documenting)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("NEO4J_TEST_URI"),
    reason="Set NEO4J_TEST_URI (e.g. bolt://localhost:7687) to run against a real Neo4j container",
)
class TestNeo4jIntegration:
    """Round-trips a real Bolt handshake against a running Neo4j instance.

    Spin up the bundled container with ``docker compose --profile graph up -d``
    and run with::

        NEO4J_TEST_URI=bolt://localhost:7687 \\
            NEO4J_TEST_USER=neo4j NEO4J_TEST_PASSWORD=password \\
            pytest -m integration tests/graph/
    """

    @pytest.mark.asyncio
    async def test_real_connection(self):
        adapter = Neo4jGraphAdapter()
        result = await adapter.test_connection(
            uri=os.environ["NEO4J_TEST_URI"],
            username=os.environ.get("NEO4J_TEST_USER", "neo4j"),
            password=os.environ.get("NEO4J_TEST_PASSWORD", "password"),
            database_name=os.environ.get("NEO4J_TEST_DB", "neo4j"),
        )
        assert result.success is True
        assert result.server_version is not None
