"""
Lineage API Endpoints

Phase 11: Data Lineage - SQL lineage parsing and impact analysis.

Endpoints:
  POST /api/lineage/parse        - Parse SQL → lineage graph
  GET  /api/lineage/query/{id}   - Get lineage for a history query
  POST /api/lineage/impact       - Analyze impact of schema change
  GET  /api/lineage/table/{name}/queries - Queries referencing a table
  GET  /api/lineage/stats        - Basic lineage statistics
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.common import get_db
from src.database.models import QueryHistory
from src.lineage.sql_lineage_parser import SQLLineageParser
from src.lineage.impact_analyzer import ImpactAnalyzer
from src.models.schemas import (
    LineageParseRequest,
    LineageGraphResponse,
    LineageNodeSchema,
    LineageEdgeSchema,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    ImpactedQuerySchema,
    LineageStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lineage", tags=["lineage"])

# Shared instances
_parser = SQLLineageParser()
_analyzer = ImpactAnalyzer()


@router.post("/parse", response_model=LineageGraphResponse)
async def parse_sql_lineage(request: LineageParseRequest):
    """
    Parse a SQL query and return its data lineage graph.

    The graph contains nodes (source tables, columns, transformations, outputs)
    and edges showing how data flows from sources to outputs.
    """
    try:
        graph = _parser.parse(request.sql)

        return LineageGraphResponse(
            nodes=[LineageNodeSchema(**n.to_dict()) for n in graph.nodes],
            edges=[LineageEdgeSchema(**e.to_dict()) for e in graph.edges],
            sql=graph.sql,
            tables_used=graph.tables_used,
            columns_used=graph.columns_used,
            output_columns=graph.output_columns,
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
