"""Abstract base classes for NoSQL database support.

Each NoSQL database implements these interfaces to provide:
- Schema introspection (document sampling, key analysis, mapping inspection)
- Query generation (NL -> native query language via LLM)
- Query execution (run generated queries safely)
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NoSQLSchemaInspector(ABC):
    """Base class for NoSQL schema introspection.

    Implementations produce dicts compatible with DatabaseConnection.schema_cache JSON.
    """

    @abstractmethod
    async def get_schema(self, connection: Any) -> Dict[str, Any]:
        """Inspect the NoSQL database and return schema information.

        Returns:
            Dict with structure compatible with SchemaCache format:
            {
                "tables": {
                    "collection_or_index_name": {
                        "columns": [{"name": str, "type": str, "nullable": bool}],
                        "row_count": int (estimated),
                    }
                },
                "database_type": str,
            }
        """
        ...

    @abstractmethod
    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Convert schema dict to a string suitable for LLM prompts.

        Returns:
            Human-readable schema description for the query generation prompt.
        """
        ...


class NoSQLQueryGenerator(ABC):
    """Base class for NoSQL query generation via LLM."""

    @abstractmethod
    async def generate(
        self,
        question: str,
        schema: str,
        model: Optional[str] = None,
    ) -> Any:
        """Generate a native query from natural language.

        Args:
            question: Natural language question
            schema: Schema string from format_schema_for_llm()
            model: Optional LLM model override

        Returns:
            Type-specific query object (MQLQuery, RedisCommand, etc.)
        """
        ...

    @abstractmethod
    def query_to_display_string(self, query: Any) -> str:
        """Convert the generated query to a human-readable string.

        This string is stored in QueryHistory.generated_sql and shown in the UI.
        """
        ...


class NoSQLHandler(ABC):
    """Base handler that orchestrates schema → generation → execution → retry.

    Each NoSQL database implements this to provide the full query flow.
    The handle() method returns a dict matching the shape of
    SelfCorrectingSQLAgent.generate_and_execute_with_retry().
    """

    @abstractmethod
    async def handle(
        self,
        question: str,
        connection: Any,
        model: Optional[str] = None,
        allow_write: bool = False,
        row_limit: int = 1000,
        db: Optional[Any] = None,
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a natural language query against a NoSQL database.

        Returns:
            Dict matching generate_and_execute_with_retry() contract:
            {
                "success": bool,
                "sql": str,  # display string of the native query
                "result": {
                    "success": bool,
                    "data": List[Dict],
                    "columns": List[str],
                    "row_count": int,
                    "execution_time_ms": float,
                    "truncated": bool,
                    "error": Optional[str],
                },
                "attempts": List,
                "self_corrected": bool,
                "total_attempts": int,
                "error": Optional[str],
                "agent_trace": Dict,
                "model_used": str,
            }
        """
        ...
