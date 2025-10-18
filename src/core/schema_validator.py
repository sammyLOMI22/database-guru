"""Schema validation and intelligent suggestions for query planning

This module provides schema validation, relationship mapping, and intelligent
suggestions to help the Query Planning Agent handle schema mismatches gracefully.
"""
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class SchemaValidationError:
    """Represents a schema validation error with suggestions"""
    error_type: str  # "missing_table", "missing_column", "invalid_join", etc.
    message: str
    table: Optional[str] = None
    column: Optional[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class JoinPath:
    """Represents a path to join between two tables"""
    from_table: str
    to_table: str
    path: List[Dict[str, str]]  # List of join steps
    confidence: float  # 0.0 to 1.0


class SchemaValidator:
    """
    Validates query plans against database schema and provides intelligent suggestions

    Features:
    - Validates table and column references
    - Suggests similar column/table names when mismatches occur
    - Maps relationships between tables
    - Finds optimal join paths
    - Provides helpful error messages with corrections
    """

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize schema validator

        Args:
            schema: Database schema dictionary from SchemaInspector.get_full_schema()
        """
        self.schema = schema
        self.tables = schema.get("tables", {})
        self.relationships = schema.get("relationships", [])

        # Build lookup structures
        self._build_indices()

    def _build_indices(self):
        """Build fast lookup indices for validation"""
        # Table names
        self.table_names = set(self.tables.keys())

        # Column names by table
        self.columns_by_table: Dict[str, Set[str]] = {}
        for table_name, table_info in self.tables.items():
            columns = {col["name"] for col in table_info.get("columns", [])}
            self.columns_by_table[table_name] = columns

        # All column names (for fuzzy matching)
        self.all_columns: Set[str] = set()
        for columns in self.columns_by_table.values():
            self.all_columns.update(columns)

        # Foreign key relationships (for join path finding)
        self.fk_graph: Dict[str, List[Dict[str, str]]] = {}
        for table_name, table_info in self.tables.items():
            self.fk_graph[table_name] = []
            for fk in table_info.get("foreign_keys", []):
                self.fk_graph[table_name].append({
                    "from_table": table_name,
                    "from_column": fk["column"],
                    "to_table": fk["referred_table"],
                    "to_column": fk["referred_column"]
                })

    def validate_table(self, table_name: str) -> Optional[SchemaValidationError]:
        """
        Validate that a table exists in the schema

        Args:
            table_name: Table name to validate

        Returns:
            SchemaValidationError if invalid, None if valid
        """
        if table_name in self.table_names:
            return None

        # Find similar table names
        suggestions = self._find_similar_names(table_name, self.table_names)

        return SchemaValidationError(
            error_type="missing_table",
            message=f"Table '{table_name}' does not exist in the schema",
            table=table_name,
            suggestions=suggestions
        )

    def validate_column(
        self,
        table_name: str,
        column_name: str,
        check_related_tables: bool = True
    ) -> Optional[SchemaValidationError]:
        """
        Validate that a column exists in the specified table

        Args:
            table_name: Table name
            column_name: Column name to validate
            check_related_tables: If True, also suggest columns from related tables

        Returns:
            SchemaValidationError if invalid, None if valid
        """
        # First validate table exists
        table_error = self.validate_table(table_name)
        if table_error:
            return table_error

        # Check if column exists in table
        table_columns = self.columns_by_table.get(table_name, set())
        if column_name in table_columns:
            return None

        # Build suggestions
        suggestions = []

        # 1. Similar columns in the same table
        similar_in_table = self._find_similar_names(column_name, table_columns, threshold=0.6)
        suggestions.extend([f"{table_name}.{col}" for col in similar_in_table])

        # 2. If enabled, check for the column in related tables
        if check_related_tables:
            related_columns = self._find_column_in_related_tables(table_name, column_name)
            suggestions.extend(related_columns)

        # 3. If no good suggestions, just show similar column names anywhere
        if not suggestions:
            similar_anywhere = self._find_similar_names(column_name, self.all_columns, threshold=0.5)
            for col in similar_anywhere[:3]:  # Limit to top 3
                # Find which table has this column
                for tbl, cols in self.columns_by_table.items():
                    if col in cols:
                        suggestions.append(f"{tbl}.{col}")
                        break

        message = f"Column '{column_name}' does not exist in table '{table_name}'"

        return SchemaValidationError(
            error_type="missing_column",
            message=message,
            table=table_name,
            column=column_name,
            suggestions=suggestions
        )

    def _find_similar_names(
        self,
        target: str,
        candidates: Set[str],
        threshold: float = 0.6
    ) -> List[str]:
        """
        Find similar names using fuzzy string matching

        Args:
            target: Target string to match
            candidates: Set of candidate strings
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of similar names, sorted by similarity
        """
        similarities = []
        target_lower = target.lower()

        for candidate in candidates:
            candidate_lower = candidate.lower()

            # Calculate similarity ratio
            ratio = SequenceMatcher(None, target_lower, candidate_lower).ratio()

            # Bonus for substring matches
            if target_lower in candidate_lower or candidate_lower in target_lower:
                ratio = max(ratio, 0.7)

            if ratio >= threshold:
                similarities.append((candidate, ratio))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [name for name, _ in similarities[:5]]  # Return top 5

    def _find_column_in_related_tables(
        self,
        table_name: str,
        column_name: str
    ) -> List[str]:
        """
        Find a column in tables related to the given table via foreign keys

        Args:
            table_name: Starting table name
            column_name: Column to search for

        Returns:
            List of suggestions like "related_table.column"
        """
        suggestions = []

        # Get directly related tables
        related_tables = self._get_related_tables(table_name)

        for related_table in related_tables:
            related_columns = self.columns_by_table.get(related_table, set())
            if column_name in related_columns:
                suggestions.append(f"{related_table}.{column_name}")

        return suggestions

    def _get_related_tables(self, table_name: str) -> Set[str]:
        """
        Get all tables directly related to the given table via foreign keys

        Args:
            table_name: Table name

        Returns:
            Set of related table names
        """
        related = set()

        # Tables this table references
        for fk in self.fk_graph.get(table_name, []):
            related.add(fk["to_table"])

        # Tables that reference this table
        for other_table, fks in self.fk_graph.items():
            for fk in fks:
                if fk["to_table"] == table_name:
                    related.add(other_table)

        return related

    def find_join_path(
        self,
        from_table: str,
        to_table: str,
        max_hops: int = 3
    ) -> Optional[JoinPath]:
        """
        Find the shortest join path between two tables using foreign keys

        Args:
            from_table: Starting table
            to_table: Target table
            max_hops: Maximum number of joins to consider

        Returns:
            JoinPath if found, None otherwise
        """
        if from_table == to_table:
            return None

        # Validate both tables exist
        if from_table not in self.table_names or to_table not in self.table_names:
            return None

        # BFS to find shortest path
        queue = [(from_table, [])]
        visited = {from_table}

        while queue:
            current_table, path = queue.pop(0)

            if len(path) >= max_hops:
                continue

            # Check foreign keys from current table
            for fk in self.fk_graph.get(current_table, []):
                next_table = fk["to_table"]

                new_path = path + [{
                    "from_table": current_table,
                    "from_column": fk["from_column"],
                    "to_table": next_table,
                    "to_column": fk["to_column"],
                    "join_type": "INNER"
                }]

                if next_table == to_table:
                    # Found path!
                    confidence = 1.0 / (len(new_path) + 1)  # Shorter paths have higher confidence
                    return JoinPath(
                        from_table=from_table,
                        to_table=to_table,
                        path=new_path,
                        confidence=confidence
                    )

                if next_table not in visited:
                    visited.add(next_table)
                    queue.append((next_table, new_path))

            # Also check reverse foreign keys (tables that reference current table)
            for other_table, fks in self.fk_graph.items():
                for fk in fks:
                    if fk["to_table"] == current_table:
                        next_table = other_table

                        new_path = path + [{
                            "from_table": current_table,
                            "from_column": fk["to_column"],
                            "to_table": next_table,
                            "to_column": fk["from_column"],
                            "join_type": "LEFT"  # Reverse FK usually needs LEFT JOIN
                        }]

                        if next_table == to_table:
                            confidence = 0.9 / (len(new_path) + 1)  # Slightly lower confidence for reverse
                            return JoinPath(
                                from_table=from_table,
                                to_table=to_table,
                                path=new_path,
                                confidence=confidence
                            )

                        if next_table not in visited:
                            visited.add(next_table)
                            queue.append((next_table, new_path))

        return None

    def validate_join(
        self,
        from_table: str,
        to_table: str,
        on_condition: str
    ) -> Optional[SchemaValidationError]:
        """
        Validate a join between two tables

        Args:
            from_table: Source table
            to_table: Target table
            on_condition: Join condition (e.g., "a.id = b.a_id")

        Returns:
            SchemaValidationError if invalid, None if valid
        """
        # Validate both tables exist
        for table in [from_table, to_table]:
            error = self.validate_table(table)
            if error:
                return error

        # Try to find a valid join path
        join_path = self.find_join_path(from_table, to_table)

        if not join_path:
            # No direct foreign key relationship found
            suggestions = [
                f"No direct relationship found between {from_table} and {to_table}",
                "Consider adding an intermediate table to join through"
            ]

            # Check if there's a path through another table
            for intermediate_table in self.table_names:
                if intermediate_table in [from_table, to_table]:
                    continue

                path1 = self.find_join_path(from_table, intermediate_table, max_hops=1)
                path2 = self.find_join_path(intermediate_table, to_table, max_hops=1)

                if path1 and path2:
                    suggestions.append(
                        f"Join through '{intermediate_table}': "
                        f"{from_table} → {intermediate_table} → {to_table}"
                    )

            return SchemaValidationError(
                error_type="invalid_join",
                message=f"Cannot find relationship between '{from_table}' and '{to_table}'",
                suggestions=suggestions
            )

        return None

    def suggest_join_conditions(
        self,
        from_table: str,
        to_table: str
    ) -> List[str]:
        """
        Suggest join conditions between two tables

        Args:
            from_table: Source table
            to_table: Target table

        Returns:
            List of suggested join condition strings
        """
        suggestions = []

        join_path = self.find_join_path(from_table, to_table)
        if not join_path:
            return suggestions

        for step in join_path.path:
            condition = (
                f"{step['from_table']}.{step['from_column']} = "
                f"{step['to_table']}.{step['to_column']}"
            )
            suggestions.append(condition)

        return suggestions

    def get_validation_report(self, errors: List[SchemaValidationError]) -> str:
        """
        Generate a human-readable validation report

        Args:
            errors: List of validation errors

        Returns:
            Formatted report string
        """
        if not errors:
            return "✓ Schema validation passed - no errors found"

        lines = [f"✗ Schema validation found {len(errors)} error(s):\n"]

        for i, error in enumerate(errors, 1):
            lines.append(f"{i}. {error.message}")

            if error.suggestions:
                lines.append("   Suggestions:")
                for suggestion in error.suggestions[:3]:  # Limit to top 3
                    lines.append(f"   - {suggestion}")

            lines.append("")  # Blank line between errors

        return "\n".join(lines)

    def detect_primary_key_pattern(self, table_name: str) -> Optional[str]:
        """
        Detect the primary key naming pattern for a table

        Args:
            table_name: Table name

        Returns:
            Primary key column name pattern or None

        Examples:
            - products table → "product_id" or "id"
            - orders table → "order_id" or "id"
        """
        if table_name not in self.table_names:
            return None

        table_info = self.tables.get(table_name, {})
        pk_columns = table_info.get("primary_keys", [])

        if not pk_columns:
            return None

        # Return the first primary key
        pk_col = pk_columns[0]

        # Detect pattern: "table_name_id" vs "id"
        if pk_col == "id":
            return "id"  # Simple pattern
        elif pk_col.endswith("_id"):
            return f"{table_name}_id"  # Table-prefixed pattern
        else:
            return pk_col  # Custom pattern

    def suggest_id_column(self, table_name: str, context: str = "join") -> List[str]:
        """
        Suggest the correct ID column name for a table

        Args:
            table_name: Table name
            context: Context for the suggestion ("join", "filter", etc.)

        Returns:
            List of suggested column names

        Examples:
            >>> validator.suggest_id_column("products")
            ["product_id", "id"]
        """
        suggestions = []

        if table_name not in self.table_names:
            return suggestions

        # Get actual primary key
        actual_pk = self.detect_primary_key_pattern(table_name)
        if actual_pk:
            suggestions.append(actual_pk)

        # Common variations
        common_patterns = [
            "id",
            f"{table_name}_id",
            f"{table_name.rstrip('s')}_id",  # products → product_id
        ]

        for pattern in common_patterns:
            if pattern not in suggestions:
                # Check if this column actually exists
                table_columns = self.columns_by_table.get(table_name, set())
                if pattern in table_columns:
                    suggestions.append(pattern)

        return suggestions

    def detect_foreign_key_pattern(self, from_table: str, to_table: str) -> Optional[Dict[str, str]]:
        """
        Detect the foreign key naming pattern between two tables

        Args:
            from_table: Source table
            to_table: Target table

        Returns:
            Dict with 'from_column' and 'to_column' or None
        """
        if from_table not in self.table_names or to_table not in self.table_names:
            return None

        # Check actual foreign keys
        for fk in self.fk_graph.get(from_table, []):
            if fk["to_table"] == to_table:
                return {
                    "from_column": fk["from_column"],
                    "to_column": fk["to_column"],
                    "pattern": "actual_fk"
                }

        # Try to infer based on naming conventions
        to_pk = self.detect_primary_key_pattern(to_table)
        from_columns = self.columns_by_table.get(from_table, set())

        # Common patterns:
        # 1. customer_id in orders → customers.id
        # 2. customer_id in orders → customers.customer_id
        possible_fk_names = [
            f"{to_table}_id",
            f"{to_table.rstrip('s')}_id",  # customers → customer_id
            to_pk if to_pk else None,
        ]

        for fk_name in possible_fk_names:
            if fk_name and fk_name in from_columns:
                return {
                    "from_column": fk_name,
                    "to_column": to_pk or "id",
                    "pattern": "inferred"
                }

        return None

    def get_schema_naming_hints(self) -> Dict[str, Any]:
        """
        Generate hints about schema naming conventions

        Returns:
            Dict with naming pattern information
        """
        hints = {
            "primary_key_patterns": {},
            "foreign_key_patterns": [],
            "common_conventions": []
        }

        # Detect primary key patterns
        id_patterns = {}
        for table_name in self.table_names:
            pk_pattern = self.detect_primary_key_pattern(table_name)
            if pk_pattern:
                id_patterns[table_name] = pk_pattern

        # Classify patterns
        uses_simple_id = sum(1 for p in id_patterns.values() if p == "id")
        uses_prefixed_id = sum(1 for p in id_patterns.values() if p.endswith("_id") and p != "id")

        if uses_simple_id > uses_prefixed_id:
            hints["common_conventions"].append("Most tables use 'id' for primary keys")
        elif uses_prefixed_id > uses_simple_id:
            hints["common_conventions"].append("Most tables use 'table_name_id' for primary keys")

        hints["primary_key_patterns"] = id_patterns

        # Detect foreign key patterns
        for table_name in self.table_names:
            for fk in self.fk_graph.get(table_name, []):
                hints["foreign_key_patterns"].append({
                    "from": f"{table_name}.{fk['from_column']}",
                    "to": f"{fk['to_table']}.{fk['to_column']}"
                })

        return hints
