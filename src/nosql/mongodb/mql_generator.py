"""MQL (MongoDB Query Language) generator via LLM.

Converts natural language questions into structured MQLQuery objects
that the executor can run against MongoDB.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.nosql.base import NoSQLQueryGenerator

logger = logging.getLogger(__name__)


class MQLOperationType(str, Enum):
    FIND = "find"
    FIND_ONE = "findOne"
    AGGREGATE = "aggregate"
    COUNT = "count"
    DISTINCT = "distinct"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class MQLQuery:
    """Represents a generated MongoDB query."""
    operation: MQLOperationType
    collection: str
    query: Dict[str, Any] = field(default_factory=dict)
    projection: Optional[Dict] = None
    pipeline: Optional[List[Dict]] = None
    sort: Optional[Dict] = None
    limit: Optional[int] = None
    skip: Optional[int] = None
    update: Optional[Dict] = None

    @property
    def is_write(self) -> bool:
        return self.operation in (
            MQLOperationType.INSERT,
            MQLOperationType.UPDATE,
            MQLOperationType.DELETE,
        )


SYSTEM_PROMPT = """You are a MongoDB query generator. Convert natural language queries into MongoDB Query Language (MQL).

Rules:
1. Use proper MongoDB operators ($eq, $gt, $gte, $lt, $lte, $in, $nin, $regex, $exists, etc.)
2. For complex queries involving grouping, sorting with aggregation, or joins, use aggregation pipelines
3. Handle date comparisons with ISODate strings
4. Use proper projection to limit returned fields when appropriate
5. Include sort, limit, skip when the query implies ordering or pagination
6. For simple lookups, prefer find over aggregate

Return ONLY valid JSON in this exact format:
{
    "operation": "find|findOne|aggregate|count|distinct",
    "collection": "collection_name",
    "query": { ... },
    "projection": { ... } or null,
    "pipeline": [ ... ] or null,
    "sort": { ... } or null,
    "limit": number or null,
    "explanation": "Brief explanation of the query"
}"""


class MQLGenerator(NoSQLQueryGenerator):
    """Generates MongoDB Query Language from natural language via LLM."""

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
    ) -> MQLQuery:
        """Generate MQL from natural language."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

Generate the MongoDB query as JSON:"""

        response = await self.ollama.generate(
            prompt=prompt,
            model=model,
            temperature=0.1,
            db=db,
            agent_type="mql_generator",
            agent_name="MQLGenerator",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._parse_response(response)

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
    ) -> MQLQuery:
        """Regenerate MQL with error context for self-correction."""
        prompt = f"""{SYSTEM_PROMPT}

{schema}

User Query: {question}

PREVIOUS ATTEMPT FAILED:
Query: {previous_query}
Error: {error_message}

Fix the query and try again. Return ONLY valid JSON:"""

        response = await self.ollama.generate(
            prompt=prompt,
            model=model,
            temperature=0.2,
            db=db,
            agent_type="mql_generator",
            agent_name="MQLGenerator.retry",
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
        )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> MQLQuery:
        """Parse LLM response into MQLQuery."""
        # Try direct JSON parse
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks or surrounding text
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if match:
                try:
                    data = json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass
                else:
                    return self._dict_to_mql(data)

            # Try finding a JSON object in the response
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    raise ValueError(f"Could not parse MQL response: {response[:200]}")
            else:
                raise ValueError(f"No JSON found in MQL response: {response[:200]}")

        return self._dict_to_mql(data)

    def _dict_to_mql(self, data: Dict) -> MQLQuery:
        """Convert parsed dict to MQLQuery dataclass."""
        operation_str = data.get("operation", "find")
        try:
            operation = MQLOperationType(operation_str)
        except ValueError:
            operation = MQLOperationType.FIND

        return MQLQuery(
            operation=operation,
            collection=data.get("collection", ""),
            query=data.get("query", {}),
            projection=data.get("projection"),
            pipeline=data.get("pipeline"),
            sort=data.get("sort"),
            limit=data.get("limit"),
            skip=data.get("skip"),
            update=data.get("update"),
        )

    def query_to_display_string(self, query: MQLQuery) -> str:
        """Convert MQLQuery to a human-readable MongoDB shell-style string."""
        coll = query.collection

        if query.operation == MQLOperationType.AGGREGATE:
            pipeline = json.dumps(query.pipeline or [], indent=2)
            return f"db.{coll}.aggregate({pipeline})"

        if query.operation == MQLOperationType.COUNT:
            filter_str = json.dumps(query.query) if query.query else ""
            return f"db.{coll}.countDocuments({filter_str})"

        if query.operation == MQLOperationType.DISTINCT:
            field = "unknown"
            if query.projection and "field" in query.projection:
                field = query.projection["field"]
            filter_str = json.dumps(query.query) if query.query else "{}"
            return f'db.{coll}.distinct("{field}", {filter_str})'

        if query.operation == MQLOperationType.FIND_ONE:
            parts = [json.dumps(query.query)]
            if query.projection:
                parts.append(json.dumps(query.projection))
            return f"db.{coll}.findOne({', '.join(parts)})"

        # Default: find
        parts = [f"db.{coll}.find({json.dumps(query.query)}"]
        if query.projection:
            parts[0] += f", {json.dumps(query.projection)}"
        parts[0] += ")"

        if query.sort:
            parts.append(f".sort({json.dumps(query.sort)})")
        if query.skip:
            parts.append(f".skip({query.skip})")
        if query.limit:
            parts.append(f".limit({query.limit})")

        return "".join(parts)
