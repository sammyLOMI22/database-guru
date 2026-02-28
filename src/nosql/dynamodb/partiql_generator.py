"""DynamoDB PartiQL generator via LLM.

PartiQL provides SQL-like syntax for DynamoDB queries.
"""
import logging
import re
from typing import Any, Dict, Optional

from src.nosql.base import NoSQLQueryGenerator

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a DynamoDB PartiQL query generator. Convert natural language queries into valid PartiQL.

Rules:
1. PartiQL is SQL-like but for DynamoDB
2. Table names MUST be double-quoted: SELECT * FROM "MyTable"
3. Always include the partition key in WHERE clause when possible
4. No JOIN, no subqueries
5. DynamoDB attribute names are case-sensitive
6. Use single quotes for string values
7. Supported: SELECT, INSERT, UPDATE, DELETE
8. Use EXISTS() to check for attribute existence
9. Include LIMIT to prevent full table scans

Return ONLY the PartiQL statement (no markdown, no explanation).
"""


class PartiQLGenerator(NoSQLQueryGenerator):
    """Generates DynamoDB PartiQL from natural language via LLM."""

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
        """Generate PartiQL from natural language."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

Generate the PartiQL query:"""

        response = await self.ollama.generate(
            prompt=prompt, model=model, temperature=0.1,
            db=db, agent_type="partiql_generator",
            agent_name="PartiQLGenerator",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._extract_partiql(response)

    async def generate_with_error_context(
        self, question, schema, previous_query, error_message,
        model=None, db=None, query_history_id=None, chat_session_id=None,
    ) -> str:
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

PREVIOUS ATTEMPT FAILED:
PartiQL: {previous_query}
Error: {error_message}

Fix the query. Return ONLY the corrected PartiQL:"""

        response = await self.ollama.generate(
            prompt=prompt, model=model, temperature=0.2,
            db=db, agent_type="partiql_generator",
            agent_name="PartiQLGenerator.retry",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._extract_partiql(response)

    def _extract_partiql(self, response: str) -> str:
        match = re.search(r'```(?:sql|partiql)?\s*([\s\S]*?)```', response)
        if match:
            return match.group(1).strip()

        lines = response.strip().split("\n")
        query_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            if stripped.lower().startswith(("this ", "note:", "explanation:")):
                break
            query_lines.append(line)

        return "\n".join(query_lines).strip()

    def query_to_display_string(self, query: str) -> str:
        return query
