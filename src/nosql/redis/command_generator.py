"""Redis command generator via LLM.

Converts natural language questions into structured Redis commands.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.nosql.base import NoSQLQueryGenerator

logger = logging.getLogger(__name__)


class RedisDataType(str, Enum):
    STRING = "string"
    HASH = "hash"
    LIST = "list"
    SET = "set"
    ZSET = "zset"
    STREAM = "stream"
    JSON = "json"
    UNKNOWN = "unknown"


@dataclass
class RedisCommand:
    """Represents a Redis command to execute."""
    command: str
    args: List[str] = field(default_factory=list)
    data_type: RedisDataType = RedisDataType.UNKNOWN
    is_write: bool = False

    def to_string(self) -> str:
        """Convert to Redis command string."""
        parts = [self.command] + self.args
        return " ".join(parts)


SYSTEM_PROMPT = """You are a Redis command generator. Convert natural language queries into Redis commands.

Rules:
1. Identify the data type (string, hash, list, set, sorted set, stream)
2. Use appropriate commands for the data type
3. Handle key patterns (user:*, order:*, etc.)
4. For read operations, use GET, HGETALL, LRANGE, SMEMBERS, ZRANGE, etc.
5. Mark write operations (SET, DEL, LPUSH, etc.) with is_write: true
6. For pattern-based queries, use SCAN with MATCH patterns
7. Return ONLY one command at a time

Return ONLY valid JSON:
{
    "command": "COMMAND_NAME",
    "args": ["arg1", "arg2", ...],
    "data_type": "string|hash|list|set|zset|stream",
    "is_write": false,
    "explanation": "What this command does"
}"""


class RedisCommandGenerator(NoSQLQueryGenerator):
    """Generates Redis commands from natural language via LLM."""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    async def generate(
        self,
        question: str,
        schema: str,
        model: Optional[str] = None,
        db=None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> RedisCommand:
        """Generate a Redis command from natural language."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

Generate the Redis command as JSON:"""

        response = await self.ollama.generate(
            prompt=prompt,
            model=model,
            temperature=0.1,
            db=db,
            agent_type="redis_command_generator",
            agent_name="RedisCommandGenerator",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._parse_response(response)

    async def generate_with_error_context(
        self,
        question: str,
        schema: str,
        previous_command: str,
        error_message: str,
        model: Optional[str] = None,
        db=None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> RedisCommand:
        """Regenerate command with error context for self-correction."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

PREVIOUS ATTEMPT FAILED:
Command: {previous_command}
Error: {error_message}

Fix the command and try again. Return ONLY valid JSON:"""

        response = await self.ollama.generate(
            prompt=prompt,
            model=model,
            temperature=0.2,
            db=db,
            agent_type="redis_command_generator",
            agent_name="RedisCommandGenerator.retry",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> RedisCommand:
        """Parse LLM response into RedisCommand."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if match:
                try:
                    data = json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass
                else:
                    return self._dict_to_command(data)

            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    raise ValueError(f"Could not parse Redis response: {response[:200]}")
            else:
                raise ValueError(f"No JSON found in Redis response: {response[:200]}")

        return self._dict_to_command(data)

    def _dict_to_command(self, data: Dict) -> RedisCommand:
        """Convert parsed dict to RedisCommand."""
        try:
            data_type = RedisDataType(data.get("data_type", "unknown"))
        except ValueError:
            data_type = RedisDataType.UNKNOWN

        args = data.get("args", [])
        # Ensure all args are strings
        args = [str(a) for a in args]

        return RedisCommand(
            command=data.get("command", "").upper(),
            args=args,
            data_type=data_type,
            is_write=data.get("is_write", False),
        )

    def query_to_display_string(self, query: RedisCommand) -> str:
        """Convert RedisCommand to display string."""
        return query.to_string()
