"""
Lineage API Endpoints

Phase 11: Data Lineage - SQL lineage parsing and impact analysis.
Phase 12.1: Lineage Narrator - LLM-powered lineage explanations.
Phase 12.2: Impact Advisor - LLM-powered migration plans and SQL patches.
Phase 12.3: Schema Health Analyzer - Database design quality analysis.
Phase 12.4: Pattern Intelligence - LLM-powered pattern analysis.
Phase 12.5: Conversational Lineage - Natural language Q&A about schema and lineage.

Endpoints:
  POST /api/lineage/parse        - Parse SQL → lineage graph (+ optional narrative)
  GET  /api/lineage/query/{id}   - Get lineage for a history query
  POST /api/lineage/impact       - Analyze impact of schema change
  POST /api/lineage/impact/advise - LLM-enhanced impact analysis with recommendations
  GET  /api/lineage/table/{name}/queries - Queries referencing a table
  GET  /api/lineage/stats        - Basic lineage statistics
  GET  /api/lineage/schema/health/{connection_id} - Analyze schema health
  GET  /api/lineage/patterns/{connection_id}/analyze - Pattern intelligence analysis
  GET  /api/lineage/patterns/{connection_id}/bottlenecks/{table} - Bottleneck analysis
  POST /api/lineage/ask          - Ask natural language questions about lineage/schema
"""

import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.common import get_db
from src.database.models import QueryHistory
from src.lineage.sql_lineage_parser import SQLLineageParser
from src.lineage.impact_analyzer import ImpactAnalyzer
from src.lineage.query_pattern_analyzer import QueryPatternAnalyzer
from src.models.schemas import (
    LineageParseRequest,
    LineageGraphResponse,
    LineageNodeSchema,
    LineageEdgeSchema,
    LineageNarrativeSchema,
    TransformationExplanationSchema,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    ImpactedQuerySchema,
    LineageStatsResponse,
    HeatmapDataResponse,
    TableUsageEntrySchema,
    JoinPatternSchema,
    PerformanceBottleneckSchema,
    # Phase 12.2: Impact Advisor
    ImpactAdviceRequest,
    ImpactAdviceResponse,
    RiskExplanationSchema,
    MigrationPlanSchema,
    MigrationStepSchema,
    SQLPatchSchema,
    # Phase 12.3: Schema Health
    SchemaHealthReportSchema,
    IndexSuggestionSchema,
    SchemaIssueSchema,
    NormalizationIssueSchema,
    TableHealthSummarySchema,
    # Phase 12.4: Pattern Intelligence
    PatternIntelligenceReportSchema,
    BottleneckAnalysisSchema,
    OptimizationSuggestionSchema,
    QueryAntiPatternSchema,
    TrendAnalysisSchema,
    UsageTrendSchema,
    # Phase 12.5: Conversational Lineage
    LineageQuestionRequest,
    LineageAnswerSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lineage", tags=["lineage"])

# Shared instances
_parser = SQLLineageParser()
_analyzer = ImpactAnalyzer()
_pattern_analyzer = QueryPatternAnalyzer()


@router.post("/parse", response_model=LineageGraphResponse)
async def parse_sql_lineage(
    request: LineageParseRequest,
    explain: bool = Query(
        default=False,
        description="Generate LLM narrative explanation of the lineage (Phase 12.1)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Parse a SQL query and return its data lineage graph.

    The graph contains nodes (source tables, columns, transformations, outputs)
    and edges showing how data flows from sources to outputs.

    Set explain=true to generate an LLM-powered natural language narrative
    explaining the data flow in business terms.
    """
    try:
        graph = _parser.parse(request.sql)

        # Generate narrative if requested (Phase 12.1)
        narrative_schema = None
        if explain and graph.nodes:
            try:
                from src.lineage.lineage_narrator import get_lineage_narrator

                narrator = await get_lineage_narrator(db_session=db)
                narrative = await narrator.generate_narrative(
                    lineage_graph=graph,
                    question=request.question,
                )

                # Convert to schema
                narrative_dict = narrative.to_dict()
                narrative_schema = LineageNarrativeSchema(
                    summary=narrative_dict.get("summary", ""),
                    data_flow_description=narrative_dict.get("data_flow_description", ""),
                    column_explanations=narrative_dict.get("column_explanations", {}),
                    transformations_explained=[
                        TransformationExplanationSchema(**t)
                        for t in narrative_dict.get("transformations_explained", [])
                    ],
                    business_context=narrative_dict.get("business_context", {}),
                    potential_issues=narrative_dict.get("potential_issues", []),
                    confidence=narrative_dict.get("confidence", 0.5),
                    generated_at=narrative_dict.get("generated_at"),
                )
                logger.info(f"✅ Generated lineage narrative with confidence {narrative.confidence:.2f}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to generate narrative: {e}")
                # Continue without narrative - graceful degradation

        return LineageGraphResponse(
            nodes=[LineageNodeSchema(**n.to_dict()) for n in graph.nodes],
            edges=[LineageEdgeSchema(**e.to_dict()) for e in graph.edges],
            sql=graph.sql,
            tables_used=graph.tables_used,
            columns_used=graph.columns_used,
            output_columns=graph.output_columns,
            narrative=narrative_schema,
        )
    except Exception as e:
        logger.error(f"Lineage parse error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse SQL: {str(e)}")


@router.get("/query/{query_id}", response_model=LineageGraphResponse)
async def get_query_lineage(
    query_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get lineage graph for a query from history.
    """
    result = await db.execute(
        select(QueryHistory).where(QueryHistory.id == query_id)
    )
    query = result.scalar_one_or_none()

    if not query:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")

    if not query.generated_sql:
        raise HTTPException(status_code=400, detail="Query has no generated SQL")

    graph = _parser.parse(query.generated_sql)

    return LineageGraphResponse(
        nodes=[LineageNodeSchema(**n.to_dict()) for n in graph.nodes],
        edges=[LineageEdgeSchema(**e.to_dict()) for e in graph.edges],
        sql=graph.sql,
        tables_used=graph.tables_used,
        columns_used=graph.columns_used,
        output_columns=graph.output_columns,
    )


@router.post("/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    request: ImpactAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze the impact of a schema change on existing queries.

    If column_name is provided, analyzes column-level impact.
    Otherwise, analyzes table-level impact.
    """
    try:
        if request.column_name:
            analysis = await _analyzer.analyze_column_impact(
                db, request.table_name, request.column_name
            )
        else:
            analysis = await _analyzer.analyze_table_impact(
                db, request.table_name
            )

        return ImpactAnalysisResponse(
            changed_object=analysis.changed_object,
            object_type=analysis.object_type,
            impacted_queries=[
                ImpactedQuerySchema(**q.to_dict()) for q in analysis.impacted_queries
            ],
            total_affected=analysis.total_affected,
            risk_level=analysis.risk_level,
            risk_counts=analysis.risk_counts,
            summary=analysis.summary,
        )
    except Exception as e:
        logger.error(f"Impact analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Impact analysis failed: {str(e)}")


@router.post("/impact/advise", response_model=ImpactAdviceResponse)
async def get_impact_advice(
    request: ImpactAdviceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Get LLM-enhanced impact analysis with recommendations.

    Phase 12.2: Extends basic impact analysis with:
    - Risk explanations (why the change is risky)
    - Migration plans (step-by-step guide)
    - SQL patches (corrected queries for the new schema)
    """
    try:
        from src.lineage.impact_advisor import get_impact_advisor

        advisor = await get_impact_advisor(db=db)
        advice = await advisor.analyze_with_recommendations(
            db=db,
            change_type=request.change_type,
            table_name=request.table_name,
            column_name=request.column_name,
            new_value=request.new_value,
            include_patches=request.include_patches,
        )

        # Convert to response schema
        impact_response = ImpactAnalysisResponse(
            changed_object=advice.impact.changed_object,
            object_type=advice.impact.object_type,
            impacted_queries=[
                ImpactedQuerySchema(**q.to_dict()) for q in advice.impact.impacted_queries
            ],
            total_affected=advice.impact.total_affected,
            risk_level=advice.impact.risk_level,
            risk_counts=advice.impact.risk_counts,
            summary=advice.impact.summary,
        )

        # Convert risk explanation
        risk_explanation = None
        if advice.risk_explanation:
            risk_explanation = RiskExplanationSchema(
                risk_level=advice.risk_explanation.risk_level,
                summary=advice.risk_explanation.summary,
                detailed_explanation=advice.risk_explanation.detailed_explanation,
                affected_areas=advice.risk_explanation.affected_areas,
                recommendations=advice.risk_explanation.recommendations,
                confidence=advice.risk_explanation.confidence,
            )

        # Convert migration plan
        migration_plan = None
        if advice.migration_plan:
            migration_plan = MigrationPlanSchema(
                change_type=advice.migration_plan.change_type,
                target_object=advice.migration_plan.target_object,
                new_value=advice.migration_plan.new_value,
                steps=[
                    MigrationStepSchema(
                        step_number=s.step_number,
                        action=s.action,
                        description=s.description,
                        sql=s.sql,
                        reversible=s.reversible,
                        risk_level=s.risk_level,
                    )
                    for s in advice.migration_plan.steps
                ],
                estimated_downtime=advice.migration_plan.estimated_downtime,
                rollback_possible=advice.migration_plan.rollback_possible,
                warnings=advice.migration_plan.warnings,
                generated_at=advice.migration_plan.generated_at,
            )

        # Convert SQL patches
        sql_patches = [
            SQLPatchSchema(
                query_id=p.query_id,
                original_sql=p.original_sql,
                patched_sql=p.patched_sql,
                change_description=p.change_description,
                confidence=p.confidence,
                requires_review=p.requires_review,
            )
            for p in advice.sql_patches
        ]

        logger.info(
            f"✅ Generated impact advice for {request.change_type} on "
            f"{request.table_name}.{request.column_name or '*'} "
            f"(LLM used: {advice.llm_used})"
        )

        return ImpactAdviceResponse(
            impact=impact_response,
            change_type=advice.change_type,
            new_value=advice.new_value,
            risk_explanation=risk_explanation,
            migration_plan=migration_plan,
            sql_patches=sql_patches,
            generated_at=advice.generated_at,
            llm_used=advice.llm_used,
        )
    except Exception as e:
        logger.error(f"Impact advice error: {e}")
        raise HTTPException(status_code=500, detail=f"Impact advice failed: {str(e)}")


@router.get("/table/{table_name}/queries")
async def get_table_queries(
    table_name: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get queries that reference a specific table.
    """
    queries = await _analyzer.get_queries_for_table(db, table_name, limit)
    return {
        "table_name": table_name,
        "queries": [q.to_dict() for q in queries],
        "total": len(queries),
    }


@router.get("/stats", response_model=LineageStatsResponse)
async def get_lineage_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get basic lineage statistics from query history.
    """
    stats = await _analyzer.get_lineage_stats(db)
    return LineageStatsResponse(**stats)


@router.get("/patterns/{connection_id}", response_model=HeatmapDataResponse)
async def get_query_patterns(
    connection_id: int,
    time_range: Optional[int] = Query(
        default=None,
        description="Time range in days (7, 30, 90, or None for all)",
        ge=1,
        le=365,
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get query pattern analytics for a connection.

    Returns table usage frequencies, common join patterns, and bottlenecks.
    Pass connection_id=0 for all connections.
    """
    conn_id = connection_id if connection_id > 0 else None
    heatmap = await _pattern_analyzer.get_heatmap_data(db, conn_id, time_range)

    return HeatmapDataResponse(
        table_usage=[
            TableUsageEntrySchema(
                table_name=t.table_name,
                query_count=t.query_count,
                join_count=t.join_count,
                avg_execution_time_ms=t.avg_execution_time_ms,
                last_used_at=t.last_used_at,
            )
            for t in heatmap.table_usage
        ],
        join_patterns=[
            JoinPatternSchema(
                table_a=j.table_a,
                table_b=j.table_b,
                join_count=j.join_count,
                sample_sql=j.sample_sql,
                avg_execution_time_ms=j.avg_execution_time_ms,
            )
            for j in heatmap.join_patterns
        ],
        bottlenecks=[
            PerformanceBottleneckSchema(
                table_name=b.table_name,
                query_count=b.query_count,
                avg_execution_time_ms=b.avg_execution_time_ms,
                max_execution_time_ms=b.max_execution_time_ms,
                bottleneck_score=b.bottleneck_score,
            )
            for b in heatmap.bottlenecks
        ],
        time_range_days=heatmap.time_range_days,
        total_queries_analyzed=heatmap.total_queries_analyzed,
        connection_id=heatmap.connection_id,
    )


@router.get("/schema/health/{connection_id}", response_model=SchemaHealthReportSchema)
async def get_schema_health(
    connection_id: int,
    include_patterns: bool = Query(
        default=True,
        description="Include query pattern analysis for index suggestions",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze schema health for a database connection.

    Phase 12.3: Returns comprehensive health report with:
    - Overall grade (A-F) and score (0-100)
    - Index suggestions based on query patterns
    - Normalization issues
    - Anti-patterns and structural issues
    - LLM-generated recommendations
    """
    try:
        from src.lineage.schema_health_analyzer import get_schema_health_analyzer

        analyzer = await get_schema_health_analyzer(db=db)
        report = await analyzer.analyze_schema_health(
            db=db,
            connection_id=connection_id,
            include_patterns=include_patterns,
        )

        # Convert to response schema
        logger.info(
            f"Schema health analysis complete for connection {connection_id}: "
            f"Grade {report.grade}, Score {report.score}"
        )

        return SchemaHealthReportSchema(
            connection_id=report.connection_id,
            database_name=report.database_name,
            grade=report.grade,
            score=report.score,
            table_count=report.table_count,
            total_issues=report.total_issues,
            critical_issues=report.critical_issues,
            index_suggestions=[
                IndexSuggestionSchema(
                    table_name=s.table_name,
                    columns=s.columns,
                    index_type=s.index_type,
                    reason=s.reason,
                    estimated_impact=s.estimated_impact,
                    create_sql=s.create_sql,
                    query_count_benefiting=s.query_count_benefiting,
                )
                for s in report.index_suggestions
            ],
            normalization_issues=[
                NormalizationIssueSchema(
                    table_name=n.table_name,
                    issue_type=n.issue_type,
                    description=n.description,
                    affected_columns=n.affected_columns,
                    recommendation=n.recommendation,
                )
                for n in report.normalization_issues
            ],
            anti_patterns=[
                SchemaIssueSchema(
                    category=a.category,
                    severity=a.severity,
                    title=a.title,
                    description=a.description,
                    affected_objects=a.affected_objects,
                    recommendation=a.recommendation,
                    fix_sql=a.fix_sql,
                )
                for a in report.anti_patterns
            ],
            table_summaries=[
                TableHealthSummarySchema(
                    table_name=t.table_name,
                    column_count=t.column_count,
                    has_primary_key=t.has_primary_key,
                    foreign_key_count=t.foreign_key_count,
                    index_count=t.index_count,
                    issues=[
                        SchemaIssueSchema(
                            category=i.category,
                            severity=i.severity,
                            title=i.title,
                            description=i.description,
                            affected_objects=i.affected_objects,
                            recommendation=i.recommendation,
                            fix_sql=i.fix_sql,
                        )
                        for i in t.issues
                    ],
                    suggestions=[
                        IndexSuggestionSchema(
                            table_name=s.table_name,
                            columns=s.columns,
                            index_type=s.index_type,
                            reason=s.reason,
                            estimated_impact=s.estimated_impact,
                            create_sql=s.create_sql,
                            query_count_benefiting=s.query_count_benefiting,
                        )
                        for s in t.suggestions
                    ],
                )
                for t in report.table_summaries
            ],
            summary=report.summary,
            recommendations=report.recommendations,
            analyzed_at=report.analyzed_at,
            llm_used=report.llm_used,
        )
    except Exception as e:
        logger.error(f"Schema health analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Schema health analysis failed: {str(e)}")


@router.get("/patterns/{connection_id}/analyze", response_model=PatternIntelligenceReportSchema)
async def analyze_patterns(
    connection_id: int,
    time_range: Optional[int] = Query(
        default=30,
        description="Time range in days (7, 30, 90, or None for all)",
        ge=1,
        le=365,
    ),
    include_trends: bool = Query(
        default=True,
        description="Include usage trend analysis",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get LLM-enhanced pattern intelligence analysis.

    Phase 12.4: Returns comprehensive pattern analysis with:
    - Bottleneck root cause analysis
    - Optimization suggestions
    - Query anti-pattern detection (N+1, SELECT *, etc.)
    - Usage trend analysis
    """
    try:
        from src.lineage.pattern_intelligence import get_pattern_intelligence_agent

        agent = await get_pattern_intelligence_agent(db=db)
        report = await agent.analyze_patterns(
            db=db,
            connection_id=connection_id,
            time_range_days=time_range,
            include_trends=include_trends,
        )

        logger.info(
            f"Pattern intelligence analysis complete for connection {connection_id}: "
            f"{len(report.bottleneck_analyses)} bottlenecks, "
            f"{len(report.anti_patterns)} anti-patterns, "
            f"{len(report.optimization_suggestions)} suggestions"
        )

        # Convert to response schema
        return PatternIntelligenceReportSchema(
            connection_id=report.connection_id,
            bottleneck_analyses=[
                BottleneckAnalysisSchema(
                    table_name=b.table_name,
                    bottleneck_score=b.bottleneck_score,
                    root_causes=b.root_causes,
                    contributing_factors=b.contributing_factors,
                    optimization_suggestions=b.optimization_suggestions,
                    estimated_improvement=b.estimated_improvement,
                    sample_slow_queries=b.sample_slow_queries,
                    confidence=b.confidence,
                )
                for b in report.bottleneck_analyses
            ],
            optimization_suggestions=[
                OptimizationSuggestionSchema(
                    category=o.category,
                    title=o.title,
                    description=o.description,
                    affected_tables=o.affected_tables,
                    estimated_impact=o.estimated_impact,
                    implementation_sql=o.implementation_sql,
                    priority=o.priority,
                )
                for o in report.optimization_suggestions
            ],
            anti_patterns=[
                QueryAntiPatternSchema(
                    pattern_type=a.pattern_type,
                    severity=a.severity,
                    title=a.title,
                    description=a.description,
                    affected_queries=a.affected_queries,
                    sample_sql=a.sample_sql,
                    recommendation=a.recommendation,
                    occurrence_count=a.occurrence_count,
                )
                for a in report.anti_patterns
            ],
            trend_analysis=_convert_trend_analysis(report.trend_analysis) if report.trend_analysis else None,
            summary=report.summary,
            recommendations=report.recommendations,
            analyzed_at=report.analyzed_at,
            llm_used=report.llm_used,
        )
    except Exception as e:
        logger.error(f"Pattern intelligence analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern intelligence analysis failed: {str(e)}")


@router.get("/patterns/{connection_id}/bottlenecks/{table_name}", response_model=BottleneckAnalysisSchema)
async def analyze_bottleneck(
    connection_id: int,
    table_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed bottleneck analysis for a specific table.

    Phase 12.4: Returns LLM-enhanced analysis with:
    - Root cause identification
    - Contributing factors
    - Specific optimization suggestions
    """
    try:
        from src.lineage.pattern_intelligence import get_pattern_intelligence_agent
        from src.lineage.query_pattern_analyzer import PerformanceBottleneck

        agent = await get_pattern_intelligence_agent(db=db)

        # Get heatmap data to find the bottleneck
        conn_id = connection_id if connection_id > 0 else None
        heatmap = await _pattern_analyzer.get_heatmap_data(db, conn_id, None)

        # Find the bottleneck for this table
        bottleneck = None
        for b in heatmap.bottlenecks:
            if b.table_name.lower() == table_name.lower():
                bottleneck = b
                break

        if not bottleneck:
            # Create a minimal bottleneck from table usage
            for t in heatmap.table_usage:
                if t.table_name.lower() == table_name.lower():
                    bottleneck = PerformanceBottleneck(
                        table_name=t.table_name,
                        query_count=t.query_count,
                        avg_execution_time_ms=t.avg_execution_time_ms or 0,
                        max_execution_time_ms=(t.avg_execution_time_ms or 0) * 2,
                        bottleneck_score=0.5,
                    )
                    break

        if not bottleneck:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in query patterns")

        analysis = await agent.analyze_bottleneck(bottleneck, db, connection_id)

        logger.info(f"Bottleneck analysis complete for {table_name}: {len(analysis.root_causes)} causes identified")

        return BottleneckAnalysisSchema(
            table_name=analysis.table_name,
            bottleneck_score=analysis.bottleneck_score,
            root_causes=analysis.root_causes,
            contributing_factors=analysis.contributing_factors,
            optimization_suggestions=analysis.optimization_suggestions,
            estimated_improvement=analysis.estimated_improvement,
            sample_slow_queries=analysis.sample_slow_queries,
            confidence=analysis.confidence,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bottleneck analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Bottleneck analysis failed: {str(e)}")


def _convert_trend_analysis(trend) -> TrendAnalysisSchema:
    """Convert TrendAnalysis dataclass to schema."""
    return TrendAnalysisSchema(
        connection_id=trend.connection_id,
        time_range_days=trend.time_range_days,
        table_trends=[
            UsageTrendSchema(
                table_name=t.table_name,
                period=t.period,
                data_points=t.data_points,
                trend_direction=t.trend_direction,
                change_percentage=t.change_percentage,
            )
            for t in trend.table_trends
        ],
        busiest_tables=trend.busiest_tables,
        emerging_tables=trend.emerging_tables,
        declining_tables=trend.declining_tables,
        summary=trend.summary,
    )


@router.post("/ask", response_model=LineageAnswerSchema)
async def ask_lineage_question(
    request: LineageQuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a natural language question about lineage, schema, or patterns.

    Phase 12.5: Conversational Lineage - Supports multi-turn conversations
    with automatic question classification and routing.

    Question types:
    - LINEAGE: "What feeds into X?", "Where does Y come from?"
    - IMPACT: "What breaks if I change X?", "Affected by Y?"
    - PATTERN: "Most used tables?", "Bottlenecks?"
    - SCHEMA: "What columns does X have?", "Describe table Y"
    - RECOMMENDATION: "How to optimize?", "Suggest indexes?"
    - GENERAL: Other questions about the database

    Use session_id for multi-turn conversations to maintain context.
    """
    try:
        from src.lineage.lineage_conversation_agent import get_lineage_conversation_agent

        agent = await get_lineage_conversation_agent(db=db)
        answer = await agent.ask(
            question=request.question,
            connection_id=request.connection_id,
            db=db,
            session_id=request.session_id,
        )

        logger.info(
            f"Answered lineage question ({answer.question_type}): "
            f"{request.question[:50]}... -> confidence={answer.confidence:.2f}"
        )

        return LineageAnswerSchema(
            question=answer.question,
            question_type=answer.question_type,
            answer=answer.answer,
            supporting_data=answer.supporting_data,
            related_tables=answer.related_tables,
            related_queries=answer.related_queries,
            confidence=answer.confidence,
            follow_up_suggestions=answer.follow_up_suggestions,
            generated_at=answer.generated_at,
            llm_used=answer.llm_used,
        )
    except Exception as e:
        logger.error(f"Lineage question error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")
