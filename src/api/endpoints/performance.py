"""Performance Guru API Endpoints (Phase 22)

Provides EXPLAIN analysis with LLM-powered interpretation
for actionable query performance insights.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.database.models import DatabaseConnection
from src.core.schema_cache import SchemaCache
from src.guru.explain_analyzer import ExplainAnalyzer
from src.guru.explain_interpreter import get_explain_interpreter
from src.middleware.rate_limit import llm_rate_limiter
from src.models.schemas import (
    PerformanceAnalysisRequest,
    PerformanceAnalysisResponse,
    ExplainOnlyRequest,
    ExplainOnlyResponse,
    ExecutionPlanSchema,
    PerformanceInsightsSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])

_analyzer = ExplainAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_connection(db: AsyncSession, connection_id: int) -> DatabaseConnection:
    """Fetch a non-deleted database connection or raise 404."""
    result = await db.execute(
        select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.is_deleted.isnot(True),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
    return conn


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=PerformanceAnalysisResponse)
async def analyze_query_performance(
    request: PerformanceAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(llm_rate_limiter),
):
    """
    Run EXPLAIN on a query and return LLM-powered performance insights.

    - Parses the execution plan into a structured tree
    - Identifies bottlenecks (sequential scans, disk spills, expensive joins)
    - Suggests indexes with CREATE INDEX SQL
    - Suggests query rewrites if applicable

    **Safety**: `run_analyze=true` actually executes the query on the target database.
    Default is `false` (cost-based estimates only).
    """
    try:
        connection = await _get_connection(db, request.connection_id)

        # Run EXPLAIN
        plan = await _analyzer.run_explain(
            connection=connection,
            sql=request.sql,
            analyze=request.run_analyze,
        )

        # Get LLM interpreter
        interpreter = await get_explain_interpreter(db=db, model=request.model)

        # Get schema context if requested
        schema_context = None
        if request.include_schema_context:
            try:
                schema_data = await SchemaCache.get_schema(connection)
                if schema_data and isinstance(schema_data, dict):
                    # Simplify to table -> column names for the prompt
                    schema_context = {}
                    tables = schema_data.get("tables", [])
                    for table in tables:
                        table_name = table.get("name", "")
                        columns = [c.get("name", "") for c in table.get("columns", [])]
                        if table_name and columns:
                            schema_context[table_name] = columns
            except Exception as e:
                logger.debug(f"Could not load schema context: {e}")

        # Interpret with LLM
        insights = await interpreter.interpret(
            plan=plan,
            schema_context=schema_context,
            db=db,
        )

        return PerformanceAnalysisResponse(
            plan=ExecutionPlanSchema(**plan.to_dict()),
            insights=PerformanceInsightsSchema(**insights.to_dict()),
            connection_id=request.connection_id,
            sql=request.sql,
            analyzed=request.run_analyze,
            dialect=connection.database_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Performance analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Performance analysis failed: {str(e)}")


@router.post("/explain-only", response_model=ExplainOnlyResponse)
async def get_execution_plan(
    request: ExplainOnlyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run EXPLAIN without LLM interpretation (fast, no rate limit).

    Returns the parsed execution plan with deterministic warnings only.
    Useful for viewing the raw plan tree.
    """
    try:
        connection = await _get_connection(db, request.connection_id)

        plan = await _analyzer.run_explain(
            connection=connection,
            sql=request.sql,
            analyze=request.run_analyze,
        )

        return ExplainOnlyResponse(
            plan=ExecutionPlanSchema(**plan.to_dict()),
            dialect=connection.database_type,
            analyzed=request.run_analyze,
            warnings=plan.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EXPLAIN-only error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"EXPLAIN failed: {str(e)}")
