"""Redis command executor - runs RedisCommand objects against redis-py client.

Handles all Redis data types and normalizes results for the standard contract.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from src.nosql.redis.command_generator import RedisCommand
from src.nosql.result_formatter import normalize_nosql_result

logger = logging.getLogger(__name__)


class RedisQueryExecutor:
    """Execute Redis commands safely with timeout."""

    def __init__(
        self,
        client: aioredis.Redis,
        max_results: int = 1000,
        timeout_seconds: int = 30,
        allow_write: bool = False,
    ):
        self.client = client
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self.allow_write = allow_write

    async def execute(self, command: RedisCommand) -> Dict[str, Any]:
        """Execute a RedisCommand and return a normalized result dict."""
        if command.is_write and not self.allow_write:
            return normalize_nosql_result(
                data=[],
                execution_time_ms=0,
                error=f"Write command '{command.command}' not allowed. Enable allow_write.",
            )

        if not command.command:
            return normalize_nosql_result(
                data=[], execution_time_ms=0, error="No command specified"
            )

        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._execute_command(command),
                timeout=self.timeout_seconds,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=result,
                execution_time_ms=elapsed_ms,
                max_rows=self.max_results,
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            return normalize_nosql_result(
                data=[],
                execution_time_ms=elapsed_ms,
                error=f"Command timed out after {self.timeout_seconds}s",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Redis command error: {e}", exc_info=True)
            return normalize_nosql_result(
                data=[], execution_time_ms=elapsed_ms, error=str(e)
            )

    async def _execute_command(self, command: RedisCommand) -> List[Dict]:
        """Execute the Redis command and format results as list of dicts."""
        cmd = command.command.upper()
        args = command.args

        # Execute the raw command
        result = await self.client.execute_command(cmd, *args)

        # Format result into list of dicts for normalize_nosql_result
        return self._format_result(cmd, args, result)

    def _format_result(
        self, cmd: str, args: List[str], result: Any
    ) -> List[Dict]:
        """Convert Redis response to list-of-dicts format."""
        key = args[0] if args else ""

        # Hash results (HGETALL returns dict)
        if isinstance(result, dict):
            return [{"key": key, "field": k, "value": v} for k, v in result.items()]

        # List/set results
        if isinstance(result, (list, tuple, set)):
            rows = []
            for i, item in enumerate(result):
                if isinstance(item, dict):
                    rows.append(item)
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    # Sorted set with scores: [(member, score), ...]
                    rows.append({"member": item[0], "score": item[1]})
                else:
                    rows.append({"key": key, "index": i, "value": item})
            return rows

        # Scalar results (GET, INCR, etc.)
        if result is None:
            return [{"key": key, "value": None}]

        return [{"key": key, "value": result}]
