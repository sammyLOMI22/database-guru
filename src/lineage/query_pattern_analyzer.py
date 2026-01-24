"""
Query Pattern Analyzer - Phase 11.5

Analyzes query history to identify table usage patterns, common JOIN combinations,
and performance bottlenecks for heatmap visualization.
"""

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QueryHistory
from src.lineage.sql_lineage_parser import SQLLineageParser

logger = logging.getLogger(__name__)

# Maximum queries to analyze (performance cap)
MAX_QUERIES = 2000


@dataclass
class TableUsageEntry:
    """Usage details for a single table."""
    table_name: str
    query_count: int
    join_count: int = 0
    avg_execution_time_ms: Optional[float] = None
    last_used_at: Optional[datetime] = None


@dataclass
class JoinPattern:
    """A frequently observed JOIN between two tables."""
    table_a: str
    table_b: str
    join_count: int
    sample_sql: str = ""
    avg_execution_time_ms: Optional[float] = None


@dataclass
class PerformanceBottleneck:
    """A table with high usage AND high avg execution time."""
    table_name: str
    query_count: int
    avg_execution_time_ms: float
    max_execution_time_ms: float
    bottleneck_score: float  # Normalized 0-1


@dataclass
class HeatmapData:
    """Complete heatmap response data."""
    table_usage: List[TableUsageEntry] = field(default_factory=list)
    join_patterns: List[JoinPattern] = field(default_factory=list)
    bottlenecks: List[PerformanceBottleneck] = field(default_factory=list)
    time_range_days: Optional[int] = None
    total_queries_analyzed: int = 0
    connection_id: Optional[int] = None


class QueryPatternAnalyzer:
    """
    Analyzes query patterns from history to identify usage frequencies,
    common join patterns, and performance bottlenecks.

    Reuses SQLLineageParser for SQL table extraction.
    """

    def __init__(self):
        self._parser = SQLLineageParser()

    async def get_table_usage_frequency(
        self,
        db: AsyncSession,
        connection_id: Optional[int] = None,
        time_range_days: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Count how often each table appears in query history.

        Returns dict mapping table_name -> query_count.
        """
        queries = await self._fetch_queries(db, connection_id, time_range_days)
        table_counts: Counter = Counter()

        for query in queries:
            tables = self._extract_tables(query.generated_sql)
            for table in tables:
                table_counts[table] += 1

        return dict(table_counts.most_common())

    async def get_common_join_patterns(
        self,
        db: AsyncSession,
        connection_id: Optional[int] = None,
        time_range_days: Optional[int] = None,
        limit: int = 20,
    ) -> List[JoinPattern]:
        """
        Find table pairs that are frequently JOINed together.

        Extracts table pairs from JOIN clauses, counts co-occurrences,
        and returns ranked list.
        """
        queries = await self._fetch_queries(db, connection_id, time_range_days)
        join_counts: Counter = Counter()
        join_samples: Dict[Tuple[str, str], str] = {}
        join_times: Dict[Tuple[str, str], List[float]] = defaultdict(list)

        for query in queries:
            pairs = self._extract_join_pairs(query.generated_sql)
            for pair in pairs:
                join_counts[pair] += 1
                if pair not in join_samples:
                    join_samples[pair] = query.generated_sql[:200]
                if query.execution_time_ms is not None:
                    join_times[pair].append(query.execution_time_ms)

        results = []
        for pair, count in join_counts.most_common(limit):
            avg_time = None
            if join_times[pair]:
                avg_time = sum(join_times[pair]) / len(join_times[pair])
            results.append(JoinPattern(
                table_a=pair[0],
                table_b=pair[1],
                join_count=count,
                sample_sql=join_samples.get(pair, ""),
                avg_execution_time_ms=avg_time,
            ))

        return results

    async def identify_bottlenecks(
        self,
        db: AsyncSession,
        connection_id: Optional[int] = None,
        time_range_days: Optional[int] = None,
        min_query_count: int = 3,
    ) -> List[PerformanceBottleneck]:
        """
        Find tables with high frequency AND high avg execution time.

        Bottleneck score = normalized_frequency * normalized_avg_time (0-1).
        Tables with fewer than min_query_count queries are excluded.
        """
        queries = await self._fetch_queries(db, connection_id, time_range_days)

        # Collect per-table execution times
        table_times: Dict[str, List[float]] = defaultdict(list)
        for query in queries:
            if query.execution_time_ms is None:
                continue
            tables = self._extract_tables(query.generated_sql)
            for table in tables:
                table_times[table].append(query.execution_time_ms)

        # Filter by min_query_count
        candidates = {
            table: times
            for table, times in table_times.items()
            if len(times) >= min_query_count
        }

        if not candidates:
            return []

        # Calculate stats
        stats = {}
        for table, times in candidates.items():
            stats[table] = {
                "query_count": len(times),
                "avg_time": sum(times) / len(times),
                "max_time": max(times),
            }

        # Normalize for scoring
        max_count = max(s["query_count"] for s in stats.values())
        max_avg_time = max(s["avg_time"] for s in stats.values())

        if max_count == 0 or max_avg_time == 0:
            return []

        results = []
        for table, s in stats.items():
            score = (s["query_count"] / max_count) * (s["avg_time"] / max_avg_time)
            results.append(PerformanceBottleneck(
                table_name=table,
                query_count=s["query_count"],
                avg_execution_time_ms=round(s["avg_time"], 2),
                max_execution_time_ms=round(s["max_time"], 2),
                bottleneck_score=round(score, 4),
            ))

        # Sort by score descending
        results.sort(key=lambda x: x.bottleneck_score, reverse=True)
        return results

    async def get_heatmap_data(
        self,
        db: AsyncSession,
        connection_id: Optional[int] = None,
        time_range_days: Optional[int] = None,
    ) -> HeatmapData:
        """
        Get comprehensive heatmap data combining usage, joins, and bottlenecks.
        Single call for the frontend heatmap component.
        """
        queries = await self._fetch_queries(db, connection_id, time_range_days)

        if not queries:
            return HeatmapData(
                time_range_days=time_range_days,
                total_queries_analyzed=0,
                connection_id=connection_id,
            )

        # Build all analytics in one pass over queries
        table_counts: Counter = Counter()
        join_counts: Counter = Counter()
        join_samples: Dict[Tuple[str, str], str] = {}
        join_times: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        table_times: Dict[str, List[float]] = defaultdict(list)
        table_last_used: Dict[str, datetime] = {}
        table_join_counts: Counter = Counter()

        for query in queries:
            tables = self._extract_tables(query.generated_sql)
            for table in tables:
                table_counts[table] += 1
                if query.execution_time_ms is not None:
                    table_times[table].append(query.execution_time_ms)
                if query.created_at:
                    if table not in table_last_used or query.created_at > table_last_used[table]:
                        table_last_used[table] = query.created_at

            pairs = self._extract_join_pairs(query.generated_sql)
            for pair in pairs:
                join_counts[pair] += 1
                table_join_counts[pair[0]] += 1
                table_join_counts[pair[1]] += 1
                if pair not in join_samples:
                    join_samples[pair] = query.generated_sql[:200]
                if query.execution_time_ms is not None:
                    join_times[pair].append(query.execution_time_ms)

        # Build table usage entries
        table_usage = []
        for table, count in table_counts.most_common():
            avg_time = None
            if table_times.get(table):
                avg_time = round(sum(table_times[table]) / len(table_times[table]), 2)
            table_usage.append(TableUsageEntry(
                table_name=table,
                query_count=count,
                join_count=table_join_counts.get(table, 0),
                avg_execution_time_ms=avg_time,
                last_used_at=table_last_used.get(table),
            ))

        # Build join patterns
        join_patterns = []
        for pair, count in join_counts.most_common(20):
            avg_time = None
            if join_times[pair]:
                avg_time = round(sum(join_times[pair]) / len(join_times[pair]), 2)
            join_patterns.append(JoinPattern(
                table_a=pair[0],
                table_b=pair[1],
                join_count=count,
                sample_sql=join_samples.get(pair, ""),
                avg_execution_time_ms=avg_time,
            ))

        # Build bottlenecks
        bottlenecks = []
        candidates = {t: times for t, times in table_times.items() if len(times) >= 3}
        if candidates:
            stats = {
                t: {"count": len(times), "avg": sum(times) / len(times), "max": max(times)}
                for t, times in candidates.items()
            }
            max_count = max(s["count"] for s in stats.values())
            max_avg = max(s["avg"] for s in stats.values())
            if max_count > 0 and max_avg > 0:
                for table, s in stats.items():
                    score = (s["count"] / max_count) * (s["avg"] / max_avg)
                    bottlenecks.append(PerformanceBottleneck(
                        table_name=table,
                        query_count=s["count"],
                        avg_execution_time_ms=round(s["avg"], 2),
                        max_execution_time_ms=round(s["max"], 2),
                        bottleneck_score=round(score, 4),
                    ))
                bottlenecks.sort(key=lambda x: x.bottleneck_score, reverse=True)

        return HeatmapData(
            table_usage=table_usage,
            join_patterns=join_patterns,
            bottlenecks=bottlenecks,
            time_range_days=time_range_days,
            total_queries_analyzed=len(queries),
            connection_id=connection_id,
        )

    async def _fetch_queries(
        self,
        db: AsyncSession,
        connection_id: Optional[int],
        time_range_days: Optional[int],
    ) -> list:
        """
        Fetch executed queries from history with optional filters.
        Limited to MAX_QUERIES most recent for performance.
        """
        stmt = select(QueryHistory).where(QueryHistory.executed == True)

        if connection_id is not None:
            stmt = stmt.where(QueryHistory.connection_id == connection_id)

        if time_range_days is not None:
            cutoff = datetime.utcnow() - timedelta(days=time_range_days)
            stmt = stmt.where(QueryHistory.created_at >= cutoff)

        stmt = stmt.order_by(QueryHistory.created_at.desc()).limit(MAX_QUERIES)

        result = await db.execute(stmt)
        return result.scalars().all()

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL using the lineage parser."""
        try:
            graph = self._parser.parse(sql)
            return graph.tables_used
        except Exception:
            # Fallback: simple regex extraction
            return self._extract_tables_regex(sql)

    def _extract_tables_regex(self, sql: str) -> List[str]:
        """Fallback regex-based table extraction."""
        tables = set()
        # FROM clause
        from_matches = re.findall(
            r'\bFROM\s+(\w+)', sql, re.IGNORECASE
        )
        tables.update(t.lower() for t in from_matches)
        # JOIN clause
        join_matches = re.findall(
            r'\bJOIN\s+(\w+)', sql, re.IGNORECASE
        )
        tables.update(t.lower() for t in join_matches)
        return sorted(tables)

    def _extract_join_pairs(self, sql: str) -> List[Tuple[str, str]]:
        """
        Extract table pairs from JOIN clauses.
        Returns sorted tuples to ensure symmetry (A-B == B-A).
        """
        pairs = []
        # Find the FROM table
        from_match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        if not from_match:
            return pairs

        # Find all JOINed tables
        join_matches = re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
        if not join_matches:
            return pairs

        from_table = from_match.group(1).lower()

        # Create pairs between FROM table and each JOIN table
        seen = set()
        for join_table in join_matches:
            join_table = join_table.lower()
            pair = tuple(sorted([from_table, join_table]))
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)

        # Also create pairs between JOIN tables themselves
        join_tables = [t.lower() for t in join_matches]
        for i in range(len(join_tables)):
            for j in range(i + 1, len(join_tables)):
                pair = tuple(sorted([join_tables[i], join_tables[j]]))
                if pair not in seen:
                    seen.add(pair)
                    pairs.append(pair)

        return pairs
