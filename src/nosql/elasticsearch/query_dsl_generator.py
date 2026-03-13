"""Elasticsearch Query DSL generator via LLM."""
import json
import logging
import re
from typing import Any, Dict, Optional

from src.nosql.base import NoSQLQueryGenerator

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an Elasticsearch Query DSL generator. Convert natural language into Elasticsearch queries.

Rules:
1. Return a valid JSON object with these keys:
   - "index": the index name to search
   - "query": the query clause (match, term, range, bool, etc.)
   - "aggs": aggregations (optional)
   - "sort": sort order (optional)
   - "size": max results (optional, default 100)
2. Use "match" for full-text search on text fields
3. Use "term" for exact matches on keyword fields
4. Use "range" for numeric/date ranges
5. Use "bool" with "must", "should", "must_not" for complex queries
6. For aggregations, use "terms", "avg", "sum", "min", "max", "date_histogram"
7. Set "size": 0 when only aggregation results are needed

Return ONLY valid JSON:
{
    "index": "index_name",
    "query": { ... },
    "aggs": { ... } or null,
    "sort": [ ... ] or null,
    "size": number
}"""


class QueryDSLGenerator(NoSQLQueryGenerator):
    """Generates Elasticsearch Query DSL from natural language via LLM."""

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
    ) -> Dict[str, Any]:
        """Generate Query DSL from natural language. Returns a dict."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

Generate the Elasticsearch query as JSON:"""

        response = await self.ollama.generate(
            prompt=prompt, model=model, temperature=0.1,
            db=db, agent_type="query_dsl_generator",
            agent_name="QueryDSLGenerator",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._parse_response(response)

    async def generate_with_error_context(
        self, question, schema, previous_query, error_message,
        model=None, db=None, query_history_id=None, chat_session_id=None,
    ) -> Dict[str, Any]:
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

PREVIOUS ATTEMPT FAILED:
Query: {previous_query}
Error: {error_message}

Fix the query. Return ONLY valid JSON:"""

        response = await self.ollama.generate(
            prompt=prompt, model=model, temperature=0.2,
            db=db, agent_type="query_dsl_generator",
            agent_name="QueryDSLGenerator.retry",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass

            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    raise ValueError(f"Could not parse Query DSL: {response[:200]}")

            raise ValueError(f"No JSON found in response: {response[:200]}")

    def query_to_display_string(self, query: Dict[str, Any]) -> str:
        """Convert Query DSL dict to a readable string."""
        index = query.get("index", "unknown")
        body = {k: v for k, v in query.items() if k != "index" and v is not None}
        return f"GET /{index}/_search\n{json.dumps(body, indent=2)}"
