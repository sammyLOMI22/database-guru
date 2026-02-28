"""CQL (Cassandra Query Language) generator via LLM.

CQL is SQL-like, so this generator reuses SQL prompt patterns with
Cassandra-specific constraints (partition key, no JOIN, etc.).
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from src.nosql.base import NoSQLQueryGenerator

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a Cassandra CQL query generator. Convert natural language queries into valid CQL.

Rules:
1. CQL is SQL-like but with important constraints:
   - Always include the partition key in WHERE clause when possible
   - No JOIN operations - Cassandra denormalizes data
   - No subqueries
   - Use ALLOW FILTERING only when absolutely necessary
   - Limited GROUP BY support
2. Aggregations available: COUNT(*), SUM, AVG, MIN, MAX
3. Use proper Cassandra types (text, int, bigint, timestamp, uuid, etc.)
4. For time-series data, use range queries on clustering columns
5. Include LIMIT to prevent full table scans

Return ONLY the CQL query as a single statement (no markdown, no explanation).
"""


class CQLGenerator(NoSQLQueryGenerator):
    """Generates CQL from natural language via LLM."""

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
    ) -> str:
        """Generate CQL from natural language. Returns a CQL string."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

Generate the CQL query:"""

        response = await self.ollama.generate(
            prompt=prompt,
            model=model,
            temperature=0.1,
            db=db,
            agent_type="cql_generator",
            agent_name="CQLGenerator",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._extract_cql(response)

    async def generate_with_error_context(
        self,
        question: str,
        schema: str,
        previous_query: str,
        error_message: str,
        model: Optional[str] = None,
        db=None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> str:
        """Regenerate CQL with error context for self-correction."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

PREVIOUS ATTEMPT FAILED:
CQL: {previous_query}
Error: {error_message}

Fix the query. Return ONLY the corrected CQL:"""

        response = await self.ollama.generate(
            prompt=prompt,
            model=model,
            temperature=0.2,
            db=db,
            agent_type="cql_generator",
            agent_name="CQLGenerator.retry",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._extract_cql(response)

    def _extract_cql(self, response: str) -> str:
        """Extract CQL from LLM response, stripping markdown and explanation."""
        # Try extracting from code block
        match = re.search(r'```(?:cql|sql)?\s*([\s\S]*?)```', response)
        if match:
            return match.group(1).strip()

        # Strip any leading/trailing explanation
        lines = response.strip().split("\n")
        cql_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith("--") or stripped.startswith("//"):
                continue
            # Stop at explanation text
            if stripped.lower().startswith(("this ", "note:", "explanation:", "the ")):
                break
            cql_lines.append(line)

        cql = "\n".join(cql_lines).strip().rstrip(";") + ";"
        return cql

    def query_to_display_string(self, query: str) -> str:
        """CQL is already a display string."""
        return query
