"""Dynamic Few-Shot Example Generator - Schema-specific SQL examples.

This module generates few-shot examples using ACTUAL table and column names
from the schema, instead of hardcoded examples that may confuse the LLM.

Key Features:
- Generates examples from actual schema tables/columns
- Intent-aware examples (different for aggregation vs lookup)
- Includes sample values for filter examples
- Relationship-aware JOIN examples

Usage:
    generator = DynamicExampleGenerator(schema_dict)
    examples = generator.generate_examples(intent=QueryIntent.LOOKUP)
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Import QueryIntent if available, else define locally
try:
    from src.llm.query_intent_classifier import QueryIntent
except ImportError:
    from enum import Enum
    class QueryIntent(Enum):
        LOOKUP = "lookup"
        AGGREGATION = "aggregation"
        COMPARISON = "comparison"
        RELATIONSHIP = "relationship"
        TEMPORAL = "temporal"
        RANKING = "ranking"
        IMPOSSIBLE = "impossible"


@dataclass
class SQLExample:
    """A single SQL example for few-shot learning.

    Attributes:
        question: Natural language question
        sql: The corresponding SQL query
        note: Optional explanatory note
        intent: The type of query this demonstrates
    """
    question: str
    sql: str
    note: Optional[str] = None
    intent: Optional[QueryIntent] = None


class DynamicExampleGenerator:
    """Generates schema-specific SQL examples for few-shot learning.

    Instead of using hardcoded examples with table names like "users" or "products"
    that may not exist in the actual schema, this generator creates examples
    using the real table and column names from the provided schema.
    """

    # Maximum examples per category
    MAX_TABLE_EXAMPLES = 2
    MAX_RELATIONSHIP_EXAMPLES = 2
    MAX_AGGREGATION_EXAMPLES = 2
    MAX_FILTER_EXAMPLES = 2

    def __init__(self, schema_dict: Dict[str, Any]):
        """Initialize with schema.

        Args:
            schema_dict: Parsed schema dictionary from SchemaInspector
        """
        self.schema = schema_dict
        self.tables = list(schema_dict.get("tables", {}).keys())
        self.relationships = schema_dict.get("relationships", [])
        self.foreign_keys = self._extract_foreign_keys()

    def _extract_foreign_keys(self) -> List[Dict[str, str]]:
        """Extract foreign key relationships from schema."""
        fks = []
        for table_name, table_info in self.schema.get("tables", {}).items():
            for fk in table_info.get("foreign_keys", []):
                fks.append({
                    "from_table": table_name,
                    "from_column": fk.get("column") or fk.get("from_column"),
                    "to_table": fk.get("references", {}).get("table") or fk.get("to_table"),
                    "to_column": fk.get("references", {}).get("column") or fk.get("to_column", "id")
                })
        return fks

    def generate_examples(
        self,
        intent: Optional[QueryIntent] = None,
        row_limit: int = 10
    ) -> str:
        """Generate schema-specific examples.

        Args:
            intent: Optional query intent to prioritize relevant examples
            row_limit: Default LIMIT clause value

        Returns:
            Formatted string of examples for inclusion in prompt
        """
        examples = []

        # Always include basic table examples
        examples.extend(self._generate_table_examples(row_limit))

        # Add relationship examples if we have FKs
        if self.foreign_keys:
            examples.extend(self._generate_relationship_examples(row_limit))

        # Add aggregation examples
        examples.extend(self._generate_aggregation_examples())

        # Add filter examples with sample values
        examples.extend(self._generate_filter_examples(row_limit))

        # If intent specified, prioritize those examples
        if intent:
            examples = self._prioritize_by_intent(examples, intent)

        return self._format_examples(examples)

    def _generate_table_examples(self, row_limit: int) -> List[SQLExample]:
        """Generate simple lookup examples for tables."""
        examples = []

        for table in self.tables[:self.MAX_TABLE_EXAMPLES]:
            # Basic select all
            examples.append(SQLExample(
                question=f"Show all {table}",
                sql=f"SELECT * FROM {table} LIMIT {row_limit}",
                intent=QueryIntent.LOOKUP
            ))

            # If table has notable columns, show selective query
            columns = self._get_table_columns(table)
            if len(columns) > 3:
                # Pick first 3 non-id columns
                display_cols = [c for c in columns if 'id' not in c.lower()][:3]
                if display_cols:
                    cols_str = ", ".join(display_cols)
                    examples.append(SQLExample(
                        question=f"List {table} with their {', '.join(display_cols[:2])}",
                        sql=f"SELECT {cols_str} FROM {table} LIMIT {row_limit}",
                        intent=QueryIntent.LOOKUP
                    ))

        return examples

    def _generate_relationship_examples(self, row_limit: int) -> List[SQLExample]:
        """Generate JOIN examples using actual foreign keys."""
        examples = []

        for fk in self.foreign_keys[:self.MAX_RELATIONSHIP_EXAMPLES]:
            from_table = fk["from_table"]
            to_table = fk["to_table"]
            from_col = fk["from_column"]
            to_col = fk["to_column"]

            if not all([from_table, to_table, from_col, to_col]):
                continue

            examples.append(SQLExample(
                question=f"Show {from_table} with their {to_table}",
                sql=(f"SELECT * FROM {from_table} "
                     f"JOIN {to_table} ON {from_table}.{from_col} = {to_table}.{to_col} "
                     f"LIMIT {row_limit}"),
                intent=QueryIntent.RELATIONSHIP
            ))

        return examples

    def _generate_aggregation_examples(self) -> List[SQLExample]:
        """Generate COUNT, SUM, AVG examples."""
        examples = []

        if not self.tables:
            return examples

        # COUNT example
        table = self.tables[0]
        examples.append(SQLExample(
            question=f"How many {table} are there?",
            sql=f"SELECT COUNT(*) FROM {table}",
            intent=QueryIntent.AGGREGATION
        ))

        # GROUP BY example if we have suitable columns
        for table in self.tables[:2]:
            group_col = self._find_groupable_column(table)
            if group_col:
                examples.append(SQLExample(
                    question=f"Count {table} by {group_col}",
                    sql=f"SELECT {group_col}, COUNT(*) as count FROM {table} GROUP BY {group_col}",
                    intent=QueryIntent.AGGREGATION
                ))
                break

        # SUM/AVG if we have numeric columns
        for table in self.tables[:2]:
            numeric_col = self._find_numeric_column(table)
            group_col = self._find_groupable_column(table)
            if numeric_col and group_col:
                examples.append(SQLExample(
                    question=f"Total {numeric_col} by {group_col}",
                    sql=f"SELECT {group_col}, SUM({numeric_col}) as total FROM {table} GROUP BY {group_col}",
                    intent=QueryIntent.AGGREGATION
                ))
                break

        return examples[:self.MAX_AGGREGATION_EXAMPLES]

    def _generate_filter_examples(self, row_limit: int) -> List[SQLExample]:
        """Generate WHERE clause examples using sample values."""
        examples = []

        for table in self.tables[:2]:
            # Look for columns with sample values
            columns_info = self._get_columns_info(table)

            for col_info in columns_info:
                col_name = col_info.get("name", "")
                samples = col_info.get("sample_values", [])

                # Status/type/category columns are great for examples
                if any(kw in col_name.lower() for kw in ['status', 'type', 'category', 'state']):
                    if samples:
                        value = samples[0]
                        examples.append(SQLExample(
                            question=f"{table} where {col_name} is '{value}'",
                            sql=f"SELECT * FROM {table} WHERE {col_name} = '{value}' LIMIT {row_limit}",
                            note=f"Note: {col_name} values include: {', '.join(str(s) for s in samples[:5])}",
                            intent=QueryIntent.COMPARISON
                        ))

                        if len(examples) >= self.MAX_FILTER_EXAMPLES:
                            return examples

        # Add a numeric comparison example if no status columns found
        if len(examples) < self.MAX_FILTER_EXAMPLES:
            for table in self.tables[:2]:
                numeric_col = self._find_numeric_column(table)
                if numeric_col:
                    examples.append(SQLExample(
                        question=f"{table} with {numeric_col} greater than 100",
                        sql=f"SELECT * FROM {table} WHERE {numeric_col} > 100 LIMIT {row_limit}",
                        intent=QueryIntent.COMPARISON
                    ))
                    break

        return examples

    def _prioritize_by_intent(
        self,
        examples: List[SQLExample],
        intent: QueryIntent
    ) -> List[SQLExample]:
        """Reorder examples to prioritize those matching the intent."""
        matching = [e for e in examples if e.intent == intent]
        others = [e for e in examples if e.intent != intent]

        # Put matching examples first, then others
        return matching + others

    def _format_examples(self, examples: List[SQLExample]) -> str:
        """Format examples as a string for inclusion in prompts."""
        if not examples:
            return ""

        lines = [
            "--- Examples using YOUR schema tables ---",
            "(Use these as patterns - they reference actual tables in your database)",
            ""
        ]

        for i, ex in enumerate(examples, 1):
            lines.append(f"Example {i}:")
            lines.append(f"Question: {ex.question}")
            lines.append(f"SQL: {ex.sql}")
            if ex.note:
                lines.append(f"// {ex.note}")
            lines.append("")

        lines.append("--- End of examples ---")
        return "\n".join(lines)

    def _get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        table_info = self.schema.get("tables", {}).get(table_name, {})
        return [col["name"] for col in table_info.get("columns", [])]

    def _get_columns_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get full column info for a table."""
        table_info = self.schema.get("tables", {}).get(table_name, {})
        return table_info.get("columns", [])

    def _find_groupable_column(self, table_name: str) -> Optional[str]:
        """Find a column suitable for GROUP BY (categorical).

        Prefers: status, type, category, state columns
        """
        columns = self._get_columns_info(table_name)
        preferred = ['status', 'type', 'category', 'state', 'country', 'region']

        for col in columns:
            col_name = col.get("name", "").lower()
            if any(kw in col_name for kw in preferred):
                return col["name"]

        # Fallback to first non-id, non-numeric column
        for col in columns:
            col_name = col.get("name", "")
            col_type = col.get("type", "").upper()
            if ('id' not in col_name.lower() and
                not any(t in col_type for t in ['INT', 'FLOAT', 'DECIMAL', 'NUMERIC', 'REAL'])):
                return col_name

        return None

    def _find_numeric_column(self, table_name: str) -> Optional[str]:
        """Find a numeric column suitable for SUM/AVG.

        Prefers: price, total, amount, quantity, count columns
        """
        columns = self._get_columns_info(table_name)
        preferred = ['price', 'total', 'amount', 'quantity', 'count', 'cost', 'value', 'revenue']
        numeric_types = ['INT', 'FLOAT', 'DECIMAL', 'NUMERIC', 'REAL', 'DOUBLE', 'MONEY']

        # First try preferred names
        for col in columns:
            col_name = col.get("name", "").lower()
            col_type = col.get("type", "").upper()
            if (any(kw in col_name for kw in preferred) and
                any(t in col_type for t in numeric_types)):
                return col["name"]

        # Fallback to any numeric column that's not an ID
        for col in columns:
            col_name = col.get("name", "").lower()
            col_type = col.get("type", "").upper()
            if (any(t in col_type for t in numeric_types) and
                'id' not in col_name):
                return col["name"]

        return None

    def get_intent_specific_examples(
        self,
        intent: QueryIntent,
        row_limit: int = 10
    ) -> str:
        """Get examples specifically for a query intent.

        This is useful when you already know the query intent and want
        highly relevant examples only.
        """
        examples = []

        if intent == QueryIntent.LOOKUP:
            examples = self._generate_table_examples(row_limit)

        elif intent == QueryIntent.AGGREGATION:
            examples = self._generate_aggregation_examples()

        elif intent == QueryIntent.COMPARISON:
            examples = self._generate_filter_examples(row_limit)

        elif intent == QueryIntent.RELATIONSHIP:
            examples = self._generate_relationship_examples(row_limit)
            if not examples:
                # No FKs, fall back to table examples
                examples = self._generate_table_examples(row_limit)

        elif intent == QueryIntent.RANKING:
            # Ranking is similar to lookup with ORDER BY
            examples = self._generate_ranking_examples(row_limit)

        elif intent == QueryIntent.TEMPORAL:
            examples = self._generate_temporal_examples(row_limit)

        if not examples:
            # Fallback to generic examples
            examples = self._generate_table_examples(row_limit)

        return self._format_examples(examples[:4])  # Limit to 4 examples

    def _generate_ranking_examples(self, row_limit: int) -> List[SQLExample]:
        """Generate TOP N / ORDER BY examples."""
        examples = []

        for table in self.tables[:2]:
            # Find a sortable column
            numeric_col = self._find_numeric_column(table)
            if numeric_col:
                examples.append(SQLExample(
                    question=f"Top {row_limit} {table} by {numeric_col}",
                    sql=f"SELECT * FROM {table} ORDER BY {numeric_col} DESC LIMIT {row_limit}",
                    intent=QueryIntent.RANKING
                ))
            else:
                # Use any column for sorting
                columns = self._get_table_columns(table)
                if columns:
                    sort_col = columns[0]
                    examples.append(SQLExample(
                        question=f"First {row_limit} {table}",
                        sql=f"SELECT * FROM {table} ORDER BY {sort_col} LIMIT {row_limit}",
                        intent=QueryIntent.RANKING
                    ))

        return examples

    def _generate_temporal_examples(self, row_limit: int) -> List[SQLExample]:
        """Generate date/time filtering examples."""
        examples = []
        date_keywords = ['date', 'time', 'created', 'updated', 'timestamp', 'when']

        for table in self.tables[:2]:
            columns = self._get_columns_info(table)
            for col in columns:
                col_name = col.get("name", "").lower()
                if any(kw in col_name for kw in date_keywords):
                    examples.append(SQLExample(
                        question=f"{table} from the last 30 days",
                        sql=(f"SELECT * FROM {table} "
                             f"WHERE {col['name']} >= CURRENT_DATE - INTERVAL '30 days' "
                             f"LIMIT {row_limit}"),
                        intent=QueryIntent.TEMPORAL
                    ))
                    return examples  # One example is enough

        return examples
