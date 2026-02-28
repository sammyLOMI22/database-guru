"""Elasticsearch schema inspector - uses index mappings API."""
import logging
from typing import Any, Dict

from src.nosql.base import NoSQLSchemaInspector

logger = logging.getLogger(__name__)


class ElasticsearchSchemaInspector(NoSQLSchemaInspector):
    """Inspect Elasticsearch index schemas from mappings."""

    def __init__(self, client):
        self.client = client  # AsyncElasticsearch

    async def get_schema(self, connection: Any = None) -> Dict[str, Any]:
        """Get all index mappings and convert to schema format."""
        tables = {}

        # Get all indices (excluding system indices)
        indices = await self.client.cat.indices(format="json", h="index,docs.count")

        for idx_info in indices:
            index_name = idx_info.get("index", "")
            if index_name.startswith("."):
                continue  # Skip system indices

            doc_count = int(idx_info.get("docs.count", 0) or 0)

            try:
                mapping = await self.client.indices.get_mapping(index=index_name)
                properties = (
                    mapping.get(index_name, {})
                    .get("mappings", {})
                    .get("properties", {})
                )
                columns = self._flatten_properties(properties)
            except Exception as e:
                logger.warning(f"Failed to get mapping for {index_name}: {e}")
                columns = []

            tables[index_name] = {
                "columns": columns,
                "row_count": doc_count,
            }

        return {
            "tables": tables,
            "database_type": "elasticsearch",
        }

    def _flatten_properties(
        self, properties: Dict, prefix: str = ""
    ) -> list:
        """Flatten nested properties into dot-notation columns."""
        columns = []
        for field_name, field_info in properties.items():
            full_name = f"{prefix}{field_name}" if prefix else field_name
            field_type = field_info.get("type", "object")

            columns.append({
                "name": full_name,
                "type": field_type,
                "nullable": True,
            })

            # Recurse into nested/object properties (max 2 levels)
            nested_props = field_info.get("properties")
            if nested_props and prefix.count(".") < 2:
                columns.extend(
                    self._flatten_properties(nested_props, f"{full_name}.")
                )

        return columns

    def format_schema_for_llm(self, schema: Dict[str, Any]) -> str:
        """Format Elasticsearch schema for Query DSL generation prompts."""
        lines = ["DATABASE: Elasticsearch (Query DSL)", ""]

        for index_name, info in schema.get("tables", {}).items():
            doc_count = info.get("row_count", 0)
            lines.append(f"Index: {index_name} (~{doc_count} documents)")

            columns = info.get("columns", [])
            if columns:
                lines.append("  Fields:")
                for col in columns[:30]:  # Limit field list
                    lines.append(f"    - {col['name']}: {col['type']}")
            lines.append("")

        lines.append("Query DSL Notes:")
        lines.append("- Use 'query' for filtering (match, term, range, bool)")
        lines.append("- Use 'aggs' for aggregations (terms, avg, sum, min, max, date_histogram)")
        lines.append("- Use 'sort' for ordering")
        lines.append("- Use 'size' to limit results")
        lines.append("- 'text' fields use 'match', 'keyword' fields use 'term'")
        lines.append("- Return JSON: {index, query, aggs, sort, size}")

        return "\n".join(lines)
