"""
Pattern Intelligence Agent - Phase 12.4

Transforms query pattern data into actionable insights:
- Bottleneck root cause analysis
- Optimization suggestions
- Query anti-pattern detection (N+1, SELECT *, etc.)
- Trend analysis

Uses QueryPatternAnalyzer for base pattern data and LLM for enhanced analysis.
"""

import asyncio
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QueryHistory, DatabaseConnection
from src.lineage.query_pattern_analyzer import (
    QueryPatternAnalyzer,
    PerformanceBottleneck,
    HeatmapData,
)
from src.lineage.llm_utils import parse_json_response

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BottleneckAnalysis:
    """LLM-enhanced analysis of a performance bottleneck."""
    table_name: str
    bottleneck_score: float
    root_causes: List[str]
    contributing_factors: List[str]
    optimization_suggestions: List[str]
    estimated_improvement: str  # "low", "medium", "high"
    sample_slow_queries: List[str]
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OptimizationSuggestion:
    """A suggested optimization for query patterns."""
    category: str  # "index", "query_rewrite", "caching", "schema"
    title: str
    description: str
    affected_tables: List[str]
    estimated_impact: str  # "low", "medium", "high"
    implementation_sql: Optional[str] = None
    priority: int = 0  # 1 = highest

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QueryAntiPattern:
    """A detected query anti-pattern."""
    pattern_type: str  # "select_star", "n_plus_one", "missing_where", "cartesian_join"
    severity: str  # "info", "warning", "error"
    title: str
    description: str
    affected_queries: List[int]  # Query IDs
    sample_sql: str
    recommendation: str
    occurrence_count: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class UsageTrend:
    """Trend data for a table's usage over time."""
    table_name: str
    period: str  # "daily", "weekly"
    data_points: List[Dict[str, Any]]  # [{"date": "2024-01-01", "count": 10}, ...]
    trend_direction: str  # "increasing", "decreasing", "stable"
    change_percentage: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrendAnalysis:
    """Complete trend analysis for a connection."""
    connection_id: int
    time_range_days: int
    table_trends: List[UsageTrend]
    busiest_tables: List[str]
    emerging_tables: List[str]  # Tables with increasing usage
    declining_tables: List[str]  # Tables with decreasing usage
    summary: str

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["table_trends"] = [t.to_dict() if isinstance(t, UsageTrend) else t for t in self.table_trends]
        return result


@dataclass
class PatternIntelligenceReport:
    """Complete pattern intelligence report."""
    connection_id: int
    bottleneck_analyses: List[BottleneckAnalysis] = field(default_factory=list)
    optimization_suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    anti_patterns: List[QueryAntiPattern] = field(default_factory=list)
    trend_analysis: Optional[TrendAnalysis] = None
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    analyzed_at: Optional[str] = None
    llm_used: bool = False

    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "connection_id": self.connection_id,
            "bottleneck_analyses": [b.to_dict() if isinstance(b, BottleneckAnalysis) else b for b in self.bottleneck_analyses],
            "optimization_suggestions": [o.to_dict() if isinstance(o, OptimizationSuggestion) else o for o in self.optimization_suggestions],
            "anti_patterns": [a.to_dict() if isinstance(a, QueryAntiPattern) else a for a in self.anti_patterns],
            "trend_analysis": self.trend_analysis.to_dict() if self.trend_analysis else None,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "analyzed_at": self.analyzed_at,
            "llm_used": self.llm_used,
        }


# =============================================================================
# LLM Prompts
# =============================================================================

BOTTLENECK_ANALYSIS_PROMPT = """Analyze this database performance bottleneck and provide insights.

## Bottleneck Information
Table: {table_name}
Query Count: {query_count}
Average Execution Time: {avg_time_ms}ms
Maximum Execution Time: {max_time_ms}ms
Bottleneck Score: {bottleneck_score} (0-1, higher = more severe)

## Sample Slow Queries
{sample_queries}

## Schema Context
{schema_context}

## Task
Analyze why this table is a bottleneck and suggest optimizations.

Respond in JSON format:
{{
  "root_causes": ["cause 1", "cause 2"],
  "contributing_factors": ["factor 1", "factor 2"],
  "optimization_suggestions": ["suggestion 1", "suggestion 2"],
  "estimated_improvement": "medium",
  "confidence": 0.8
}}

Keep root_causes focused on WHY it's slow (missing indexes, complex joins, full table scans).
Keep optimization_suggestions actionable and specific."""


ANTI_PATTERN_PROMPT = """Analyze these SQL queries for anti-patterns and bad practices.

## Sample Queries
{queries}

## Detected Patterns Summary
{detected_patterns}

## Task
Review the queries and provide additional insights about anti-patterns.

Respond in JSON format:
{{
  "additional_patterns": [
    {{
      "pattern_type": "n_plus_one",
      "title": "N+1 Query Pattern",
      "description": "Multiple similar queries suggest N+1 pattern",
      "severity": "warning",
      "recommendation": "Use JOINs or batch queries"
    }}
  ],
  "general_recommendations": ["recommendation 1", "recommendation 2"]
}}"""


OPTIMIZATION_PROMPT = """Analyze query patterns and suggest optimizations for this database.

## Pattern Summary
Most Used Tables: {most_used_tables}
Slowest Tables: {slowest_tables}
Common Join Patterns: {join_patterns}
Detected Anti-Patterns: {anti_patterns}

## Schema Overview
{schema_overview}

## Task
Provide prioritized optimization suggestions.

Respond in JSON format:
{{
  "suggestions": [
    {{
      "category": "index",
      "title": "Add composite index on orders",
      "description": "Detailed description",
      "affected_tables": ["orders"],
      "estimated_impact": "high",
      "implementation_sql": "CREATE INDEX ...",
      "priority": 1
    }}
  ],
  "summary": "Overall assessment in 2-3 sentences"
}}"""


# =============================================================================
# Anti-Pattern Detector (Deterministic)
# =============================================================================

class AntiPatternDetector:
    """Detects common SQL anti-patterns without LLM."""

    def detect_select_star(self, queries: List[QueryHistory]) -> List[QueryAntiPattern]:
        """Detect SELECT * usage."""
        affected = []
        sample_sql = ""
        count = 0

        for q in queries:
            sql = q.generated_sql or ""
            if re.search(r'\bSELECT\s+\*\s+FROM\b', sql, re.IGNORECASE):
                count += 1
                affected.append(q.id)
                if not sample_sql:
                    sample_sql = sql[:200]

        if count > 0:
            return [QueryAntiPattern(
                pattern_type="select_star",
                severity="warning",
                title="SELECT * Usage",
                description=f"Found {count} queries using SELECT *. This fetches unnecessary columns and can impact performance.",
                affected_queries=affected[:10],  # Limit to first 10
                sample_sql=sample_sql,
                recommendation="Specify only the columns you need to reduce data transfer and enable covering indexes.",
                occurrence_count=count,
            )]
        return []

    def detect_missing_where(self, queries: List[QueryHistory]) -> List[QueryAntiPattern]:
        """Detect SELECT/UPDATE/DELETE without WHERE clause."""
        affected = []
        sample_sql = ""
        count = 0

        for q in queries:
            sql = q.generated_sql or ""
            # Check for SELECT FROM without WHERE (but not aggregations)
            if re.search(r'\bSELECT\b.+\bFROM\b', sql, re.IGNORECASE):
                if not re.search(r'\bWHERE\b', sql, re.IGNORECASE):
                    # Exclude aggregations without grouping (valid)
                    if not re.search(r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\(', sql, re.IGNORECASE):
                        count += 1
                        affected.append(q.id)
                        if not sample_sql:
                            sample_sql = sql[:200]

        if count >= 3:  # Only report if multiple occurrences
            return [QueryAntiPattern(
                pattern_type="missing_where",
                severity="info",
                title="Full Table Scans",
                description=f"Found {count} SELECT queries without WHERE clauses, causing full table scans.",
                affected_queries=affected[:10],
                sample_sql=sample_sql,
                recommendation="Add WHERE clauses to limit data retrieval and improve performance.",
                occurrence_count=count,
            )]
        return []

    def detect_like_leading_wildcard(self, queries: List[QueryHistory]) -> List[QueryAntiPattern]:
        """Detect LIKE '%...' patterns that prevent index usage."""
        affected = []
        sample_sql = ""
        count = 0

        for q in queries:
            sql = q.generated_sql or ""
            if re.search(r"LIKE\s+['\"]%", sql, re.IGNORECASE):
                count += 1
                affected.append(q.id)
                if not sample_sql:
                    sample_sql = sql[:200]

        if count > 0:
            return [QueryAntiPattern(
                pattern_type="leading_wildcard",
                severity="warning",
                title="Leading Wildcard in LIKE",
                description=f"Found {count} queries with LIKE '%...' pattern. Leading wildcards prevent index usage.",
                affected_queries=affected[:10],
                sample_sql=sample_sql,
                recommendation="Consider full-text search, trigram indexes, or restructure queries to use trailing wildcards only.",
                occurrence_count=count,
            )]
        return []

    def detect_or_in_where(self, queries: List[QueryHistory]) -> List[QueryAntiPattern]:
        """Detect multiple OR conditions that may prevent index usage."""
        affected = []
        sample_sql = ""
        count = 0

        for q in queries:
            sql = q.generated_sql or ""
            # Count OR occurrences in WHERE clause
            where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', sql, re.I | re.S)
            if where_match:
                or_count = len(re.findall(r'\bOR\b', where_match.group(1), re.IGNORECASE))
                if or_count >= 3:  # Multiple ORs
                    count += 1
                    affected.append(q.id)
                    if not sample_sql:
                        sample_sql = sql[:200]

        if count >= 2:
            return [QueryAntiPattern(
                pattern_type="multiple_or",
                severity="info",
                title="Multiple OR Conditions",
                description=f"Found {count} queries with 3+ OR conditions. This can prevent efficient index usage.",
                affected_queries=affected[:10],
                sample_sql=sample_sql,
                recommendation="Consider using IN clause or UNION ALL for better index utilization.",
                occurrence_count=count,
            )]
        return []

    def detect_n_plus_one(self, queries: List[QueryHistory]) -> List[QueryAntiPattern]:
        """Detect potential N+1 query patterns (many similar queries in sequence)."""
        # Group queries by normalized pattern
        patterns: Dict[str, List[QueryHistory]] = defaultdict(list)

        for q in queries:
            sql = q.generated_sql or ""
            # Normalize by replacing values with placeholders
            normalized = re.sub(r"=\s*\d+", "= ?", sql)
            normalized = re.sub(r"=\s*'[^']*'", "= ?", normalized)
            normalized = re.sub(r"IN\s*\([^)]+\)", "IN (?)", normalized)
            patterns[normalized].append(q)

        # Find patterns with many repetitions
        results = []
        for pattern, qs in patterns.items():
            if len(qs) >= 10:  # Many similar queries
                results.append(QueryAntiPattern(
                    pattern_type="n_plus_one",
                    severity="warning",
                    title="Potential N+1 Query Pattern",
                    description=f"Found {len(qs)} similar queries differing only by parameter values. This suggests N+1 problem.",
                    affected_queries=[q.id for q in qs[:10]],
                    sample_sql=qs[0].generated_sql[:200] if qs[0].generated_sql else "",
                    recommendation="Use JOINs to fetch related data in a single query, or use IN clause for batch lookups.",
                    occurrence_count=len(qs),
                ))

        return results[:3]  # Limit to top 3

    def detect_all(self, queries: List[QueryHistory]) -> List[QueryAntiPattern]:
        """Run all anti-pattern detectors."""
        results = []
        results.extend(self.detect_select_star(queries))
        results.extend(self.detect_missing_where(queries))
        results.extend(self.detect_like_leading_wildcard(queries))
        results.extend(self.detect_or_in_where(queries))
        results.extend(self.detect_n_plus_one(queries))

        # Sort by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        results.sort(key=lambda x: (severity_order.get(x.severity, 3), -x.occurrence_count))

        return results


# =============================================================================
# Trend Analyzer (Deterministic)
# =============================================================================

class TrendAnalyzer:
    """Analyzes usage trends over time."""

    def __init__(self, parser=None):
        from src.lineage.sql_lineage_parser import SQLLineageParser
        self._parser = parser or SQLLineageParser()

    async def analyze_trends(
        self,
        db: AsyncSession,
        connection_id: int,
        time_range_days: int = 30,
    ) -> TrendAnalysis:
        """Analyze usage trends for a connection."""
        # Fetch queries with timestamps
        cutoff = datetime.now(timezone.utc) - timedelta(days=time_range_days)

        stmt = select(QueryHistory).where(
            QueryHistory.connection_id == connection_id,
            QueryHistory.executed == True,
            QueryHistory.created_at >= cutoff,
        ).order_by(QueryHistory.created_at.asc())

        result = await db.execute(stmt)
        queries = result.scalars().all()

        if not queries:
            return TrendAnalysis(
                connection_id=connection_id,
                time_range_days=time_range_days,
                table_trends=[],
                busiest_tables=[],
                emerging_tables=[],
                declining_tables=[],
                summary="No query data available for trend analysis.",
            )

        # Group by day and table
        daily_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for q in queries:
            if not q.generated_sql or not q.created_at:
                continue

            date_key = q.created_at.strftime("%Y-%m-%d")
            tables = self._extract_tables(q.generated_sql)

            for table in tables:
                daily_usage[table][date_key] += 1

        # Calculate trends for each table
        table_trends = []
        total_counts: Counter = Counter()

        for table, daily_data in daily_usage.items():
            sorted_dates = sorted(daily_data.keys())
            data_points = [{"date": d, "count": daily_data[d]} for d in sorted_dates]

            # Calculate trend
            if len(sorted_dates) >= 2:
                first_half = sorted_dates[:len(sorted_dates)//2]
                second_half = sorted_dates[len(sorted_dates)//2:]

                first_avg = sum(daily_data[d] for d in first_half) / len(first_half) if first_half else 0
                second_avg = sum(daily_data[d] for d in second_half) / len(second_half) if second_half else 0

                if first_avg > 0:
                    change_pct = ((second_avg - first_avg) / first_avg) * 100
                else:
                    change_pct = 100 if second_avg > 0 else 0

                if change_pct > 20:
                    direction = "increasing"
                elif change_pct < -20:
                    direction = "decreasing"
                else:
                    direction = "stable"
            else:
                direction = "stable"
                change_pct = 0

            trend = UsageTrend(
                table_name=table,
                period="daily",
                data_points=data_points,
                trend_direction=direction,
                change_percentage=round(change_pct, 1),
            )
            table_trends.append(trend)

            # Total count for sorting
            total_counts[table] = sum(daily_data.values())

        # Sort by total usage
        table_trends.sort(key=lambda t: total_counts[t.table_name], reverse=True)

        # Identify categories
        busiest = [t.table_name for t in table_trends[:5]]
        emerging = [t.table_name for t in table_trends if t.trend_direction == "increasing"][:5]
        declining = [t.table_name for t in table_trends if t.trend_direction == "decreasing"][:5]

        # Generate summary
        summary_parts = []
        if busiest:
            summary_parts.append(f"Most active tables: {', '.join(busiest[:3])}")
        if emerging:
            summary_parts.append(f"Usage increasing: {', '.join(emerging[:2])}")
        if declining:
            summary_parts.append(f"Usage declining: {', '.join(declining[:2])}")

        summary = ". ".join(summary_parts) + "." if summary_parts else "Query patterns are stable."

        return TrendAnalysis(
            connection_id=connection_id,
            time_range_days=time_range_days,
            table_trends=table_trends[:20],  # Limit to top 20
            busiest_tables=busiest,
            emerging_tables=emerging,
            declining_tables=declining,
            summary=summary,
        )

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        try:
            graph = self._parser.parse(sql)
            return graph.tables_used
        except Exception:
            # Fallback regex
            tables = set()
            from_matches = re.findall(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
            join_matches = re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
            tables.update(t.lower() for t in from_matches)
            tables.update(t.lower() for t in join_matches)
            return list(tables)


# =============================================================================
# Pattern Intelligence Agent
# =============================================================================

class PatternIntelligenceAgent:
    """
    LLM-enhanced pattern intelligence agent.

    Combines deterministic analysis with LLM-generated insights.
    """

    def __init__(
        self,
        ollama_client=None,
        model_router=None,
        timeout_seconds: float = 20.0,
        model: Optional[str] = None,
    ):
        self.client = ollama_client
        self.router = model_router
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.pattern_analyzer = QueryPatternAnalyzer()
        self.anti_pattern_detector = AntiPatternDetector()
        self.trend_analyzer = TrendAnalyzer()

    async def analyze_patterns(
        self,
        db: AsyncSession,
        connection_id: int,
        time_range_days: Optional[int] = 30,
        include_trends: bool = True,
    ) -> PatternIntelligenceReport:
        """
        Perform complete pattern intelligence analysis.

        Args:
            db: Database session
            connection_id: Connection to analyze
            time_range_days: Time range for analysis
            include_trends: Whether to include trend analysis

        Returns:
            PatternIntelligenceReport with complete analysis
        """
        report = PatternIntelligenceReport(connection_id=connection_id)

        # Step 1: Get base pattern data
        heatmap_data = await self.pattern_analyzer.get_heatmap_data(
            db, connection_id if connection_id > 0 else None, time_range_days
        )

        # Step 2: Fetch raw queries for anti-pattern analysis
        queries = await self._fetch_queries(db, connection_id, time_range_days)

        # Step 3: Detect anti-patterns (deterministic)
        report.anti_patterns = self.anti_pattern_detector.detect_all(queries)

        # Step 4: Analyze bottlenecks with LLM
        for bottleneck in heatmap_data.bottlenecks[:5]:  # Top 5
            analysis = await self.analyze_bottleneck(
                bottleneck, db, connection_id, queries
            )
            report.bottleneck_analyses.append(analysis)

        # Step 5: Generate optimization suggestions
        report.optimization_suggestions = await self._generate_optimizations(
            heatmap_data, report.anti_patterns, db, connection_id
        )

        # Step 6: Trend analysis
        if include_trends and connection_id > 0:
            report.trend_analysis = await self.trend_analyzer.analyze_trends(
                db, connection_id, time_range_days or 30
            )

        # Step 7: Generate summary
        report.summary = self._generate_summary(report, heatmap_data)
        report.recommendations = self._generate_recommendations(report)

        return report

    async def analyze_bottleneck(
        self,
        bottleneck: PerformanceBottleneck,
        db: AsyncSession,
        connection_id: int,
        queries: Optional[List[QueryHistory]] = None,
    ) -> BottleneckAnalysis:
        """Analyze a single bottleneck with LLM enhancement."""
        # Get sample slow queries for this table
        if queries is None:
            queries = await self._fetch_queries(db, connection_id, None)

        slow_queries = []
        for q in queries:
            if q.generated_sql and bottleneck.table_name.lower() in q.generated_sql.lower():
                if q.execution_time_ms and q.execution_time_ms > bottleneck.avg_execution_time_ms:
                    slow_queries.append(q.generated_sql[:300])
                    if len(slow_queries) >= 3:
                        break

        # Deterministic analysis
        analysis = BottleneckAnalysis(
            table_name=bottleneck.table_name,
            bottleneck_score=bottleneck.bottleneck_score,
            root_causes=[],
            contributing_factors=[],
            optimization_suggestions=[],
            estimated_improvement="medium",
            sample_slow_queries=slow_queries,
        )

        # Basic deterministic causes
        if bottleneck.avg_execution_time_ms > 1000:
            analysis.root_causes.append("High average query time indicates missing indexes or complex queries")
        if bottleneck.query_count > 100:
            analysis.root_causes.append("High query frequency suggests this is a hot table")
        if bottleneck.max_execution_time_ms > bottleneck.avg_execution_time_ms * 5:
            analysis.contributing_factors.append("High variance in execution times suggests occasional full table scans")

        # Basic suggestions
        analysis.optimization_suggestions.append(f"Review indexes on {bottleneck.table_name}")
        analysis.optimization_suggestions.append("Check for missing WHERE clause filters")

        # LLM enhancement
        if self.client and slow_queries:
            try:
                llm_analysis = await self._llm_analyze_bottleneck(bottleneck, slow_queries)
                if llm_analysis:
                    analysis.root_causes = self._normalize_string_list(
                        llm_analysis.get("root_causes", analysis.root_causes)
                    )
                    analysis.contributing_factors = self._normalize_string_list(
                        llm_analysis.get("contributing_factors", analysis.contributing_factors)
                    )
                    analysis.optimization_suggestions = self._normalize_string_list(
                        llm_analysis.get("optimization_suggestions", analysis.optimization_suggestions)
                    )
                    analysis.estimated_improvement = llm_analysis.get("estimated_improvement", "medium")
                    analysis.confidence = llm_analysis.get("confidence", 0.7)
            except Exception as e:
                logger.warning(f"LLM bottleneck analysis failed: {e}")

        return analysis

    async def _llm_analyze_bottleneck(
        self,
        bottleneck: PerformanceBottleneck,
        slow_queries: List[str],
    ) -> Optional[Dict]:
        """Get LLM analysis for a bottleneck."""
        prompt = BOTTLENECK_ANALYSIS_PROMPT.format(
            table_name=bottleneck.table_name,
            query_count=bottleneck.query_count,
            avg_time_ms=round(bottleneck.avg_execution_time_ms, 2),
            max_time_ms=round(bottleneck.max_execution_time_ms, 2),
            bottleneck_score=round(bottleneck.bottleneck_score, 4),
            sample_queries="\n".join(f"- {q}" for q in slow_queries[:3]),
            schema_context="(Schema not available)",
        )

        try:
            model = self._get_model()
            response = await asyncio.wait_for(
                self.client.generate(prompt=prompt, model=model, temperature=0.2),
                timeout=self.timeout_seconds,
            )
            return parse_json_response(response)
        except Exception as e:
            logger.warning(f"LLM bottleneck analysis error: {e}")
            return None

    async def _generate_optimizations(
        self,
        heatmap_data: HeatmapData,
        anti_patterns: List[QueryAntiPattern],
        db: AsyncSession,
        connection_id: int,
    ) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions."""
        suggestions = []

        # Index suggestions based on usage patterns
        for table in heatmap_data.table_usage[:10]:
            if table.query_count > 20 and (table.avg_execution_time_ms or 0) > 100:
                suggestions.append(OptimizationSuggestion(
                    category="index",
                    title=f"Review indexes on {table.table_name}",
                    description=f"Table has {table.query_count} queries with avg {table.avg_execution_time_ms:.0f}ms. Consider adding indexes.",
                    affected_tables=[table.table_name],
                    estimated_impact="medium" if table.avg_execution_time_ms < 500 else "high",
                    priority=2,
                ))

        # Join pattern optimizations
        for jp in heatmap_data.join_patterns[:5]:
            if jp.avg_execution_time_ms and jp.avg_execution_time_ms > 200:
                suggestions.append(OptimizationSuggestion(
                    category="index",
                    title=f"Optimize {jp.table_a} - {jp.table_b} join",
                    description=f"Join used {jp.join_count}x with avg {jp.avg_execution_time_ms:.0f}ms. Ensure join columns are indexed.",
                    affected_tables=[jp.table_a, jp.table_b],
                    estimated_impact="medium",
                    priority=3,
                ))

        # Anti-pattern based suggestions
        for ap in anti_patterns:
            if ap.pattern_type == "select_star":
                suggestions.append(OptimizationSuggestion(
                    category="query_rewrite",
                    title="Replace SELECT * with specific columns",
                    description=f"{ap.occurrence_count} queries use SELECT *. Specify columns to reduce data transfer.",
                    affected_tables=[],
                    estimated_impact="low",
                    priority=4,
                ))
            elif ap.pattern_type == "n_plus_one":
                suggestions.append(OptimizationSuggestion(
                    category="query_rewrite",
                    title="Fix N+1 query pattern",
                    description=f"Detected {ap.occurrence_count} similar queries. Use JOINs or batch queries.",
                    affected_tables=[],
                    estimated_impact="high",
                    priority=1,
                ))

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority)

        return suggestions[:10]

    def _generate_summary(self, report: PatternIntelligenceReport, heatmap: HeatmapData) -> str:
        """Generate summary for the report."""
        parts = []

        if report.bottleneck_analyses:
            parts.append(f"Identified {len(report.bottleneck_analyses)} performance bottlenecks")

        if report.anti_patterns:
            severe = sum(1 for ap in report.anti_patterns if ap.severity in ("warning", "error"))
            parts.append(f"Detected {len(report.anti_patterns)} anti-patterns ({severe} need attention)")

        if report.optimization_suggestions:
            high_impact = sum(1 for s in report.optimization_suggestions if s.estimated_impact == "high")
            parts.append(f"Generated {len(report.optimization_suggestions)} optimization suggestions ({high_impact} high-impact)")

        if heatmap.total_queries_analyzed > 0:
            parts.append(f"Based on {heatmap.total_queries_analyzed} queries analyzed")

        return ". ".join(parts) + "." if parts else "No significant patterns detected."

    def _generate_recommendations(self, report: PatternIntelligenceReport) -> List[str]:
        """Generate top recommendations."""
        recs = []

        # From bottlenecks
        for ba in report.bottleneck_analyses[:2]:
            if ba.optimization_suggestions:
                recs.append(f"[Bottleneck] {ba.table_name}: {ba.optimization_suggestions[0]}")

        # From anti-patterns
        for ap in report.anti_patterns[:2]:
            recs.append(f"[Anti-pattern] {ap.title}: {ap.recommendation[:100]}")

        # From optimizations
        for opt in report.optimization_suggestions[:2]:
            if opt.estimated_impact == "high":
                recs.append(f"[Optimization] {opt.title}")

        return recs[:5]

    async def _fetch_queries(
        self,
        db: AsyncSession,
        connection_id: int,
        time_range_days: Optional[int],
    ) -> List[QueryHistory]:
        """Fetch queries for analysis."""
        stmt = select(QueryHistory).where(
            QueryHistory.executed == True,
            QueryHistory.generated_sql.isnot(None),
        )

        if connection_id > 0:
            stmt = stmt.where(QueryHistory.connection_id == connection_id)

        if time_range_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=time_range_days)
            stmt = stmt.where(QueryHistory.created_at >= cutoff)

        stmt = stmt.order_by(QueryHistory.created_at.desc()).limit(500)

        result = await db.execute(stmt)
        return result.scalars().all()

    def _get_model(self) -> Optional[str]:
        """Get model to use for generation."""
        if self.model:
            return self.model
        if self.router:
            from src.llm.model_router import TaskType
            return self.router.get_model_for_task(TaskType.PATTERN_INTELLIGENCE)
        return None

    def _normalize_string_list(self, items: List[Any]) -> List[str]:
        """
        Normalize a list to contain only strings.

        LLMs sometimes return objects like {"cause": "..."} instead of plain strings.
        This method extracts the string value from such objects.
        """
        if not items:
            return []

        result = []
        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Extract the first string value from the dict
                for key in ['cause', 'factor', 'suggestion', 'reason', 'value', 'text', 'description']:
                    if key in item and isinstance(item[key], str):
                        result.append(item[key])
                        break
                else:
                    # Fallback: use first string value found
                    for v in item.values():
                        if isinstance(v, str):
                            result.append(v)
                            break
        return result

# =============================================================================
# Factory Function
# =============================================================================

async def get_pattern_intelligence_agent(
    db: Optional[AsyncSession] = None,
    model: Optional[str] = None,
) -> PatternIntelligenceAgent:
    """
    Factory function to create a PatternIntelligenceAgent instance.

    Args:
        db: Optional database session (for loading settings)
        model: Optional model override

    Returns:
        Configured PatternIntelligenceAgent instance
    """
    from src.llm.ollama_client import get_ollama_client
    from src.llm.model_router import get_model_router, TaskType

    client = get_ollama_client()
    router = await get_model_router(db) if db else None

    # Get timeout from router or use default
    timeout = 20.0
    if router:
        timeout = router.get_timeout_for_task(TaskType.PATTERN_INTELLIGENCE)

    # Use provided model or get from router
    effective_model = model
    if not effective_model and router:
        effective_model = router.get_model_for_task(TaskType.PATTERN_INTELLIGENCE)

    return PatternIntelligenceAgent(
        ollama_client=client,
        model_router=router,
        timeout_seconds=timeout,
        model=effective_model,
    )
