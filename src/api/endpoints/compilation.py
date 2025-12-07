"""
Query Compilation API Endpoints (Phase 4.2)

Provides REST API for managing query compilation metrics, plan cache,
and prepared statement management.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.connection import get_db
from src.database.models import CompiledQueryMetrics, CompilationInvalidationLog, DatabaseConnection
from src.cache.plan_cache import get_plan_cache
from src.core.prepared_statement_manager import get_prepared_statement_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compilation", tags=["compilation"])


class CompilationStatsResponse:
    """Response model for compilation statistics"""

    def __init__(self, data: Dict[str, Any]):
        self.plan_cache_stats = data.get("plan_cache_stats", {})
        self.statement_manager_stats = data.get("statement_manager_stats", {})
        self.database_metrics = data.get("database_metrics", {})
        self.timestamp = data.get("timestamp")


@router.get("/stats", summary="Get global compilation statistics")
async def get_compilation_stats(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get global compilation statistics across all connections.

    Returns:
        - Plan cache statistics (size, hit rate, plans cached)
        - Prepared statement manager statistics
        - Database metrics summary
    """
    try:
        plan_cache = get_plan_cache()
        stmt_manager = get_prepared_statement_manager()

        # Get plan cache stats
        plan_cache_stats = plan_cache.get_stats()

        # Get statement manager stats
        stmt_manager_stats = stmt_manager.get_stats()

        # Get database metrics summary
        result = await db.execute(
            select(
                DatabaseConnection.id,
                DatabaseConnection.name,
            ).where(DatabaseConnection.is_active == True)
        )
        connections = result.fetchall()

        database_metrics = {}
        for conn_id, conn_name in connections:
            result = await db.execute(
                select(CompiledQueryMetrics).where(
                    CompiledQueryMetrics.connection_id == conn_id
                )
            )
            metrics = result.fetchall()

            if metrics:
                total_executions = sum(m[0].total_executions for m in result)
                total_execution_ms = sum(m[0].total_execution_ms for m in result)
                prepared_count = sum(1 for m in metrics if m[0].is_prepared)
                plan_cached_count = sum(1 for m in metrics if m[0].is_plan_cached)

                database_metrics[conn_name] = {
                    "connection_id": conn_id,
                    "total_queries": len(metrics),
                    "prepared_statements": prepared_count,
                    "cached_plans": plan_cached_count,
                    "total_executions": total_executions,
                    "total_execution_ms": round(total_execution_ms, 2),
                    "avg_execution_ms": round(
                        total_execution_ms / max(total_executions, 1), 2
                    ),
                }

        return {
            "success": True,
            "plan_cache": plan_cache_stats,
            "statement_manager": stmt_manager_stats,
            "databases": database_metrics,
            "timestamp": str(__import__("datetime").datetime.utcnow()),
        }

    except Exception as e:
        logger.error(f"Error getting compilation stats: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/metrics/{connection_id}", summary="Get per-connection compilation metrics")
async def get_connection_metrics(
    connection_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get compilation metrics for a specific database connection.

    Args:
        connection_id: Database connection ID
        limit: Maximum number of metrics to return (default: 50)
        offset: Number of metrics to skip (default: 0)

    Returns:
        - Connection name and type
        - Compiled query metrics (execution counts, cache hits, etc.)
        - Performance statistics
        - Pagination info
    """
    try:
        # Verify connection exists
        result = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Get metrics for this connection
        result = await db.execute(
            select(CompiledQueryMetrics)
            .where(CompiledQueryMetrics.connection_id == connection_id)
            .order_by(CompiledQueryMetrics.last_executed_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        metrics_list = result.fetchall()

        # Check if there are more results
        has_more = len(metrics_list) > limit
        if has_more:
            metrics_list = metrics_list[:limit]

        # Convert to dictionaries
        metrics = []
        for m_tuple in metrics_list:
            m = m_tuple[0]
            metrics.append({
                "id": m.id,
                "normalized_hash": m.normalized_hash,
                "template_sql": m.template_sql[:100] + "..." if len(m.template_sql) > 100 else m.template_sql,
                "is_prepared": m.is_prepared,
                "is_plan_cached": m.is_plan_cached,
                "total_executions": m.total_executions,
                "total_execution_ms": round(m.total_execution_ms, 2),
                "avg_execution_ms": round(m.avg_execution_ms, 2),
                "plan_cache_hits": m.plan_cache_hits,
                "plan_cache_misses": m.plan_cache_misses,
                "prepared_statement_hits": m.prepared_statement_hits,
                "last_executed_at": m.last_executed_at.isoformat(),
            })

        # Calculate totals
        total_executions = sum(m["total_executions"] for m in metrics) if metrics else 0
        total_execution_ms = sum(m["total_execution_ms"] for m in metrics) if metrics else 0
        prepared_count = sum(1 for m in metrics if m["is_prepared"])
        cached_count = sum(1 for m in metrics if m["is_plan_cached"])

        return {
            "success": True,
            "connection": {
                "id": connection.id,
                "name": connection.name,
                "database_type": connection.database_type,
            },
            "metrics": metrics,
            "summary": {
                "total_compiled_queries": len(metrics),
                "prepared_statements": prepared_count,
                "cached_plans": cached_count,
                "total_executions": total_executions,
                "total_execution_ms": round(total_execution_ms, 2),
                "avg_execution_ms": round(total_execution_ms / max(total_executions, 1), 2),
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connection metrics: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.delete(
    "/cache/connection/{connection_id}",
    summary="Invalidate all compilation caches for a connection"
)
async def invalidate_connection_cache(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Invalidate all plan caches and prepared statements for a connection.

    This is useful when the database schema has changed significantly
    or for manual cache clearing.

    Args:
        connection_id: Database connection ID to invalidate

    Returns:
        - Number of plans invalidated
        - Number of prepared statements invalidated
        - Invalidation log entry ID
    """
    try:
        # Verify connection exists
        result = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Invalidate plan cache
        plan_cache = get_plan_cache()
        plans_invalidated = await plan_cache.invalidate_connection(connection_id)

        # Invalidate prepared statements
        stmt_manager = get_prepared_statement_manager()
        statements_invalidated = await stmt_manager.invalidate_connection(connection_id)

        # Log invalidation
        invalidation_log = CompilationInvalidationLog(
            connection_id=connection_id,
            table_name=None,
            invalidation_reason="manual",
            plans_invalidated=plans_invalidated,
            statements_invalidated=statements_invalidated,
            details="Manual invalidation via API",
        )
        db.add(invalidation_log)
        await db.commit()

        return {
            "success": True,
            "connection_id": connection_id,
            "plans_invalidated": plans_invalidated,
            "statements_invalidated": statements_invalidated,
            "log_id": invalidation_log.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating connection cache: {e}")
        await db.rollback()
        return {
            "success": False,
            "error": str(e),
        }


@router.delete(
    "/cache/table/{connection_id}/{table_name}",
    summary="Invalidate compilation cache for a specific table"
)
async def invalidate_table_cache(
    connection_id: int,
    table_name: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Invalidate plan caches and prepared statements for queries using a specific table.

    This is useful when a table's schema changes without affecting other tables.

    Args:
        connection_id: Database connection ID
        table_name: Table name that changed

    Returns:
        - Number of plans invalidated
        - Number of prepared statements invalidated
        - Invalidation log entry ID
    """
    try:
        # Verify connection exists
        result = await db.execute(
            select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Invalidate plan cache for this table
        plan_cache = get_plan_cache()
        plans_invalidated = await plan_cache.invalidate_table(connection_id, table_name)

        # Note: Statement manager doesn't have table-level invalidation yet
        statements_invalidated = 0

        # Log invalidation
        invalidation_log = CompilationInvalidationLog(
            connection_id=connection_id,
            table_name=table_name,
            invalidation_reason="manual",
            plans_invalidated=plans_invalidated,
            statements_invalidated=statements_invalidated,
            details=f"Manual table invalidation via API for table: {table_name}",
        )
        db.add(invalidation_log)
        await db.commit()

        return {
            "success": True,
            "connection_id": connection_id,
            "table_name": table_name,
            "plans_invalidated": plans_invalidated,
            "statements_invalidated": statements_invalidated,
            "log_id": invalidation_log.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating table cache: {e}")
        await db.rollback()
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/invalidation-log", summary="Get compilation invalidation log")
async def get_invalidation_log(
    connection_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get recent invalidation log entries.

    Args:
        connection_id: Filter by connection ID (optional)
        limit: Maximum number of entries to return
        offset: Number of entries to skip

    Returns:
        - List of invalidation log entries
        - Pagination info
    """
    try:
        query = select(CompilationInvalidationLog)

        if connection_id is not None:
            query = query.where(CompilationInvalidationLog.connection_id == connection_id)

        result = await db.execute(
            query.order_by(CompilationInvalidationLog.invalidated_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        log_entries = result.fetchall()

        has_more = len(log_entries) > limit
        if has_more:
            log_entries = log_entries[:limit]

        entries = []
        for entry_tuple in log_entries:
            entry = entry_tuple[0]
            entries.append({
                "id": entry.id,
                "connection_id": entry.connection_id,
                "table_name": entry.table_name,
                "invalidation_reason": entry.invalidation_reason,
                "plans_invalidated": entry.plans_invalidated,
                "statements_invalidated": entry.statements_invalidated,
                "invalidated_at": entry.invalidated_at.isoformat(),
            })

        return {
            "success": True,
            "entries": entries,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            },
        }

    except Exception as e:
        logger.error(f"Error getting invalidation log: {e}")
        return {
            "success": False,
            "error": str(e),
        }
