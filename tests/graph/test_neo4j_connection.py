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

from neo4j.exceptions import AuthError, ConfigurationError, ServiceUnavailable

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
        assert "URI is required" in result["message"]
