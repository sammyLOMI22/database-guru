"""Redis schema inspector - analyzes key patterns and data types.

Redis has no formal schema. This inspector samples keys using SCAN,
groups them by pattern, and detects their data types.
"""
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from src.nosql.base import NoSQLSchemaInspector

logger = logging.getLogger(__name__)

MAX_SCAN_KEYS = 1000


class RedisSchemaInspector(NoSQLSchemaInspector):
    """Analyze Redis key patterns and data types by scanning."""

    def __init__(self, client: aioredis.Redis, max_keys: int = MAX_SCAN_KEYS):
        self.client = client
        self.max_keys = max_keys

    async def get_schema(self, connection: Any = None) -> Dict[str, Any]:
        """Scan keys, group by pattern, detect types.

        Returns dict compatible with SchemaCache format, where "tables" maps
        key patterns to their detected type and example keys.
        """
        # Scan up to max_keys keys
        keys = []
        cursor = 0
        while len(keys) < self.max_keys:
            cursor, batch = await self.client.scan(cursor=cursor, count=200)
            keys.extend(batch)
            if cursor == 0:
                break

        keys = keys[: self.max_keys]

        if not keys:
            return {"tables": {}, "database_type": "redis"}

        # Get types for all keys (pipeline for efficiency)
        pipe = self.client.pipeline()
        for key in keys:
            pipe.type(key)
        types = await pipe.execute()

        # Group keys by pattern
        pattern_groups: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"type": set(), "count": 0, "examples": []}
        )

        for key, key_type in zip(keys, types):
            pattern = self._extract_pattern(key)
            group = pattern_groups[pattern]
            group["type"].add(key_type)
            group["count"] += 1
            if len(group["examples"]) < 3:
                group["examples"].append(key)

        # Convert to schema format
        tables = {}
        for pattern, info in sorted(pattern_groups.items()):
            type_str = ", ".join(sorted(info["type"]))
            tables[pattern] = {
                "columns": [
                    {"name": "key", "type": "string", "nullable": False},
                    {"name": "value", "type": type_str, "nullable": False},
                ],
                "row_count": info["count"],
                "examples": info["examples"],
                "redis_type": type_str,
            }

        # Get total DB size
        db_size = await self.client.dbsize()

        return {
            "tables": tables,
            "database_type": "redis",
            "total_keys": db_size,
            "sampled_keys": len(keys),
        }

    def _extract_pattern(self, key: str) -> str:
        """Extract a key pattern by replacing numeric/UUID segments with wildcards.

        Examples:
            "user:123:profile" -> "user:*:profile"
            "session:abc-def-ghi" -> "session:*"
            "orders" -> "orders"
        """
        parts = key.split(":")
        normalized = []
        for part in parts:
            if re.match(r"^\d+$", part):
                normalized.append("*")
            elif re.match(r"^[0-9a-f-]{8,}$", part, re.IGNORECASE):
                normalized.append("*")
            else:
                normalized.append(part)
        return ":".join(normalized)

    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Format Redis key patterns for LLM prompt."""
        lines = [
            "DATABASE: Redis",
            f"Total keys: {schema.get('total_keys', 'unknown')}",
            "",
        ]

        tables = schema.get("tables", {})
        for pattern, info in tables.items():
            redis_type = info.get("redis_type", "unknown")
            count = info.get("row_count", 0)
            examples = info.get("examples", [])

            lines.append(f"Key Pattern: {pattern} (type: {redis_type}, ~{count} keys)")
            if examples:
                lines.append(f"  Examples: {', '.join(examples[:3])}")
            lines.append("")

        lines.append("Available Redis commands:")
        lines.append("  Strings: GET, SET, MGET, INCR, DECR")
        lines.append("  Hashes: HGETALL, HGET, HSET, HMGET, HDEL")
        lines.append("  Lists: LRANGE, LPUSH, RPUSH, LLEN, LPOP")
        lines.append("  Sets: SMEMBERS, SADD, SREM, SINTER, SUNION, SCARD")
        lines.append("  Sorted Sets: ZRANGE, ZRANGEBYSCORE, ZADD, ZREM, ZCARD, ZREVRANGE")
        lines.append("  General: SCAN, TYPE, TTL, DEL, EXISTS")

        return "\n".join(lines)
