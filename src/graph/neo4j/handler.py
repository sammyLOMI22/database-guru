"""Neo4j adapter implementation (Phase 25.1).

Phase 25.1 ships :meth:`test_connection` only. Schema introspection,
Cypher execution, and AI-assisted query generation arrive in 25.2+.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from neo4j.exceptions import (
    AuthError,
    ConfigurationError,
    ServiceUnavailable,
)

from src.graph.base import ConnectionTestResult, GraphAdapter, GraphProvider
from src.graph.neo4j.driver_pool import (
    build_driver,
    sanitize_uri_for_log,
    uri_scheme_forces_tls,
)

logger = logging.getLogger(__name__)


class Neo4jGraphAdapter(GraphAdapter):
    """Adapter for Neo4j 5.x via the official async Bolt driver."""

    provider = GraphProvider.NEO4J

    async def test_connection(
        self,
        uri: str,
        username: str,
        password: str,
        database_name: Optional[str] = None,
        encrypted: bool = False,
        timeout_ms: int = 5000,
    ) -> ConnectionTestResult:
        """Open a short-lived driver, verify connectivity, and tear it down.

        Failure cases are mapped to human-readable messages aligned with the
        spec §13 categories: unreachable, authentication failed, unknown
        database, TLS/encryption mismatch, driver/config issue.
        """
        if not uri or not uri.strip():
            return ConnectionTestResult(
                success=False,
                provider=self.provider.value,
                message="URI is required",
                error_code="invalid_uri",
            )
        if not username:
            return ConnectionTestResult(
                success=False,
                provider=self.provider.value,
                message="Username is required",
                error_code="invalid_credentials",
            )

        safe_uri = sanitize_uri_for_log(uri)
        timeout_s = max(0.5, timeout_ms / 1000.0)
        effective_encryption = encrypted or uri_scheme_forces_tls(uri)

        driver = None
        start = time.perf_counter()
        try:
            try:
                driver = build_driver(
                    uri,
                    username,
                    password,
                    encrypted=encrypted,
                    connection_timeout_s=timeout_s,
                )
            except ConfigurationError as exc:
                logger.info("Neo4j config error testing %s: %s", safe_uri, exc)
                return ConnectionTestResult(
                    success=False,
                    provider=self.provider.value,
                    message=f"Driver configuration error: {exc}",
                    error_code="configuration_error",
                )
            except ValueError as exc:
                return ConnectionTestResult(
                    success=False,
                    provider=self.provider.value,
                    message=str(exc),
                    error_code="invalid_uri",
                )

            # verify_connectivity does authenticated handshake with no graph mutation.
            try:
                await asyncio.wait_for(driver.verify_connectivity(), timeout=timeout_s)
            except asyncio.TimeoutError:
                latency_ms = (time.perf_counter() - start) * 1000
                return ConnectionTestResult(
                    success=False,
                    provider=self.provider.value,
                    message=f"Connection timed out after {timeout_s:.1f}s",
                    error_code="timeout",
                    latency_ms=latency_ms,
                )

            # Best-effort metadata fetch — must not fail the test if the user
            # lacks permission on system database. Uses a tiny RETURN 1 to
            # confirm session-level access against the target database too.
            server_info: dict = {}
            try:
                async with driver.session(database=database_name or None) as session:
                    result = await session.run(
                        "CALL dbms.components() YIELD name, versions, edition "
                        "RETURN name, versions, edition LIMIT 1"
                    )
                    record = await result.single()
                    if record is not None:
                        server_info = {
                            "name": record.get("name"),
                            "versions": record.get("versions"),
                            "edition": record.get("edition"),
                        }
            except Exception as exc:  # noqa: BLE001
                # Connectivity verified, metadata blocked — that's fine.
                logger.debug(
                    "Neo4j metadata probe failed for %s (non-fatal): %s",
                    safe_uri,
                    exc,
                )

            latency_ms = (time.perf_counter() - start) * 1000
            versions = server_info.get("versions") or []
            version_str = versions[0] if versions else None

            return ConnectionTestResult(
                success=True,
                provider=self.provider.value,
                message="Connection successful",
                server_version=version_str,
                edition=server_info.get("edition"),
                database_name=database_name or "neo4j",
                latency_ms=latency_ms,
                details={"encrypted": effective_encryption},
            )

        except AuthError as exc:
            logger.info("Neo4j auth failure for %s", safe_uri)
            return ConnectionTestResult(
                success=False,
                provider=self.provider.value,
                message="Authentication failed — check username and password",
                error_code="authentication_failed",
                details={"raw": str(exc)},
            )
        except ServiceUnavailable as exc:
            logger.info("Neo4j unreachable %s: %s", safe_uri, exc)
            return ConnectionTestResult(
                success=False,
                provider=self.provider.value,
                message=f"Could not reach database at {safe_uri}",
                error_code="service_unavailable",
                details={"raw": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001
            # Catch-all so test_connection never raises into the API layer.
            # Includes SSL/TLS mismatches surfaced as opaque OSError on some
            # platforms.
            logger.exception("Unexpected Neo4j test_connection error for %s", safe_uri)
            return ConnectionTestResult(
                success=False,
                provider=self.provider.value,
                message=f"Connection failed: {exc}",
                error_code="unknown_error",
                details={"raw": str(exc)},
            )
        finally:
            if driver is not None:
                try:
                    await driver.close()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Error closing Neo4j test driver: %s", exc)


__all__ = ["Neo4jGraphAdapter"]
