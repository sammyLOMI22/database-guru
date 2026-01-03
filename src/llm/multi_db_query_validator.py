"""
Multi-Database Query Validator

Phase 2.4: Per-Database Query Intelligence

Validates query feasibility across multiple databases with different schemas.
Assesses each database's capability (FULL/PARTIAL/CANNOT) and generates
per-database SQL when schemas differ.

Example:
    Query: "Show orders from California"

    Database A (orders has state column):
      -> FULL capability: SELECT * FROM orders WHERE state = 'CA'

    Database B (orders has NO state column):
      -> CANNOT capability: Missing column 'state' in orders table
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Any, Tuple

logger = logging.getLogger(__name__)


class QueryCapability(Enum):
    """Capability assessment for a database to answer a query."""
    FULL = "full"       # Can answer completely with original SQL
    PARTIAL = "partial" # Can answer with modifications (alternatives found)
    CANNOT = "cannot"   # Cannot answer at all (missing required data)


@dataclass
class DatabaseQueryAssessment:
    """Assessment of whether a database can answer a query."""
    connection_id: int
    connection_name: str
    database_type: str
    capability: QueryCapability
    missing_tables: List[str]
    missing_columns: Dict[str, List[str]]  # table -> [columns]
    available_alternatives: Dict[str, str]  # "table.column" -> "alternative_column"
    suggested_sql: Optional[str]  # Modified SQL if PARTIAL capability
    reason: str
    confidence: float  # 0.0-1.0 confidence in assessment

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "connection_id": self.connection_id,
            "connection_name": self.connection_name,
            "database_type": self.database_type,
            "capability": self.capability.value,
            "missing_tables": self.missing_tables,
            "missing_columns": self.missing_columns,
            "available_alternatives": self.available_alternatives,
            "suggested_sql": self.suggested_sql,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class MultiDatabaseValidationResult:
    """Result of validating a query across all databases."""
    assessments: Dict[int, DatabaseQueryAssessment]  # connection_id -> assessment
    can_execute_any: bool  # At least one FULL or PARTIAL capability
    all_full: bool  # All databases have FULL capability
    primary_sql: str  # Base SQL for FULL capability databases
    warnings: List[str] = field(default_factory=list)

    def get_executable_databases(self) -> List[int]:
        """Get connection IDs for databases that can execute (FULL or PARTIAL)."""
        return [
            conn_id for conn_id, assessment in self.assessments.items()
            if assessment.capability in (QueryCapability.FULL, QueryCapability.PARTIAL)
        ]

    def get_summary(self) -> Dict[str, int]:
        """Get summary counts by capability."""
        counts = {"full": 0, "partial": 0, "cannot": 0}
        for assessment in self.assessments.values():
            counts[assessment.capability.value] += 1
        return counts


class MultiDatabaseQueryValidator:
    """
    Validates query feasibility across multiple databases.

    This validator performs pre-flight checks before query execution to:
    1. Identify which databases can answer the query
    2. Find alternative columns for missing ones
    3. Generate modified SQL for partial matches
    4. Provide informative feedback for non-answerable databases
    """

    # Common alternative column mappings
    COMMON_ALTERNATIVES: Dict[str, List[str]] = {
        "state": ["region", "province", "territory", "state_code", "location_state"],
        "country": ["nation", "country_code", "country_name", "location_country"],
        "city": ["town", "municipality", "city_name", "location_city"],
        "name": ["title", "label", "description", "full_name"],
        "price": ["cost", "amount", "unit_price", "total_price"],
        "date": ["created_at", "timestamp", "datetime", "created_date"],
        "id": ["uuid", "identifier", "pk", "key"],
        "status": ["state", "condition", "status_code"],
        "email": ["email_address", "mail", "contact_email"],
        "phone": ["telephone", "phone_number", "contact_phone"],
    }

    # US State names and codes for location detection
    US_STATES = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new hampshire", "new jersey", "new mexico", "new york",
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west virginia", "wisconsin", "wyoming",
        # State codes
        "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi",
        "id", "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi",
        "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc",
        "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
        "vt", "va", "wa", "wv", "wi", "wy",
    }

    # Location-related column names to look for
    LOCATION_COLUMNS = [
        "state", "state_code", "region", "province", "territory",
        "city", "town", "location", "address", "country", "zip", "postal_code",
    ]

    def __init__(self, schemas: Dict[int, Dict[str, Any]]):
        """
        Initialize validator with schemas.

        Args:
            schemas: Map of connection_id -> schema_dict
                     Schema dict should have format:
                     {
                         "name": "Database Name",
                         "database_type": "postgresql",
                         "tables": {
                             "table_name": {
                                 "columns": [
                                     {"name": "col1", "type": "integer"},
                                     ...
                                 ]
                             }
                         }
                     }
        """
        self.schemas = schemas
        self._build_schema_indexes()

    def _build_schema_indexes(self) -> None:
        """Build indexes for fast lookup."""
        self.tables_by_db: Dict[int, Set[str]] = {}
        self.columns_by_table: Dict[int, Dict[str, Set[str]]] = {}

        for conn_id, schema in self.schemas.items():
            tables = schema.get("tables", {})
            self.tables_by_db[conn_id] = set(t.lower() for t in tables.keys())

            self.columns_by_table[conn_id] = {}
            for table_name, table_info in tables.items():
                columns = table_info.get("columns", [])
                col_names = set()
                for col in columns:
                    if isinstance(col, dict):
                        col_names.add(col.get("name", "").lower())
                    elif isinstance(col, str):
                        col_names.add(col.lower())
                self.columns_by_table[conn_id][table_name.lower()] = col_names

    def assess_query(
        self,
        question: str,
        base_sql: str,
        connection_names: Dict[int, str]
    ) -> MultiDatabaseValidationResult:
        """
        Assess all databases and return combined result.

        Args:
            question: Natural language question
            base_sql: SQL generated for primary database (can be empty)
            connection_names: Map of connection_id -> display name

        Returns:
            MultiDatabaseValidationResult with per-database assessments
        """
        logger.info(f"Validating query across {len(self.schemas)} databases")

        # Extract requirements from SQL if available, otherwise from question
        if base_sql and base_sql.strip():
            required = self._extract_requirements(base_sql)
            logger.debug(f"SQL requirements: {required}")
        else:
            required = self._extract_requirements_from_question(question)
            logger.debug(f"Question-based requirements: {required}")

        # Assess each database
        assessments: Dict[int, DatabaseQueryAssessment] = {}

        for conn_id, schema in self.schemas.items():
            conn_name = connection_names.get(conn_id, f"Database {conn_id}")
            db_type = schema.get("database_type", "unknown")

            assessment = self._assess_database(
                conn_id=conn_id,
                conn_name=conn_name,
                db_type=db_type,
                schema=schema,
                required=required,
                base_sql=base_sql
            )
            assessments[conn_id] = assessment

            logger.info(
                f"Database '{conn_name}' ({conn_id}): {assessment.capability.value} - {assessment.reason}"
            )

        # Calculate summary flags
        can_execute_any = any(
            a.capability in (QueryCapability.FULL, QueryCapability.PARTIAL)
            for a in assessments.values()
        )
        all_full = all(
            a.capability == QueryCapability.FULL
            for a in assessments.values()
        )

        # Generate warnings
        warnings = []
        summary = {"full": 0, "partial": 0, "cannot": 0}
        for a in assessments.values():
            summary[a.capability.value] += 1

        if summary["cannot"] > 0:
            warnings.append(
                f"{summary['cannot']} database(s) cannot answer this query"
            )
        if summary["partial"] > 0:
            warnings.append(
                f"{summary['partial']} database(s) will use modified SQL"
            )

        return MultiDatabaseValidationResult(
            assessments=assessments,
            can_execute_any=can_execute_any,
            all_full=all_full,
            primary_sql=base_sql,
            warnings=warnings
        )

    def _extract_requirements(self, sql: str) -> Dict[str, Any]:
        """
        Extract tables and columns from SQL.

        Args:
            sql: SQL query string

        Returns:
            Dict with "tables" list and "columns" dict (table -> [columns])
        """
        tables: Set[str] = set()
        columns: Dict[str, Set[str]] = {}

        sql_upper = sql.upper()
        sql_clean = re.sub(r"'[^']*'", "", sql)  # Remove string literals
        sql_clean = re.sub(r'"[^"]*"', "", sql_clean)  # Remove quoted identifiers

        # Extract tables from FROM clause
        from_match = re.search(
            r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            sql_clean,
            re.IGNORECASE
        )
        if from_match:
            tables.add(from_match.group(1).lower())

        # Extract tables from JOIN clauses
        join_matches = re.findall(
            r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            sql_clean,
            re.IGNORECASE
        )
        for match in join_matches:
            tables.add(match.lower())

        # Extract columns from SELECT clause
        select_match = re.search(
            r'\bSELECT\s+(.*?)\s+FROM\b',
            sql_clean,
            re.IGNORECASE | re.DOTALL
        )
        if select_match:
            select_clause = select_match.group(1)
            # Handle SELECT *
            if '*' not in select_clause:
                # Extract column references
                col_refs = re.findall(
                    r'\b([a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)\b',
                    select_clause
                )
                for table_prefix, col_name in col_refs:
                    col_name = col_name.lower()
                    # Skip SQL keywords
                    if col_name.upper() in ('AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN'):
                        continue
                    # Add to first table if no prefix
                    if tables:
                        first_table = next(iter(tables))
                        if first_table not in columns:
                            columns[first_table] = set()
                        columns[first_table].add(col_name)

        # Extract columns from WHERE clause
        where_match = re.search(
            r'\bWHERE\s+(.*?)(?:\bORDER\b|\bGROUP\b|\bLIMIT\b|\bHAVING\b|$)',
            sql_clean,
            re.IGNORECASE | re.DOTALL
        )
        if where_match:
            where_clause = where_match.group(1)
            # Extract column references from WHERE
            col_refs = re.findall(
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|<>|<|>|<=|>=|LIKE|IN|IS)',
                where_clause,
                re.IGNORECASE
            )
            for col_name in col_refs:
                col_name = col_name.lower()
                if col_name.upper() not in ('AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE'):
                    if tables:
                        first_table = next(iter(tables))
                        if first_table not in columns:
                            columns[first_table] = set()
                        columns[first_table].add(col_name)

        # Extract columns from ORDER BY clause
        order_match = re.search(
            r'\bORDER\s+BY\s+(.*?)(?:\bLIMIT\b|$)',
            sql_clean,
            re.IGNORECASE | re.DOTALL
        )
        if order_match:
            order_clause = order_match.group(1)
            col_refs = re.findall(
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b',
                order_clause
            )
            for col_name in col_refs:
                col_name = col_name.lower()
                if col_name.upper() not in ('ASC', 'DESC', 'NULLS', 'FIRST', 'LAST'):
                    if tables:
                        first_table = next(iter(tables))
                        if first_table not in columns:
                            columns[first_table] = set()
                        columns[first_table].add(col_name)

        return {
            "tables": list(tables),
            "columns": {t: list(c) for t, c in columns.items()}
        }

    def _extract_requirements_from_question(self, question: str) -> Dict[str, Any]:
        """
        Extract likely table/column requirements from natural language question.

        This is used when SQL is not yet available for pre-flight validation.
        Detects patterns like:
        - Location mentions (California, CA) -> needs location column
        - "from [table]" -> likely table reference
        - Table name mentions in question

        Args:
            question: Natural language question

        Returns:
            Dict with "tables" list, "columns" dict, and "needs_location" flag
        """
        question_lower = question.lower()
        tables: Set[str] = set()
        likely_columns: Dict[str, Set[str]] = {}
        needs_location = False
        detected_locations: List[str] = []

        # Detect US state mentions (indicates need for location column)
        for state in self.US_STATES:
            if state in question_lower:
                needs_location = True
                detected_locations.append(state)
                logger.info(f"Detected location mention: '{state}' - query needs location column")
                break

        # Also check for "from [location]" pattern
        from_location = re.search(
            r'\bfrom\s+(\w+(?:\s+\w+)?)\b',
            question_lower
        )
        if from_location:
            location_candidate = from_location.group(1)
            # Check if it's a US state (full name or code)
            if location_candidate in self.US_STATES or location_candidate.replace(" ", "") in self.US_STATES:
                needs_location = True
                detected_locations.append(location_candidate)

        # Try to detect likely table names from schema
        for conn_id, conn_tables in self.tables_by_db.items():
            for table_name in conn_tables:
                # Check if table name appears in question
                if table_name in question_lower or table_name.rstrip('s') in question_lower:
                    tables.add(table_name)
                # Also check singular forms (orders -> order)
                if table_name.endswith('s') and table_name[:-1] in question_lower:
                    tables.add(table_name)

        # If location needed, add location column requirement
        if needs_location and tables:
            for table in tables:
                if table not in likely_columns:
                    likely_columns[table] = set()
                # Add common location column names as requirements
                likely_columns[table].update(["state", "region", "location"])

        return {
            "tables": list(tables),
            "columns": {t: list(c) for t, c in likely_columns.items()},
            "needs_location": needs_location,
            "detected_locations": detected_locations,
        }

    def _assess_database(
        self,
        conn_id: int,
        conn_name: str,
        db_type: str,
        schema: Dict[str, Any],
        required: Dict[str, Any],
        base_sql: str
    ) -> DatabaseQueryAssessment:
        """
        Assess a single database's capability to answer the query.

        Args:
            conn_id: Connection ID
            conn_name: Connection display name
            db_type: Database type (postgresql, mysql, etc.)
            schema: Schema dictionary
            required: Required tables and columns from SQL
            base_sql: Original SQL query

        Returns:
            DatabaseQueryAssessment with capability determination
        """
        missing_tables: List[str] = []
        missing_columns: Dict[str, List[str]] = {}
        alternatives: Dict[str, str] = {}

        available_tables = self.tables_by_db.get(conn_id, set())

        # Special check: If query needs location filtering, verify database has location columns
        # When validating from question (no SQL yet), check ALL tables since JOINs may be needed
        needs_location = required.get("needs_location", False)
        detected_locations = required.get("detected_locations", [])
        location_satisfied = False  # Track if location requirement is met

        if needs_location and detected_locations:
            # Check ALL tables in the database for location columns
            all_tables_cols = self.columns_by_table.get(conn_id, {})

            for tbl_name, cols in all_tables_cols.items():
                for loc_col in self.LOCATION_COLUMNS:
                    if loc_col in cols:
                        location_satisfied = True
                        logger.info(
                            f"Location column '{loc_col}' found in {conn_name}.{tbl_name} "
                            f"(LLM can JOIN if needed for '{detected_locations}')"
                        )
                        break
                if location_satisfied:
                    break

            if not location_satisfied:
                # No location column anywhere - mark as missing
                for table in required.get("tables", []):
                    if table not in missing_columns:
                        missing_columns[table] = []
                    missing_columns[table].append("location column (state/region/city)")
                logger.warning(
                    f"No location column found in any table in {conn_name} for '{detected_locations}'"
                )

        # Check required tables
        for table in required.get("tables", []):
            table_lower = table.lower()
            if table_lower not in available_tables:
                missing_tables.append(table)
                # Try to find similar table
                similar = self._find_similar(table_lower, available_tables, threshold=0.7)
                if similar:
                    alternatives[table] = similar

        # Check required columns (only for existing tables)
        for table, cols in required.get("columns", {}).items():
            table_lower = table.lower()
            if table_lower in missing_tables:
                continue  # Skip if table is missing

            available_cols = self.columns_by_table.get(conn_id, {}).get(table_lower, set())

            for col in cols:
                col_lower = col.lower()

                # Skip location columns if location requirement is satisfied elsewhere
                if location_satisfied and col_lower in self.LOCATION_COLUMNS:
                    logger.debug(f"Skipping location column '{col}' check - satisfied via JOIN")
                    continue

                if col_lower not in available_cols:
                    if table not in missing_columns:
                        missing_columns[table] = []
                    missing_columns[table].append(col)

                    # Try to find alternative
                    alt = self._find_alternative_column(col_lower, available_cols)
                    if alt:
                        alternatives[f"{table}.{col}"] = alt

        # Determine capability
        if not missing_tables and not missing_columns:
            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=conn_name,
                database_type=db_type,
                capability=QueryCapability.FULL,
                missing_tables=[],
                missing_columns={},
                available_alternatives={},
                suggested_sql=None,
                reason="All required tables and columns are available",
                confidence=1.0
            )

        elif missing_tables and not alternatives:
            # Tables missing with no alternatives
            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=conn_name,
                database_type=db_type,
                capability=QueryCapability.CANNOT,
                missing_tables=missing_tables,
                missing_columns=missing_columns,
                available_alternatives=alternatives,
                suggested_sql=None,
                reason=f"Required table(s) not found: {', '.join(missing_tables)}",
                confidence=0.95
            )

        elif missing_columns and not alternatives:
            # Columns missing with no alternatives
            missing_desc = [
                f"{t}.{c}" for t, cols in missing_columns.items() for c in cols
            ]
            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=conn_name,
                database_type=db_type,
                capability=QueryCapability.CANNOT,
                missing_tables=missing_tables,
                missing_columns=missing_columns,
                available_alternatives=alternatives,
                suggested_sql=None,
                reason=f"Required column(s) not found: {', '.join(missing_desc)}",
                confidence=0.9
            )

        else:
            # Has alternatives - can potentially answer with modifications
            suggested_sql = self._generate_alternative_sql(
                base_sql, alternatives
            )

            alt_desc = [
                f"{k} -> {v}" for k, v in alternatives.items()
            ]

            return DatabaseQueryAssessment(
                connection_id=conn_id,
                connection_name=conn_name,
                database_type=db_type,
                capability=QueryCapability.PARTIAL,
                missing_tables=missing_tables,
                missing_columns=missing_columns,
                available_alternatives=alternatives,
                suggested_sql=suggested_sql,
                reason=f"Using alternatives: {', '.join(alt_desc)}",
                confidence=0.7
            )

    def _find_alternative_column(
        self,
        target: str,
        available: Set[str]
    ) -> Optional[str]:
        """
        Find alternative column name.

        First checks common alternatives, then uses fuzzy matching.

        Args:
            target: Target column name
            available: Available column names in database

        Returns:
            Alternative column name or None
        """
        target_lower = target.lower()

        # Check common alternatives first
        if target_lower in self.COMMON_ALTERNATIVES:
            for alt in self.COMMON_ALTERNATIVES[target_lower]:
                if alt in available:
                    return alt

        # Check if target is an alternative for something else
        for primary, alternatives in self.COMMON_ALTERNATIVES.items():
            if target_lower in alternatives and primary in available:
                return primary

        # Fall back to fuzzy matching
        return self._find_similar(target_lower, available, threshold=0.6)

    def _find_similar(
        self,
        target: str,
        candidates: Set[str],
        threshold: float = 0.6
    ) -> Optional[str]:
        """
        Find similar name using fuzzy string matching.

        Args:
            target: Target string to match
            candidates: Set of candidate strings
            threshold: Minimum similarity ratio (0.0-1.0)

        Returns:
            Best matching candidate or None
        """
        best_match: Optional[str] = None
        best_ratio: float = threshold

        target_lower = target.lower()

        for candidate in candidates:
            candidate_lower = candidate.lower()

            # Calculate similarity ratio
            ratio = SequenceMatcher(None, target_lower, candidate_lower).ratio()

            # Bonus for substring matches
            if target_lower in candidate_lower or candidate_lower in target_lower:
                ratio = max(ratio, 0.7)

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate

        return best_match

    def _generate_alternative_sql(
        self,
        base_sql: str,
        alternatives: Dict[str, str]
    ) -> Optional[str]:
        """
        Generate modified SQL using alternative column/table names.

        Args:
            base_sql: Original SQL query
            alternatives: Map of "table.column" or "table" -> alternative

        Returns:
            Modified SQL or None if modification not possible
        """
        modified_sql = base_sql

        for original, replacement in alternatives.items():
            if "." in original:
                # Column replacement: "table.column" -> replacement
                table, col = original.split(".", 1)
                # Replace with word boundaries to avoid partial matches
                pattern = rf'\b{re.escape(col)}\b'
                modified_sql = re.sub(pattern, replacement, modified_sql, flags=re.IGNORECASE)
            else:
                # Table replacement
                pattern = rf'\b{re.escape(original)}\b'
                modified_sql = re.sub(pattern, replacement, modified_sql, flags=re.IGNORECASE)

        # Return None if no changes made
        if modified_sql == base_sql:
            return None

        return modified_sql


def validate_multi_database_query(
    question: str,
    base_sql: str,
    schemas: Dict[int, Dict[str, Any]],
    connection_names: Dict[int, str]
) -> MultiDatabaseValidationResult:
    """
    Convenience function to validate a query across multiple databases.

    Args:
        question: Natural language question
        base_sql: SQL generated for primary database
        schemas: Map of connection_id -> schema_dict
        connection_names: Map of connection_id -> display name

    Returns:
        MultiDatabaseValidationResult with per-database assessments
    """
    validator = MultiDatabaseQueryValidator(schemas)
    return validator.assess_query(question, base_sql, connection_names)
