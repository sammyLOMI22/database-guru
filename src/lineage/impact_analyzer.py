"""
Impact Analyzer

Analyzes the impact of schema changes (table/column modifications) by scanning
query history to find queries that reference the affected objects.

Provides risk assessment based on how many historical queries would be affected.
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QueryHistory

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level for a schema change impact."""
    LOW = "low"        # <5 affected queries
    MEDIUM = "medium"  # 5-20 affected queries
    HIGH = "high"      # >20 affected queries


class ImpactType(Enum):
    """How the query references the changed object."""
    SELECT = "select"    # Column/table in SELECT clause
    FILTER = "filter"    # Column/table in WHERE clause
    JOIN = "join"        # Column/table in JOIN clause
    GROUP = "group"      # Column in GROUP BY
    ORDER = "order"      # Column in ORDER BY


@dataclass
class ImpactedQuery:
    """A query affected by a schema change."""
    query_id: int
    natural_language_query: str
    generated_sql: str
    impact_type: str
    risk_level: str

    def to_dict(self):
        return {
            "query_id": self.query_id,
            "natural_language_query": self.natural_language_query,
            "generated_sql": self.generated_sql,
            "impact_type": self.impact_type,
            "risk_level": self.risk_level,
        }


@dataclass
class ImpactAnalysis:
    """Complete impact analysis for a schema change."""
    changed_object: str
    object_type: str  # "table" or "column"
    impacted_queries: List[ImpactedQuery] = field(default_factory=list)
    total_affected: int = 0
    risk_level: str = RiskLevel.LOW.value
    risk_counts: dict = field(default_factory=lambda: {"low": 0, "medium": 0, "high": 0})
    summary: str = ""

    def to_dict(self):
        return {
            "changed_object": self.changed_object,
            "object_type": self.object_type,
            "impacted_queries": [q.to_dict() for q in self.impacted_queries],
            "total_affected": self.total_affected,
            "risk_level": self.risk_level,
            "risk_counts": self.risk_counts,
            "summary": self.summary,
        }


class ImpactAnalyzer:
    """
    Analyzes the impact of schema changes on existing queries.

    Scans query_history for references to specified tables/columns
    and assesses the risk level of changes.
    """

    async def analyze_table_impact(
        self, db: AsyncSession, table_name: str, limit: int = 50
    ) -> ImpactAnalysis:
        """
        Analyze impact of changing/removing a table.

        Args:
            db: Database session
            table_name: Table being changed
            limit: Maximum queries to return

        Returns:
            ImpactAnalysis with affected queries and risk assessment
        """
        analysis = ImpactAnalysis(
            changed_object=table_name,
            object_type="table",
        )

        queries = await self._scan_query_history(db, table_name, None, limit)

        for row in queries:
            impact_type = self._detect_impact_type(row.generated_sql, table_name, None)
            impacted = ImpactedQuery(
                query_id=row.id,
                natural_language_query=row.natural_language_query,
                generated_sql=row.generated_sql,
                impact_type=impact_type,
                risk_level=self._assess_individual_risk(impact_type),
            )
            analysis.impacted_queries.append(impacted)

        analysis.total_affected = len(analysis.impacted_queries)
        analysis.risk_level = self._assess_risk(analysis.total_affected)
        analysis.risk_counts = self._count_risks(analysis.impacted_queries)
        analysis.summary = self._build_summary(analysis)

        return analysis

    async def analyze_column_impact(
        self, db: AsyncSession, table_name: str, column_name: str, limit: int = 50
    ) -> ImpactAnalysis:
        """
        Analyze impact of changing/removing a column.

        Args:
            db: Database session
            table_name: Table containing the column
            column_name: Column being changed
            limit: Maximum queries to return

        Returns:
            ImpactAnalysis with affected queries and risk assessment
        """
        analysis = ImpactAnalysis(
            changed_object=f"{table_name}.{column_name}",
            object_type="column",
        )

        queries = await self._scan_query_history(db, table_name, column_name, limit)

        for row in queries:
            impact_type = self._detect_impact_type(row.generated_sql, table_name, column_name)
            impacted = ImpactedQuery(
                query_id=row.id,
                natural_language_query=row.natural_language_query,
                generated_sql=row.generated_sql,
                impact_type=impact_type,
                risk_level=self._assess_individual_risk(impact_type),
            )
            analysis.impacted_queries.append(impacted)

        analysis.total_affected = len(analysis.impacted_queries)
        analysis.risk_level = self._assess_risk(analysis.total_affected)
        analysis.risk_counts = self._count_risks(analysis.impacted_queries)
        analysis.summary = self._build_summary(analysis)

        return analysis

    async def get_queries_for_table(
        self, db: AsyncSession, table_name: str, limit: int = 50
    ) -> List[ImpactedQuery]:
        """Get all queries that reference a specific table."""
        queries = await self._scan_query_history(db, table_name, None, limit)
        results = []
        for row in queries:
            impact_type = self._detect_impact_type(row.generated_sql, table_name, None)
            results.append(ImpactedQuery(
                query_id=row.id,
                natural_language_query=row.natural_language_query,
                generated_sql=row.generated_sql,
                impact_type=impact_type,
                risk_level="low",
            ))
        return results

    async def get_lineage_stats(self, db: AsyncSession) -> dict:
        """Get basic lineage statistics from query history."""
        result = await db.execute(
            select(QueryHistory).where(QueryHistory.executed == True)
        )
        all_queries = result.scalars().all()

        tables_referenced = set()
        for q in all_queries:
            if q.generated_sql:
                # Simple extraction of table names from FROM/JOIN
                sql_upper = q.generated_sql.upper()
                for keyword in ['FROM', 'JOIN']:
                    idx = sql_upper.find(keyword)
                    while idx != -1:
                        # Extract word after keyword
                        start = idx + len(keyword)
                        remaining = q.generated_sql[start:].strip()
                        table_match = remaining.split()[0] if remaining.split() else None
                        if table_match:
                            clean = table_match.strip('(),;').lower()
                            if clean and not clean.upper() in ('SELECT', 'WHERE', 'ON', '('):
                                tables_referenced.add(clean)
                        idx = sql_upper.find(keyword, start)

        return {
            "total_queries": len(all_queries),
            "unique_tables_referenced": len(tables_referenced),
            "tables": sorted(tables_referenced)[:50],
        }

    async def _scan_query_history(
        self,
        db: AsyncSession,
        table_name: str,
        column_name: Optional[str],
        limit: int,
    ) -> list:
        """
        Scan query history for references to a table/column.

        Uses SQL LIKE queries against generated_sql field.
        """
        conditions = []

        # Table reference patterns
        table_patterns = [
            f"%{table_name}%",
        ]

        for pattern in table_patterns:
            conditions.append(QueryHistory.generated_sql.ilike(pattern))

        stmt = (
            select(QueryHistory)
            .where(
                QueryHistory.executed == True,
                or_(*conditions),
            )
            .order_by(QueryHistory.id.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.scalars().all()

        # If column specified, further filter in Python for accuracy
        if column_name:
            filtered = []
            for row in rows:
                sql_lower = row.generated_sql.lower()
                if column_name.lower() in sql_lower:
                    filtered.append(row)
            return filtered

        return rows

    def _detect_impact_type(
        self, sql: str, table_name: str, column_name: Optional[str]
    ) -> str:
        """Detect how the object is referenced in the query."""
        sql_upper = sql.upper()
        target = (column_name or table_name).upper()

        # Check position relative to SQL clauses
        select_idx = sql_upper.find('SELECT')
        from_idx = sql_upper.find('FROM')
        where_idx = sql_upper.find('WHERE')
        join_idx = sql_upper.find('JOIN')
        group_idx = sql_upper.find('GROUP BY')
        order_idx = sql_upper.find('ORDER BY')

        target_idx = sql_upper.find(target)
        if target_idx == -1:
            return ImpactType.SELECT.value

        if join_idx != -1 and target_idx > join_idx and (where_idx == -1 or target_idx < where_idx):
            return ImpactType.JOIN.value
        if where_idx != -1 and target_idx > where_idx:
            if group_idx != -1 and target_idx > group_idx:
                return ImpactType.GROUP.value
            if order_idx != -1 and target_idx > order_idx:
                return ImpactType.ORDER.value
            return ImpactType.FILTER.value
        if group_idx != -1 and target_idx > group_idx:
            return ImpactType.GROUP.value
        if order_idx != -1 and target_idx > order_idx:
            return ImpactType.ORDER.value

        return ImpactType.SELECT.value

    def _assess_risk(self, affected_count: int) -> str:
        """Assess overall risk based on number of affected queries."""
        if affected_count > 20:
            return RiskLevel.HIGH.value
        elif affected_count >= 5:
            return RiskLevel.MEDIUM.value
        return RiskLevel.LOW.value

    def _assess_individual_risk(self, impact_type: str) -> str:
        """Assess risk for an individual query based on impact type."""
        if impact_type in (ImpactType.JOIN.value, ImpactType.FILTER.value):
            return RiskLevel.MEDIUM.value
        return RiskLevel.LOW.value

    def _count_risks(self, queries: List[ImpactedQuery]) -> dict:
        """Count queries by risk level."""
        counts = {"low": 0, "medium": 0, "high": 0}
        for q in queries:
            if q.risk_level in counts:
                counts[q.risk_level] += 1
        return counts

    def _build_summary(self, analysis: ImpactAnalysis) -> str:
        """Build a human-readable summary of the impact."""
        if analysis.total_affected == 0:
            return f"No queries reference {analysis.changed_object}. Safe to modify."

        risk_text = {
            "low": "Low risk",
            "medium": "Medium risk",
            "high": "High risk - review carefully",
        }

        return (
            f"{risk_text[analysis.risk_level]}: {analysis.total_affected} "
            f"{'query references' if analysis.total_affected == 1 else 'queries reference'} "
            f"{analysis.changed_object}."
        )
