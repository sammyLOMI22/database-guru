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

# Allowlisted Redis commands that are safe for query execution.
# Commands NOT on this list are blocked to prevent destructive operations
# (e.g. FLUSHALL, FLUSHDB, CONFIG, DEBUG, SHUTDOWN, SCRIPT, EVAL, CLUSTER).
ALLOWED_READ_COMMANDS = frozenset({
    # String
    "GET", "MGET", "STRLEN", "GETRANGE",
    # Hash
    "HGET", "HGETALL", "HMGET", "HKEYS", "HVALS", "HLEN", "HEXISTS", "HSCAN",
    # List
    "LRANGE", "LLEN", "LINDEX", "LPOS",
    # Set
    "SMEMBERS", "SCARD", "SISMEMBER", "SRANDMEMBER", "SSCAN", "SUNION", "SINTER", "SDIFF",
    # Sorted Set
    "ZRANGE", "ZRANGEBYSCORE", "ZRANGEBYLEX", "ZREVRANGE", "ZREVRANGEBYSCORE",
    "ZCARD", "ZCOUNT", "ZSCORE", "ZRANK", "ZREVRANK", "ZSCAN",
    # Key inspection
    "EXISTS", "TYPE", "TTL", "PTTL", "KEYS", "SCAN", "DBSIZE", "RANDOMKEY",
    "OBJECT", "DUMP",
    # Stream (read)
    "XRANGE", "XREVRANGE", "XLEN", "XINFO", "XREAD",
    # Server info (read-only)
    "INFO", "PING", "ECHO", "TIME",
})

ALLOWED_WRITE_COMMANDS = frozenset({
    # String
    "SET", "MSET", "SETNX", "SETEX", "PSETEX", "INCR", "INCRBY", "INCRBYFLOAT",
    "DECR", "DECRBY", "APPEND", "SETRANGE",
    # Hash
    "HSET", "HMSET", "HSETNX", "HINCRBY", "HINCRBYFLOAT", "HDEL",
    # List
    "LPUSH", "RPUSH", "LPOP", "RPOP", "LSET", "LINSERT", "LTRIM", "LREM",
    # Set
    "SADD", "SREM", "SPOP", "SMOVE",
    # Sorted Set
    "ZADD", "ZREM", "ZINCRBY", "ZPOPMIN", "ZPOPMAX",
    # Key lifecycle
    "DEL", "UNLINK", "EXPIRE", "PEXPIRE", "EXPIREAT", "PEXPIREAT", "PERSIST", "RENAME",
    # Stream (write)
    "XADD", "XDEL", "XTRIM",
})

ALL_ALLOWED_COMMANDS = ALLOWED_READ_COMMANDS | ALLOWED_WRITE_COMMANDS


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
        if not command.command:
            return normalize_nosql_result(
                data=[], execution_time_ms=0, error="No command specified"
            )

        cmd_upper = command.command.upper()

        # Block commands not on the allowlist (e.g. FLUSHALL, CONFIG, SHUTDOWN, EVAL)
        if cmd_upper not in ALL_ALLOWED_COMMANDS:
            return normalize_nosql_result(
                data=[],
                execution_time_ms=0,
                error=f"Command '{cmd_upper}' is not allowed. Only safe read/write commands are permitted.",
            )

        # Block write commands unless explicitly allowed
        if (command.is_write or cmd_upper in ALLOWED_WRITE_COMMANDS) and not self.allow_write:
            return normalize_nosql_result(
                data=[],
                execution_time_ms=0,
                error=f"Write command '{cmd_upper}' not allowed. Enable allow_write.",
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
