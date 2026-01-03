"""Query Template Engine - Bypass LLM for Simple Query Patterns

This module provides template-based SQL generation for common query patterns,
avoiding LLM calls for simple queries. This improves response time and reduces
errors for straightforward requests.

Supported Patterns:
- list_all: "show all products" → SELECT * FROM products LIMIT 100
- count: "how many customers" → SELECT COUNT(*) FROM customers
- top_n: "top 5 by price" → SELECT * FROM X ORDER BY Y DESC LIMIT 5
- filter_location: "orders from California" → SELECT * FROM orders WHERE state = 'CA'
- filter_category: "products in Electronics" → SELECT * FROM products WHERE category = 'Electronics'
- filter_value: "customers where status is active" → SELECT * FROM customers WHERE status = 'active'

Usage:
    engine = TemplateEngine(schema_dict)
    match = engine.try_match("show all customers")
    if match:
        print(match.sql)  # SELECT * FROM customers LIMIT 100
        print(match.confidence)  # 0.95

Part of: Small Model Optimization Phase
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Types of query templates."""
    LIST_ALL = "list_all"
    COUNT = "count"
    TOP_N = "top_n"
    FILTER_LOCATION = "filter_location"
    FILTER_CATEGORY = "filter_category"
    FILTER_VALUE = "filter_value"
    FILTER_DATE = "filter_date"
    SUM_TOTAL = "sum_total"
    AVERAGE = "average"
    GROUP_BY = "group_by"


@dataclass
class TemplateMatch:
    """Result of a template match."""
    template_type: TemplateType
    sql: str
    confidence: float  # 0.0-1.0
    matched_table: str
    matched_columns: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "template": self.template_type.value,
            "sql": self.sql,
            "confidence": self.confidence,
            "table": self.matched_table,
            "columns": self.matched_columns,
            "params": self.parameters,
        }


@dataclass
class SchemaInfo:
    """Simplified schema information for template matching."""
    tables: Dict[str, List[str]]  # table_name -> list of column names
    location_columns: Dict[str, str]  # table_name -> location column name
    category_columns: Dict[str, str]  # table_name -> category/type column name
    numeric_columns: Dict[str, List[str]]  # table_name -> numeric column names
    date_columns: Dict[str, List[str]]  # table_name -> date column names
    sample_values: Dict[str, Dict[str, List[str]]]  # table.column -> sample values


class TemplateEngine:
    """
    Template-based SQL generator for common query patterns.

    Bypasses LLM for simple queries by matching natural language patterns
    to predefined SQL templates. Falls back to None if no pattern matches.
    """

    # Pattern keywords for each template type
    LIST_ALL_PATTERNS = [
        r"^(show|list|get|display|view)\s+(all\s+)?(\w+)$",
        r"^(show|list|get)\s+me\s+(all\s+)?(\w+)$",
        r"^what\s+(are\s+)?(all\s+)?(the\s+)?(\w+)$",
        r"^(all|every)\s+(\w+)$",
    ]

    COUNT_PATTERNS = [
        r"^how\s+many\s+(\w+)",
        r"^count\s+(all\s+)?(\w+)",
        r"^(total|number\s+of)\s+(\w+)",
        r"^(\w+)\s+count$",
    ]

    TOP_N_PATTERNS = [
        r"^top\s+(\d+)\s+(\w+)\s+by\s+(\w+)",
        r"^(\d+)\s+(highest|top|best)\s+(\w+)\s+by\s+(\w+)",
        r"^(highest|top|best)\s+(\d+)\s+(\w+)\s+by\s+(\w+)",
        r"^(\w+)\s+with\s+(highest|most|greatest)\s+(\w+)",
    ]

    BOTTOM_N_PATTERNS = [
        r"^bottom\s+(\d+)\s+(\w+)\s+by\s+(\w+)",
        r"^(\d+)\s+(lowest|bottom|worst)\s+(\w+)\s+by\s+(\w+)",
        r"^(lowest|bottom|worst)\s+(\d+)\s+(\w+)\s+by\s+(\w+)",
        r"^(\w+)\s+with\s+(lowest|least|smallest)\s+(\w+)",
    ]

    FILTER_LOCATION_PATTERNS = [
        r"^(\w+)\s+(from|in)\s+(.+)$",
        r"^(show|list|get)\s+(\w+)\s+(from|in)\s+(.+)$",
        r"^(\w+)\s+located\s+in\s+(.+)$",
    ]

    FILTER_VALUE_PATTERNS = [
        r"^(\w+)\s+where\s+(\w+)\s+(is|=|equals?)\s+['\"]?(.+?)['\"]?$",
        r"^(\w+)\s+with\s+(\w+)\s+(of|=)\s+['\"]?(.+?)['\"]?$",
        r"^(show|list|get)\s+(\w+)\s+where\s+(\w+)\s+(is|=)\s+['\"]?(.+?)['\"]?$",
        # Removed overly general pattern that was matching "show all customers" incorrectly
    ]

    SUM_PATTERNS = [
        r"^(total|sum)\s+(of\s+)?(\w+)\s+(for|in|from)\s+(\w+)",
        r"^(total|sum)\s+(\w+)\s+(for|in|from)\s+(\w+)",
        r"^what\s+is\s+(the\s+)?(total|sum)\s+(of\s+)?(\w+)",
    ]

    AVERAGE_PATTERNS = [
        r"^average\s+(of\s+)?(\w+)\s+(for|in|from)\s+(\w+)",
        r"^(avg|mean)\s+(\w+)\s+(for|in|from)\s+(\w+)",
        r"^what\s+is\s+(the\s+)?average\s+(of\s+)?(\w+)",
    ]

    GROUP_BY_PATTERNS = [
        r"^(\w+)\s+(by|per|grouped\s+by)\s+(\w+)$",
        r"^(count|sum|average|total)\s+(\w+)\s+(by|per)\s+(\w+)$",
        r"^(\w+)\s+(for\s+each|per)\s+(\w+)$",
    ]

    def __init__(self, schema_dict: Dict[str, Any], default_limit: int = 100):
        """
        Initialize the template engine with schema information.

        Args:
            schema_dict: Parsed schema dictionary from SchemaInspector
            default_limit: Default row limit for list queries
        """
        self.default_limit = default_limit
        self.schema_info = self._parse_schema(schema_dict)
        self._table_aliases = self._build_table_aliases()

        logger.debug(
            f"TemplateEngine initialized: {len(self.schema_info.tables)} tables, "
            f"{len(self.schema_info.location_columns)} location columns"
        )

    def _parse_schema(self, schema_dict: Dict[str, Any]) -> SchemaInfo:
        """Extract relevant schema information for template matching."""
        tables = {}
        location_columns = {}
        category_columns = {}
        numeric_columns = {}
        date_columns = {}
        sample_values = {}

        for table_name, table_info in schema_dict.get("tables", {}).items():
            columns = []
            table_numeric = []
            table_dates = []

            for col in table_info.get("columns", []):
                col_name = col.get("name", "")
                col_type = col.get("type", "").lower()
                columns.append(col_name)

                # Track column types
                if any(t in col_type for t in ["int", "float", "decimal", "numeric", "double", "real"]):
                    table_numeric.append(col_name)
                elif any(t in col_type for t in ["date", "time", "timestamp"]):
                    table_dates.append(col_name)

                # Detect location columns
                col_lower = col_name.lower()
                if col_lower in ("state", "st", "state_code", "province", "region", "country", "city"):
                    location_columns[table_name] = col_name

                # Detect category columns
                if col_lower in ("category", "type", "status", "kind", "class", "group", "department"):
                    category_columns[table_name] = col_name

                # Store sample values
                if col.get("sample_values"):
                    key = f"{table_name}.{col_name}"
                    sample_values[key] = col["sample_values"][:20]

            tables[table_name] = columns
            if table_numeric:
                numeric_columns[table_name] = table_numeric
            if table_dates:
                date_columns[table_name] = table_dates

        return SchemaInfo(
            tables=tables,
            location_columns=location_columns,
            category_columns=category_columns,
            numeric_columns=numeric_columns,
            date_columns=date_columns,
            sample_values=sample_values
        )

    def _build_table_aliases(self) -> Dict[str, str]:
        """Build common aliases for table names."""
        aliases = {}

        for table_name in self.schema_info.tables.keys():
            table_lower = table_name.lower()

            # Add the table name itself
            aliases[table_lower] = table_name

            # Add singular/plural variants
            if table_lower.endswith("s"):
                aliases[table_lower[:-1]] = table_name  # customers -> customer
            elif table_lower.endswith("ies"):
                aliases[table_lower[:-3] + "y"] = table_name  # categories -> category
            else:
                aliases[table_lower + "s"] = table_name  # order -> orders

            # Add common abbreviations
            if table_lower == "customers":
                aliases["customer"] = table_name
                aliases["cust"] = table_name
            elif table_lower == "products":
                aliases["product"] = table_name
                aliases["prod"] = table_name
            elif table_lower == "orders":
                aliases["order"] = table_name
            elif table_lower == "employees":
                aliases["employee"] = table_name
                aliases["emp"] = table_name

        return aliases

    def _find_table(self, text: str) -> Optional[str]:
        """Find a table name from text, handling aliases."""
        text_lower = text.lower().strip()

        # Direct match
        if text_lower in self._table_aliases:
            return self._table_aliases[text_lower]

        # Fuzzy match (simple substring)
        for alias, table in self._table_aliases.items():
            if alias in text_lower or text_lower in alias:
                return table

        return None

    def _find_column(self, table: str, text: str) -> Optional[str]:
        """Find a column name in a table, handling common variations."""
        if table not in self.schema_info.tables:
            return None

        text_lower = text.lower().strip()
        columns = self.schema_info.tables[table]

        # Direct match
        for col in columns:
            if col.lower() == text_lower:
                return col

        # Handle common variations
        variations = {
            "price": ["price", "unit_price", "unitprice", "cost", "amount"],
            "name": ["name", "product_name", "customer_name", "item_name", "title"],
            "date": ["date", "created_at", "order_date", "created", "timestamp"],
            "quantity": ["quantity", "qty", "amount", "count"],
            "total": ["total", "total_amount", "amount", "sum"],
            "status": ["status", "state", "condition"],
            "category": ["category", "type", "category_name", "product_category"],
        }

        if text_lower in variations:
            for variant in variations[text_lower]:
                for col in columns:
                    if col.lower() == variant:
                        return col

        # Partial match
        for col in columns:
            if text_lower in col.lower() or col.lower() in text_lower:
                return col

        return None

    def try_match(self, question: str) -> Optional[TemplateMatch]:
        """
        Try to match the question to a template.

        Args:
            question: Natural language question

        Returns:
            TemplateMatch if a pattern matches, None otherwise
        """
        question_clean = question.strip().lower()
        question_clean = re.sub(r'[?!.]$', '', question_clean)  # Remove trailing punctuation

        # Try each template type in order of specificity
        matchers = [
            (self._try_count, TemplateType.COUNT),
            (self._try_top_n, TemplateType.TOP_N),
            (self._try_sum, TemplateType.SUM_TOTAL),
            (self._try_average, TemplateType.AVERAGE),
            (self._try_group_by, TemplateType.GROUP_BY),
            (self._try_filter_location, TemplateType.FILTER_LOCATION),
            (self._try_list_all, TemplateType.LIST_ALL),  # "show all X" before value filters
            (self._try_filter_value, TemplateType.FILTER_VALUE),  # Most general, try last
        ]

        for matcher, template_type in matchers:
            result = matcher(question_clean)
            if result:
                logger.info(
                    f"Template matched: {template_type.value} for '{question}' -> {result.sql}"
                )
                return result

        logger.debug(f"No template match for: '{question}'")
        return None

    def _try_list_all(self, question: str) -> Optional[TemplateMatch]:
        """Try to match list/show all pattern."""
        for pattern in self.LIST_ALL_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                # Extract the table name from the last group
                groups = match.groups()
                table_text = groups[-1] if groups else None

                if table_text:
                    table = self._find_table(table_text)
                    if table:
                        sql = f"SELECT * FROM {table} LIMIT {self.default_limit}"
                        return TemplateMatch(
                            template_type=TemplateType.LIST_ALL,
                            sql=sql,
                            confidence=0.95,
                            matched_table=table,
                            explanation=f"List all records from {table}"
                        )

        return None

    def _try_count(self, question: str) -> Optional[TemplateMatch]:
        """Try to match count pattern."""
        for pattern in self.COUNT_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Find the table name (usually last non-None group)
                table_text = None
                for g in reversed(groups):
                    if g and g.lower() not in ("all", "the"):
                        table_text = g
                        break

                if table_text:
                    table = self._find_table(table_text)
                    if table:
                        sql = f"SELECT COUNT(*) as count FROM {table}"
                        return TemplateMatch(
                            template_type=TemplateType.COUNT,
                            sql=sql,
                            confidence=0.95,
                            matched_table=table,
                            explanation=f"Count all records in {table}"
                        )

        return None

    def _try_top_n(self, question: str) -> Optional[TemplateMatch]:
        """Try to match top N pattern."""
        # Check for descending (top/highest)
        for pattern in self.TOP_N_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = match.groups()
                n = None
                table_text = None
                column_text = None

                # Parse groups based on pattern structure
                for g in groups:
                    if g and g.isdigit():
                        n = int(g)
                    elif g and g.lower() not in ("highest", "top", "best", "by"):
                        if table_text is None:
                            table_text = g
                        else:
                            column_text = g

                if n and table_text:
                    table = self._find_table(table_text)
                    if table:
                        # Find the sort column
                        sort_col = self._find_column(table, column_text) if column_text else None
                        if not sort_col:
                            # Default to first numeric column
                            numeric = self.schema_info.numeric_columns.get(table, [])
                            sort_col = numeric[0] if numeric else "id"

                        sql = f"SELECT * FROM {table} ORDER BY {sort_col} DESC LIMIT {n}"
                        return TemplateMatch(
                            template_type=TemplateType.TOP_N,
                            sql=sql,
                            confidence=0.90,
                            matched_table=table,
                            matched_columns=[sort_col],
                            parameters={"n": n, "order": "DESC"},
                            explanation=f"Top {n} {table} by {sort_col}"
                        )

        # Check for ascending (bottom/lowest)
        for pattern in self.BOTTOM_N_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = match.groups()
                n = None
                table_text = None
                column_text = None

                for g in groups:
                    if g and g.isdigit():
                        n = int(g)
                    elif g and g.lower() not in ("lowest", "bottom", "worst", "by"):
                        if table_text is None:
                            table_text = g
                        else:
                            column_text = g

                if n and table_text:
                    table = self._find_table(table_text)
                    if table:
                        sort_col = self._find_column(table, column_text) if column_text else None
                        if not sort_col:
                            numeric = self.schema_info.numeric_columns.get(table, [])
                            sort_col = numeric[0] if numeric else "id"

                        sql = f"SELECT * FROM {table} ORDER BY {sort_col} ASC LIMIT {n}"
                        return TemplateMatch(
                            template_type=TemplateType.TOP_N,
                            sql=sql,
                            confidence=0.90,
                            matched_table=table,
                            matched_columns=[sort_col],
                            parameters={"n": n, "order": "ASC"},
                            explanation=f"Bottom {n} {table} by {sort_col}"
                        )

        return None

    def _try_filter_location(self, question: str) -> Optional[TemplateMatch]:
        """Try to match location filter pattern."""
        for pattern in self.FILTER_LOCATION_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = match.groups()

                # Find table and location
                table_text = None
                location_text = None

                for i, g in enumerate(groups):
                    if g and g.lower() not in ("from", "in", "show", "list", "get", "located"):
                        if table_text is None:
                            table_text = g
                        else:
                            location_text = g

                if table_text and location_text:
                    table = self._find_table(table_text)
                    if table and table in self.schema_info.location_columns:
                        loc_col = self.schema_info.location_columns[table]

                        # Normalize location value
                        location_value = self._normalize_location(location_text, table, loc_col)

                        sql = f"SELECT * FROM {table} WHERE {loc_col} = '{location_value}' LIMIT {self.default_limit}"
                        return TemplateMatch(
                            template_type=TemplateType.FILTER_LOCATION,
                            sql=sql,
                            confidence=0.90,
                            matched_table=table,
                            matched_columns=[loc_col],
                            parameters={"location": location_value},
                            explanation=f"{table} from {location_value}"
                        )

        return None

    def _normalize_location(self, location: str, table: str, column: str) -> str:
        """Normalize location value based on database format."""
        try:
            from src.core.location_mapper import LocationMapper

            # Check sample values to determine format
            key = f"{table}.{column}"
            samples = self.schema_info.sample_values.get(key, [])

            if samples:
                # Detect if DB uses codes or full names
                code_count = sum(1 for v in samples if len(str(v)) == 2 and str(v).isupper())
                if code_count > len(samples) / 2:
                    # DB uses codes
                    normalized = LocationMapper.normalize_us_state(location)
                    if normalized:
                        return normalized

            # Default: return as-is with title case
            return location.strip()

        except ImportError:
            return location.strip()

    def _try_filter_value(self, question: str) -> Optional[TemplateMatch]:
        """Try to match value filter pattern."""
        for pattern in self.FILTER_VALUE_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = match.groups()

                # Different patterns have different group structures
                table_text = None
                column_text = None
                value_text = None

                # Parse based on number of groups
                clean_groups = [g for g in groups if g and g.lower() not in ("is", "=", "equals", "of", "with", "where", "show", "list", "get")]

                if len(clean_groups) >= 3:
                    table_text = clean_groups[0]
                    column_text = clean_groups[1]
                    value_text = clean_groups[2]
                elif len(clean_groups) == 2:
                    # Could be "active customers" pattern
                    value_text = clean_groups[0]
                    table_text = clean_groups[1]

                if table_text:
                    table = self._find_table(table_text)
                    if table:
                        # Find the filter column
                        filter_col = None
                        if column_text:
                            filter_col = self._find_column(table, column_text)

                        if not filter_col and value_text:
                            # Try to find column by value match
                            filter_col = self._find_column_by_value(table, value_text)

                        if not filter_col:
                            # Default to category/status column
                            filter_col = self.schema_info.category_columns.get(table)

                        if filter_col and value_text:
                            # Clean up value
                            clean_value = value_text.strip().strip("'\"")

                            sql = f"SELECT * FROM {table} WHERE {filter_col} = '{clean_value}' LIMIT {self.default_limit}"
                            return TemplateMatch(
                                template_type=TemplateType.FILTER_VALUE,
                                sql=sql,
                                confidence=0.85,
                                matched_table=table,
                                matched_columns=[filter_col],
                                parameters={"column": filter_col, "value": clean_value},
                                explanation=f"{table} where {filter_col} = '{clean_value}'"
                            )

        return None

    def _find_column_by_value(self, table: str, value: str) -> Optional[str]:
        """Find column that contains a specific value."""
        value_lower = value.lower().strip()

        for col in self.schema_info.tables.get(table, []):
            key = f"{table}.{col}"
            samples = self.schema_info.sample_values.get(key, [])

            for sample in samples:
                if str(sample).lower() == value_lower:
                    return col

        return None

    def _try_sum(self, question: str) -> Optional[TemplateMatch]:
        """Try to match sum/total pattern."""
        for pattern in self.SUM_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g and g.lower() not in ("total", "sum", "of", "for", "in", "from", "the", "is", "what")]

                if len(groups) >= 2:
                    column_text = groups[0]
                    table_text = groups[1]

                    table = self._find_table(table_text)
                    if table:
                        column = self._find_column(table, column_text)
                        if column:
                            sql = f"SELECT SUM({column}) as total FROM {table}"
                            return TemplateMatch(
                                template_type=TemplateType.SUM_TOTAL,
                                sql=sql,
                                confidence=0.90,
                                matched_table=table,
                                matched_columns=[column],
                                explanation=f"Sum of {column} in {table}"
                            )

        return None

    def _try_average(self, question: str) -> Optional[TemplateMatch]:
        """Try to match average pattern."""
        for pattern in self.AVERAGE_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g and g.lower() not in ("average", "avg", "mean", "of", "for", "in", "from", "the", "is", "what")]

                if len(groups) >= 2:
                    column_text = groups[0]
                    table_text = groups[1]

                    table = self._find_table(table_text)
                    if table:
                        column = self._find_column(table, column_text)
                        if column:
                            sql = f"SELECT AVG({column}) as average FROM {table}"
                            return TemplateMatch(
                                template_type=TemplateType.AVERAGE,
                                sql=sql,
                                confidence=0.90,
                                matched_table=table,
                                matched_columns=[column],
                                explanation=f"Average of {column} in {table}"
                            )

        return None

    def _try_group_by(self, question: str) -> Optional[TemplateMatch]:
        """Try to match group by pattern."""
        for pattern in self.GROUP_BY_PATTERNS:
            match = re.match(pattern, question, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g and g.lower() not in ("by", "per", "grouped", "for", "each")]

                if len(groups) >= 2:
                    # First group is usually the aggregation, last is group column
                    agg_text = groups[0]
                    group_col_text = groups[-1]

                    # Check if first is an aggregation function
                    agg_func = None
                    table_text = None

                    if agg_text.lower() in ("count", "sum", "average", "total"):
                        agg_func = "COUNT(*)" if agg_text.lower() == "count" else f"{agg_text.upper()}(*)"
                        if len(groups) > 2:
                            table_text = groups[1]
                    else:
                        table_text = agg_text
                        agg_func = "COUNT(*)"

                    if table_text:
                        table = self._find_table(table_text)
                        if not table:
                            table = self._find_table(group_col_text)
                            if table:
                                group_col_text = table_text

                        if table:
                            group_col = self._find_column(table, group_col_text)
                            if group_col:
                                sql = f"SELECT {group_col}, {agg_func} as count FROM {table} GROUP BY {group_col} ORDER BY count DESC"
                                return TemplateMatch(
                                    template_type=TemplateType.GROUP_BY,
                                    sql=sql,
                                    confidence=0.85,
                                    matched_table=table,
                                    matched_columns=[group_col],
                                    explanation=f"Count {table} grouped by {group_col}"
                                )

        return None


def try_template_match(
    question: str,
    schema_dict: Dict[str, Any],
    default_limit: int = 100
) -> Optional[TemplateMatch]:
    """
    Convenience function to try matching a question to a template.

    Args:
        question: Natural language question
        schema_dict: Schema dictionary from SchemaInspector
        default_limit: Default row limit

    Returns:
        TemplateMatch if pattern matches, None otherwise
    """
    engine = TemplateEngine(schema_dict, default_limit)
    return engine.try_match(question)
