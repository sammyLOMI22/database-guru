"""
Schema Health Analyzer - Phase 12.3

Analyzes database schema design quality with:
- Index suggestions based on query patterns
- Normalization analysis
- Anti-pattern detection
- LLM-enhanced recommendations

Uses SchemaInspector for schema data and QueryPatternAnalyzer for usage patterns.
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.schema_inspector import SchemaInspector
from src.lineage.query_pattern_analyzer import QueryPatternAnalyzer
from src.database.models import QueryHistory, DatabaseConnection
from src.lineage.llm_utils import extract_json_object

logger = logging.getLogger(__name__)


class HealthGrade(Enum):
    """Overall schema health grade."""
    EXCELLENT = "A"
    GOOD = "B"
    FAIR = "C"
    POOR = "D"
    CRITICAL = "F"


class IssueSeverity(Enum):
    """Severity of a schema issue."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Category of schema issue."""
    INDEXING = "indexing"
    NORMALIZATION = "normalization"
    NAMING = "naming"
    STRUCTURE = "structure"
    PERFORMANCE = "performance"
    INTEGRITY = "integrity"


@dataclass
class IndexSuggestion:
    """A suggested index to improve query performance."""
    table_name: str
    columns: List[str]
    index_type: str = "btree"  # btree, hash, gin, etc.
    reason: str = ""
    estimated_impact: str = "medium"  # low, medium, high
    create_sql: str = ""
    query_count_benefiting: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SchemaIssue:
    """A detected schema issue or anti-pattern."""
    category: str
    severity: str
    title: str
    description: str
    affected_objects: List[str] = field(default_factory=list)
    recommendation: str = ""
    fix_sql: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class NormalizationIssue:
    """A normalization violation."""
    table_name: str
    issue_type: str  # 1NF, 2NF, 3NF violation
    description: str
    affected_columns: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TableHealthSummary:
    """Health summary for a single table."""
    table_name: str
    column_count: int
    has_primary_key: bool
    foreign_key_count: int
    index_count: int
    issues: List[SchemaIssue] = field(default_factory=list)
    suggestions: List[IndexSuggestion] = field(default_factory=list)

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["issues"] = [i.to_dict() if isinstance(i, SchemaIssue) else i for i in self.issues]
        result["suggestions"] = [s.to_dict() if isinstance(s, IndexSuggestion) else s for s in self.suggestions]
        return result


@dataclass
class SchemaHealthReport:
    """Complete schema health analysis report."""
    connection_id: int
    database_name: str
    grade: str = HealthGrade.GOOD.value
    score: int = 75  # 0-100
    table_count: int = 0
    total_issues: int = 0
    critical_issues: int = 0

    # Detailed findings
    index_suggestions: List[IndexSuggestion] = field(default_factory=list)
    normalization_issues: List[NormalizationIssue] = field(default_factory=list)
    anti_patterns: List[SchemaIssue] = field(default_factory=list)
    table_summaries: List[TableHealthSummary] = field(default_factory=list)

    # LLM-generated summary
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: Optional[str] = None
    llm_used: bool = False

    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        result = {
            "connection_id": self.connection_id,
            "database_name": self.database_name,
            "grade": self.grade,
            "score": self.score,
            "table_count": self.table_count,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "index_suggestions": [s.to_dict() if isinstance(s, IndexSuggestion) else s for s in self.index_suggestions],
            "normalization_issues": [n.to_dict() if isinstance(n, NormalizationIssue) else n for n in self.normalization_issues],
            "anti_patterns": [a.to_dict() if isinstance(a, SchemaIssue) else a for a in self.anti_patterns],
            "table_summaries": [t.to_dict() if isinstance(t, TableHealthSummary) else t for t in self.table_summaries],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "analyzed_at": self.analyzed_at,
            "llm_used": self.llm_used,
        }
        return result


# LLM Prompt for enhanced analysis
SCHEMA_HEALTH_PROMPT = """Analyze this database schema for design quality and provide recommendations.

## Schema Overview
Database: {database_name}
Tables: {table_count}
Total Columns: {total_columns}

## Tables Structure
{schema_formatted}

## Query Pattern Data
Most Used Tables: {most_used_tables}
Common Join Patterns: {join_patterns}
Performance Bottlenecks: {bottlenecks}

## Detected Issues
{detected_issues}

## Index Suggestions
{index_suggestions}

## Task
Provide a comprehensive health assessment with:
1. SUMMARY: 2-3 sentences about overall schema health
2. GRADE: A (excellent), B (good), C (fair), D (poor), F (critical)
3. TOP RECOMMENDATIONS: 3-5 prioritized actionable recommendations

Respond in JSON format:
{{
  "summary": "...",
  "grade": "B",
  "recommendations": ["...", "...", "..."],
  "additional_issues": [
    {{"title": "...", "description": "...", "severity": "warning", "category": "normalization"}}
  ]
}}"""


class StructuralAnalyzer:
    """
    Deterministic analyzer for structural schema issues.
    No LLM calls - pure heuristic analysis.
    """

    def find_missing_primary_keys(self, schema: Dict[str, Any]) -> List[str]:
        """Find tables without primary keys."""
        missing_pk = []
        for table_name, table_info in schema.get("tables", {}).items():
            pks = table_info.get("primary_keys", [])
            if not pks:
                missing_pk.append(table_name)
        return missing_pk

    def find_orphaned_foreign_keys(self, schema: Dict[str, Any]) -> List[Dict]:
        """Find foreign keys referencing non-existent tables."""
        orphans = []
        table_names = set(schema.get("tables", {}).keys())

        for table_name, table_info in schema.get("tables", {}).items():
            for fk in table_info.get("foreign_keys", []):
                referred = fk.get("referred_table", "")
                if referred and referred not in table_names:
                    orphans.append({
                        "table": table_name,
                        "column": fk.get("column"),
                        "references": referred,
                    })
        return orphans

    def detect_circular_references(self, schema: Dict[str, Any]) -> List[List[str]]:
        """Detect circular FK relationships between tables."""
        # Build adjacency graph
        graph: Dict[str, Set[str]] = defaultdict(set)
        for table_name, table_info in schema.get("tables", {}).items():
            for fk in table_info.get("foreign_keys", []):
                referred = fk.get("referred_table", "")
                if referred:
                    graph[table_name].add(referred)

        # DFS to find cycles
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for table in graph:
            if table not in visited:
                dfs(table, [])

        return cycles

    def find_wide_tables(self, schema: Dict[str, Any], threshold: int = 30) -> List[Dict]:
        """Find tables with too many columns (may indicate poor normalization)."""
        wide = []
        for table_name, table_info in schema.get("tables", {}).items():
            col_count = len(table_info.get("columns", []))
            if col_count > threshold:
                wide.append({
                    "table": table_name,
                    "column_count": col_count,
                    "threshold": threshold,
                })
        return wide

    def find_naming_issues(self, schema: Dict[str, Any]) -> List[Dict]:
        """Find naming convention issues."""
        issues = []

        # Check for mixed naming conventions (snake_case vs camelCase)
        snake_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        camel_pattern = re.compile(r'^[a-z][a-zA-Z0-9]*$')

        for table_name, table_info in schema.get("tables", {}).items():
            # Check table name
            if not snake_pattern.match(table_name) and not camel_pattern.match(table_name):
                issues.append({
                    "type": "table_naming",
                    "object": table_name,
                    "issue": "Table name doesn't follow common conventions",
                })

            # Check for reserved words in column names
            reserved_words = {'select', 'from', 'where', 'order', 'group', 'by', 'join',
                             'table', 'index', 'key', 'primary', 'foreign', 'user', 'date'}

            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                if col_name in reserved_words:
                    issues.append({
                        "type": "reserved_word",
                        "object": f"{table_name}.{col['name']}",
                        "issue": f"Column name '{col['name']}' is a SQL reserved word",
                    })

        return issues

    def find_missing_not_null(self, schema: Dict[str, Any]) -> List[Dict]:
        """Find columns that should probably be NOT NULL."""
        issues = []

        # Columns that typically should be NOT NULL
        should_be_not_null = {'id', 'created_at', 'updated_at', 'name', 'email', 'status', 'type'}

        for table_name, table_info in schema.get("tables", {}).items():
            pks = set(table_info.get("primary_keys", []))

            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                is_nullable = col.get("nullable", True)

                if is_nullable and col_name in should_be_not_null and col_name not in pks:
                    issues.append({
                        "table": table_name,
                        "column": col["name"],
                        "issue": f"Column '{col['name']}' is nullable but typically should be NOT NULL",
                    })

        return issues


class IndexAnalyzer:
    """
    Deterministic analyzer for index suggestions based on query patterns.
    """

    def __init__(self, schema: Dict[str, Any], query_patterns: Dict[str, Any]):
        """
        Initialize with schema and query pattern data.

        Args:
            schema: Schema dictionary from SchemaInspector
            query_patterns: Pattern data from QueryPatternAnalyzer
        """
        self.schema = schema
        self.patterns = query_patterns
        self.existing_indexes = self._collect_existing_indexes()

    def _collect_existing_indexes(self) -> Dict[str, Set[Tuple[str, ...]]]:
        """Collect existing indexes by table."""
        indexes: Dict[str, Set[Tuple[str, ...]]] = defaultdict(set)

        for table_name, table_info in self.schema.get("tables", {}).items():
            # Add PK as an index
            pks = table_info.get("primary_keys", [])
            if pks:
                indexes[table_name].add(tuple(pks))

            # Add explicit indexes
            for idx in table_info.get("indexes", []):
                cols = tuple(idx.get("columns", []))
                if cols:
                    indexes[table_name].add(cols)

        return indexes

    def _index_exists(self, table: str, columns: List[str]) -> bool:
        """Check if an index covering these columns already exists."""
        col_tuple = tuple(columns)
        existing = self.existing_indexes.get(table, set())

        # Check if exact match exists
        if col_tuple in existing:
            return True

        # Check if a covering index exists (prefix match)
        for idx_cols in existing:
            if len(idx_cols) >= len(col_tuple):
                if idx_cols[:len(col_tuple)] == col_tuple:
                    return True

        return False

    def analyze_where_clauses(self, queries: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Analyze WHERE clause columns from queries.

        Returns: Dict[table_name, Dict[column_name, count]]
        """
        where_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Simple pattern to extract WHERE conditions
        where_pattern = re.compile(
            r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)',
            re.IGNORECASE | re.DOTALL
        )
        column_pattern = re.compile(
            r'(\w+)\.(\w+)\s*(?:=|<|>|<=|>=|!=|<>|LIKE|IN|BETWEEN)',
            re.IGNORECASE
        )

        for sql in queries:
            where_match = where_pattern.search(sql)
            if where_match:
                where_clause = where_match.group(1)
                for match in column_pattern.finditer(where_clause):
                    table = match.group(1).lower()
                    column = match.group(2).lower()
                    where_usage[table][column] += 1

        return dict(where_usage)

    def analyze_join_columns(self, queries: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Analyze JOIN clause columns from queries.

        Returns: Dict[table_name, Dict[column_name, count]]
        """
        join_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Pattern to extract JOIN conditions
        join_pattern = re.compile(
            r'JOIN\s+(\w+)\s+(?:\w+\s+)?ON\s+(.+?)(?:JOIN|WHERE|ORDER|GROUP|$)',
            re.IGNORECASE | re.DOTALL
        )
        column_pattern = re.compile(
            r'(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)',
            re.IGNORECASE
        )

        for sql in queries:
            for join_match in join_pattern.finditer(sql):
                on_clause = join_match.group(2)
                for col_match in column_pattern.finditer(on_clause):
                    table1, col1 = col_match.group(1).lower(), col_match.group(2).lower()
                    table2, col2 = col_match.group(3).lower(), col_match.group(4).lower()
                    join_usage[table1][col1] += 1
                    join_usage[table2][col2] += 1

        return dict(join_usage)

    def suggest_indexes(self, min_query_count: int = 3) -> List[IndexSuggestion]:
        """
        Suggest indexes based on query patterns.

        Args:
            min_query_count: Minimum queries using a column to suggest index

        Returns:
            List of index suggestions
        """
        suggestions = []

        # Get query data from patterns
        queries = self.patterns.get("queries", [])
        if not queries:
            return suggestions

        # Analyze WHERE and JOIN usage
        where_usage = self.analyze_where_clauses(queries)
        join_usage = self.analyze_join_columns(queries)

        # Combine usage data
        combined_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for table, cols in where_usage.items():
            for col, count in cols.items():
                combined_usage[table][col] += count

        for table, cols in join_usage.items():
            for col, count in cols.items():
                combined_usage[table][col] += count * 2  # JOIN columns more important

        # Generate suggestions for frequently used columns
        for table, cols in combined_usage.items():
            for col, count in cols.items():
                if count < min_query_count:
                    continue

                # Check if index already exists
                if self._index_exists(table, [col]):
                    continue

                # Create suggestion
                suggestion = IndexSuggestion(
                    table_name=table,
                    columns=[col],
                    index_type="btree",
                    reason=f"Used in {count} queries (WHERE/JOIN clauses)",
                    estimated_impact="high" if count > 10 else "medium",
                    create_sql=f"CREATE INDEX idx_{table}_{col} ON {table} ({col});",
                    query_count_benefiting=count,
                )
                suggestions.append(suggestion)

        # Sort by impact (query count)
        suggestions.sort(key=lambda s: s.query_count_benefiting, reverse=True)

        return suggestions[:20]  # Limit to top 20

    def suggest_composite_indexes(self, min_co_occurrence: int = 3) -> List[IndexSuggestion]:
        """
        Suggest composite indexes for columns frequently used together.

        Returns:
            List of composite index suggestions
        """
        suggestions = []

        queries = self.patterns.get("queries", [])
        if not queries:
            return suggestions

        # Track column pairs used together in WHERE/JOIN
        column_pairs: Dict[str, Counter] = defaultdict(Counter)

        where_pattern = re.compile(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', re.I | re.DOTALL)
        and_pattern = re.compile(r'(\w+)\.(\w+)\s*(?:=|<|>|LIKE|IN)', re.I)

        for sql in queries:
            where_match = where_pattern.search(sql)
            if where_match:
                where_clause = where_match.group(1)
                columns_in_where = []

                for match in and_pattern.finditer(where_clause):
                    table = match.group(1).lower()
                    col = match.group(2).lower()
                    columns_in_where.append((table, col))

                # Find pairs from same table
                table_cols: Dict[str, List[str]] = defaultdict(list)
                for table, col in columns_in_where:
                    table_cols[table].append(col)

                for table, cols in table_cols.items():
                    if len(cols) >= 2:
                        # Create sorted pair for consistency
                        pair = tuple(sorted(cols[:2]))
                        column_pairs[table][pair] += 1

        # Generate suggestions for frequent pairs
        for table, pairs in column_pairs.items():
            for (col1, col2), count in pairs.most_common(5):
                if count < min_co_occurrence:
                    continue

                # Check if composite index already exists
                if self._index_exists(table, [col1, col2]):
                    continue

                suggestion = IndexSuggestion(
                    table_name=table,
                    columns=[col1, col2],
                    index_type="btree",
                    reason=f"Columns used together in {count} queries",
                    estimated_impact="high" if count > 5 else "medium",
                    create_sql=f"CREATE INDEX idx_{table}_{col1}_{col2} ON {table} ({col1}, {col2});",
                    query_count_benefiting=count,
                )
                suggestions.append(suggestion)

        return suggestions


class SchemaHealthAnalyzer:
    """
    LLM-enhanced schema health analyzer.

    Combines deterministic analysis (StructuralAnalyzer, IndexAnalyzer)
    with LLM-generated insights and recommendations.
    """

    def __init__(
        self,
        ollama_client=None,
        model_router=None,
        timeout_seconds: float = 30.0,
        model: Optional[str] = None,
    ):
        """
        Initialize the schema health analyzer.

        Args:
            ollama_client: OllamaClient instance for LLM calls
            model_router: Optional ModelRouter for per-task model selection
            timeout_seconds: Timeout for LLM calls
            model: Optional model override
        """
        self.client = ollama_client
        self.router = model_router
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.schema_inspector = SchemaInspector()
        self.pattern_analyzer = QueryPatternAnalyzer()
        self.structural_analyzer = StructuralAnalyzer()

    async def analyze_schema_health(
        self,
        db: AsyncSession,
        connection_id: int,
        include_patterns: bool = True,
        timeout: Optional[float] = None,
    ) -> SchemaHealthReport:
        """
        Perform complete schema health analysis.

        Args:
            db: Database session
            connection_id: Connection to analyze
            include_patterns: Whether to include query pattern analysis
            timeout: Optional timeout override

        Returns:
            SchemaHealthReport with complete analysis
        """
        effective_timeout = timeout or self.timeout_seconds

        # Step 1: Get connection info
        from sqlalchemy import select
        result = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            return SchemaHealthReport(
                connection_id=connection_id,
                database_name="Unknown",
                grade=HealthGrade.CRITICAL.value,
                score=0,
                summary="Connection not found",
            )

        # Step 2: Get schema from connection
        try:
            from src.core.user_db_connector import UserDatabaseConnector

            async with UserDatabaseConnector.get_user_db_session(connection) as conn_session:
                schema = await self.schema_inspector.get_full_schema(
                    conn_session, include_samples=False
                )
        except Exception as e:
            logger.error(f"Failed to get schema for connection {connection_id}: {e}")
            return SchemaHealthReport(
                connection_id=connection_id,
                database_name=connection.name,
                grade=HealthGrade.CRITICAL.value,
                score=0,
                summary=f"Failed to analyze schema: {str(e)}",
            )

        # Step 3: Run deterministic analysis
        report = SchemaHealthReport(
            connection_id=connection_id,
            database_name=connection.name,
            table_count=len(schema.get("tables", {})),
        )

        # Structural analysis
        structural_issues = self._run_structural_analysis(schema)
        report.anti_patterns.extend(structural_issues)

        # Normalization analysis
        normalization_issues = self._analyze_normalization(schema)
        report.normalization_issues.extend(normalization_issues)

        # Step 4: Index analysis with query patterns
        if include_patterns:
            pattern_data = await self._get_pattern_data(db, connection_id)
            index_analyzer = IndexAnalyzer(schema, pattern_data)

            # Get index suggestions
            single_suggestions = index_analyzer.suggest_indexes()
            composite_suggestions = index_analyzer.suggest_composite_indexes()
            report.index_suggestions.extend(single_suggestions)
            report.index_suggestions.extend(composite_suggestions)
        else:
            pattern_data = {}

        # Step 5: Build table summaries
        report.table_summaries = self._build_table_summaries(schema, report)

        # Step 6: Calculate score and grade
        report = self._calculate_score(report)

        # Step 7: LLM enhancement (if available)
        if self.client:
            try:
                llm_result = await self._generate_llm_insights(
                    schema, pattern_data, report, effective_timeout
                )
                if llm_result:
                    report.summary = llm_result.get("summary", report.summary)
                    report.recommendations = llm_result.get("recommendations", [])

                    # Add any additional issues found by LLM
                    for issue_data in llm_result.get("additional_issues", []):
                        issue = SchemaIssue(
                            category=issue_data.get("category", "structure"),
                            severity=issue_data.get("severity", "warning"),
                            title=issue_data.get("title", ""),
                            description=issue_data.get("description", ""),
                        )
                        report.anti_patterns.append(issue)

                    # Override grade if LLM suggests different
                    if llm_result.get("grade"):
                        report.grade = llm_result["grade"]

                    report.llm_used = True
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")
                # Continue with deterministic results

        # Ensure we have a summary
        if not report.summary:
            report.summary = self._generate_fallback_summary(report)

        # Update issue counts
        report.total_issues = len(report.anti_patterns) + len(report.normalization_issues)
        report.critical_issues = sum(
            1 for i in report.anti_patterns if i.severity == IssueSeverity.CRITICAL.value
        )

        return report

    def _run_structural_analysis(self, schema: Dict[str, Any]) -> List[SchemaIssue]:
        """Run all structural analysis checks."""
        issues = []

        # Missing primary keys
        missing_pks = self.structural_analyzer.find_missing_primary_keys(schema)
        for table in missing_pks:
            issues.append(SchemaIssue(
                category=IssueCategory.INTEGRITY.value,
                severity=IssueSeverity.ERROR.value,
                title="Missing Primary Key",
                description=f"Table '{table}' has no primary key defined",
                affected_objects=[table],
                recommendation="Add a primary key to ensure data integrity",
            ))

        # Orphaned foreign keys
        orphans = self.structural_analyzer.find_orphaned_foreign_keys(schema)
        for orphan in orphans:
            issues.append(SchemaIssue(
                category=IssueCategory.INTEGRITY.value,
                severity=IssueSeverity.WARNING.value,
                title="Orphaned Foreign Key",
                description=f"FK {orphan['table']}.{orphan['column']} references non-existent table '{orphan['references']}'",
                affected_objects=[orphan["table"]],
                recommendation="Remove the orphaned constraint or create the referenced table",
            ))

        # Circular references
        cycles = self.structural_analyzer.detect_circular_references(schema)
        for cycle in cycles:
            issues.append(SchemaIssue(
                category=IssueCategory.STRUCTURE.value,
                severity=IssueSeverity.WARNING.value,
                title="Circular Reference Detected",
                description=f"Circular FK chain: {' -> '.join(cycle)}",
                affected_objects=cycle,
                recommendation="Review and potentially refactor to avoid circular dependencies",
            ))

        # Wide tables
        wide_tables = self.structural_analyzer.find_wide_tables(schema)
        for wide in wide_tables:
            issues.append(SchemaIssue(
                category=IssueCategory.NORMALIZATION.value,
                severity=IssueSeverity.INFO.value,
                title="Wide Table",
                description=f"Table '{wide['table']}' has {wide['column_count']} columns (threshold: {wide['threshold']})",
                affected_objects=[wide["table"]],
                recommendation="Consider splitting into related tables for better normalization",
            ))

        # Naming issues
        naming_issues = self.structural_analyzer.find_naming_issues(schema)
        for naming in naming_issues:
            issues.append(SchemaIssue(
                category=IssueCategory.NAMING.value,
                severity=IssueSeverity.INFO.value,
                title="Naming Convention Issue",
                description=naming["issue"],
                affected_objects=[naming["object"]],
                recommendation="Follow consistent naming conventions",
            ))

        return issues

    def _analyze_normalization(self, schema: Dict[str, Any]) -> List[NormalizationIssue]:
        """Analyze schema for normalization issues."""
        issues = []

        for table_name, table_info in schema.get("tables", {}).items():
            columns = table_info.get("columns", [])

            # Check for potential 1NF violations (repeated groups)
            # Look for numbered columns like address1, address2, phone1, phone2
            numbered_cols = defaultdict(list)
            for col in columns:
                col_name = col.get("name", "")
                match = re.match(r'^(.+?)(\d+)$', col_name)
                if match:
                    base_name = match.group(1).rstrip('_')
                    numbered_cols[base_name].append(col_name)

            for base, cols in numbered_cols.items():
                if len(cols) >= 2:
                    issues.append(NormalizationIssue(
                        table_name=table_name,
                        issue_type="1NF",
                        description=f"Repeated column group detected: {', '.join(cols)}",
                        affected_columns=cols,
                        recommendation=f"Consider creating a separate table for {base} entries",
                    ))

            # Check for potential denormalization (embedded data)
            # Look for columns that might contain JSON or delimited data
            for col in columns:
                col_name = col.get("name", "").lower()
                col_type = str(col.get("type", "")).lower()

                if 'json' in col_type or col_type == 'text':
                    if any(kw in col_name for kw in ['data', 'metadata', 'properties', 'attributes', 'config']):
                        issues.append(NormalizationIssue(
                            table_name=table_name,
                            issue_type="1NF",
                            description=f"Column '{col['name']}' may contain structured data",
                            affected_columns=[col["name"]],
                            recommendation="Consider normalizing embedded data into related tables",
                        ))

        return issues

    async def _get_pattern_data(
        self, db: AsyncSession, connection_id: int
    ) -> Dict[str, Any]:
        """Get query pattern data for index analysis."""
        try:
            # Get recent queries for this connection
            from sqlalchemy import select

            result = await db.execute(
                select(QueryHistory)
                .where(
                    QueryHistory.connection_id == connection_id,
                    QueryHistory.executed == True,
                    QueryHistory.generated_sql.isnot(None),
                )
                .order_by(QueryHistory.id.desc())
                .limit(200)
            )
            queries = result.scalars().all()

            return {
                "queries": [q.generated_sql for q in queries if q.generated_sql],
                "query_count": len(queries),
            }
        except Exception as e:
            logger.warning(f"Failed to get pattern data: {e}")
            return {"queries": [], "query_count": 0}

    def _build_table_summaries(
        self, schema: Dict[str, Any], report: SchemaHealthReport
    ) -> List[TableHealthSummary]:
        """Build per-table health summaries."""
        summaries = []

        for table_name, table_info in schema.get("tables", {}).items():
            summary = TableHealthSummary(
                table_name=table_name,
                column_count=len(table_info.get("columns", [])),
                has_primary_key=len(table_info.get("primary_keys", [])) > 0,
                foreign_key_count=len(table_info.get("foreign_keys", [])),
                index_count=len(table_info.get("indexes", [])),
            )

            # Add issues for this table
            summary.issues = [
                i for i in report.anti_patterns
                if table_name in i.affected_objects
            ]

            # Add index suggestions for this table
            summary.suggestions = [
                s for s in report.index_suggestions
                if s.table_name == table_name
            ]

            summaries.append(summary)

        return summaries

    def _calculate_score(self, report: SchemaHealthReport) -> SchemaHealthReport:
        """Calculate overall health score and grade."""
        score = 100

        # Deduct for issues
        for issue in report.anti_patterns:
            if issue.severity == IssueSeverity.CRITICAL.value:
                score -= 20
            elif issue.severity == IssueSeverity.ERROR.value:
                score -= 10
            elif issue.severity == IssueSeverity.WARNING.value:
                score -= 5
            else:  # INFO
                score -= 1

        # Deduct for normalization issues
        for issue in report.normalization_issues:
            score -= 3

        # Bonus for index suggestions implemented (none initially)
        # Tables with missing PKs are a big issue
        missing_pk_count = sum(
            1 for s in report.table_summaries if not s.has_primary_key
        )
        score -= missing_pk_count * 10

        # Clamp score
        score = max(0, min(100, score))
        report.score = score

        # Determine grade
        if score >= 90:
            report.grade = HealthGrade.EXCELLENT.value
        elif score >= 75:
            report.grade = HealthGrade.GOOD.value
        elif score >= 60:
            report.grade = HealthGrade.FAIR.value
        elif score >= 40:
            report.grade = HealthGrade.POOR.value
        else:
            report.grade = HealthGrade.CRITICAL.value

        return report

    async def _generate_llm_insights(
        self,
        schema: Dict[str, Any],
        pattern_data: Dict[str, Any],
        report: SchemaHealthReport,
        timeout: float,
    ) -> Optional[Dict]:
        """Generate LLM-enhanced insights."""
        if not self.client:
            return None

        # Format schema for prompt
        schema_formatted = self.schema_inspector.format_schema_for_llm(schema)

        # Format detected issues
        issues_formatted = "\n".join([
            f"- [{i.severity}] {i.title}: {i.description}"
            for i in report.anti_patterns[:10]
        ]) or "No major issues detected"

        # Format index suggestions
        suggestions_formatted = "\n".join([
            f"- {s.table_name}({', '.join(s.columns)}): {s.reason}"
            for s in report.index_suggestions[:10]
        ]) or "No index suggestions"

        prompt = SCHEMA_HEALTH_PROMPT.format(
            database_name=report.database_name,
            table_count=report.table_count,
            total_columns=schema.get("summary", {}).get("total_columns", 0),
            schema_formatted=schema_formatted[:4000],  # Limit size
            most_used_tables="(from query patterns)",
            join_patterns="(from query patterns)",
            bottlenecks="(from query patterns)",
            detected_issues=issues_formatted,
            index_suggestions=suggestions_formatted,
        )

        try:
            model = self._get_model()
            response = await asyncio.wait_for(
                self.client.generate(prompt=prompt, model=model, temperature=0.2),
                timeout=timeout,
            )

            json_str = extract_json_object(response)
            if json_str:
                return json.loads(json_str)
        except asyncio.TimeoutError:
            logger.warning(f"LLM insights timed out after {timeout}s")
        except Exception as e:
            logger.warning(f"LLM insights failed: {e}")

        return None

    def _generate_fallback_summary(self, report: SchemaHealthReport) -> str:
        """Generate fallback summary without LLM."""
        issue_count = len(report.anti_patterns)
        suggestion_count = len(report.index_suggestions)

        if report.score >= 90:
            return f"Schema health is excellent with {report.table_count} tables. {issue_count} minor issues detected."
        elif report.score >= 75:
            return f"Schema health is good with {report.table_count} tables. {issue_count} issues and {suggestion_count} index suggestions."
        elif report.score >= 60:
            return f"Schema health is fair. Found {issue_count} issues that should be addressed. {suggestion_count} index optimizations recommended."
        else:
            return f"Schema health needs attention. {issue_count} issues detected, including structural problems. Review recommendations."

    def _get_model(self) -> Optional[str]:
        """Get model to use for generation."""
        if self.model:
            return self.model
        if self.router:
            from src.llm.model_router import TaskType
            return self.router.get_model_for_task(TaskType.SCHEMA_HEALTH)
        return None

async def get_schema_health_analyzer(
    db: Optional[AsyncSession] = None,
    model: Optional[str] = None,
) -> SchemaHealthAnalyzer:
    """
    Factory function to create a SchemaHealthAnalyzer instance.

    Args:
        db: Optional database session (for loading settings)
        model: Optional model override

    Returns:
        Configured SchemaHealthAnalyzer instance
    """
    from src.llm.ollama_client import get_ollama_client
    from src.llm.model_router import get_model_router, TaskType

    client = get_ollama_client()
    router = await get_model_router(db) if db else None

    # Get timeout from router or use default
    timeout = 30.0
    if router:
        timeout = router.get_timeout_for_task(TaskType.SCHEMA_HEALTH)

    # Use provided model or get from router
    effective_model = model
    if not effective_model and router:
        effective_model = router.get_model_for_task(TaskType.SCHEMA_HEALTH)

    return SchemaHealthAnalyzer(
        ollama_client=client,
        model_router=router,
        timeout_seconds=timeout,
        model=effective_model,
    )
