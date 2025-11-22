"""Mapping management endpoints for viewing and managing learned patterns"""
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, desc, func, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.api.dependencies.common import get_db
from src.llm.mapping_cache import get_mapping_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mappings", tags=["Mappings"])


# ============================================================================
# Response Schemas
# ============================================================================

class ColumnMappingResponse(BaseModel):
    """Column mapping details"""
    id: int
    source_column: str
    target_column: str
    table_name: Optional[str]
    connection_name: Optional[str]
    database_type: str
    description: Optional[str]
    confidence_score: float
    times_applied: int
    success_rate: float
    created_by: str
    created_at: datetime
    last_applied_at: Optional[datetime]

    class Config:
        from_attributes = True


class TableMappingResponse(BaseModel):
    """Table mapping details"""
    id: int
    source_table: str
    target_table: str
    connection_name: Optional[str]
    database_type: str
    mapping_type: str
    description: Optional[str]
    confidence_score: float
    times_applied: int
    success_rate: float
    created_by: str
    created_at: datetime
    last_applied_at: Optional[datetime]

    class Config:
        from_attributes = True


class ResultPatternResponse(BaseModel):
    """Result validation pattern details"""
    id: int
    pattern_type: str
    pattern_description: str
    matching_criteria: Dict[str, Any]
    action: str
    suggestion: Optional[str]
    times_triggered: int
    times_helpful: int
    confidence_score: float
    created_at: datetime
    last_triggered_at: Optional[datetime]

    class Config:
        from_attributes = True


class MappingStatsResponse(BaseModel):
    """Statistics for mappings"""
    total_mappings: int
    total_applications: int
    average_success_rate: float
    most_used: List[Dict[str, Any]]
    by_database_type: Dict[str, int]
    by_connection: Dict[str, int]


class PatternStatsResponse(BaseModel):
    """Statistics for result patterns"""
    total_patterns: int
    total_triggers: int
    total_helpful: int
    helpfulness_rate: float
    by_type: Dict[str, int]
    by_action: Dict[str, int]


# ============================================================================
# Column Mapping Endpoints
# ============================================================================

@router.get("/columns", response_model=List[ColumnMappingResponse])
async def get_column_mappings(
    connection_name: Optional[str] = Query(None, description="Filter by connection name"),
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    database_type: Optional[str] = Query(None, description="Filter by database type"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    List learned column mappings with optional filtering

    Returns column name mappings learned from user feedback, sorted by
    most recently used.
    """
    try:
        # Build query with filters
        conditions = []
        params = {"limit": limit, "offset": offset}

        if connection_name:
            conditions.append("connection_name = :connection_name")
            params["connection_name"] = connection_name

        if table_name:
            conditions.append("table_name = :table_name")
            params["table_name"] = table_name.lower()

        if database_type:
            conditions.append("database_type = :database_type")
            params["database_type"] = database_type.lower()

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT
                id,
                source_column,
                target_column,
                table_name,
                connection_name,
                database_type,
                description,
                confidence_score,
                times_applied,
                success_rate,
                created_by,
                created_at,
                last_applied_at
            FROM column_mappings
            {where_clause}
            ORDER BY last_applied_at DESC NULLS LAST, created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(query, params)
        rows = result.fetchall()

        mappings = []
        for row in rows:
            mappings.append(ColumnMappingResponse(
                id=row[0],
                source_column=row[1],
                target_column=row[2],
                table_name=row[3],
                connection_name=row[4],
                database_type=row[5],
                description=row[6],
                confidence_score=row[7],
                times_applied=row[8],
                success_rate=row[9],
                created_by=row[10],
                created_at=row[11],
                last_applied_at=row[12]
            ))

        logger.info(
            f"Retrieved {len(mappings)} column mappings "
            f"(connection={connection_name}, table={table_name}, db_type={database_type})"
        )

        return mappings

    except Exception as e:
        logger.error(f"Failed to get column mappings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get column mappings: {str(e)}"
        )


@router.delete("/columns/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a column mapping

    Removes the learned column mapping from the system. Future queries
    will no longer apply this mapping.
    """
    try:
        # Check if mapping exists
        check_query = text("SELECT id FROM column_mappings WHERE id = :id")
        result = await db.execute(check_query, {"id": mapping_id})

        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Column mapping {mapping_id} not found"
            )

        # Delete mapping
        delete_query = text("DELETE FROM column_mappings WHERE id = :id")
        await db.execute(delete_query, {"id": mapping_id})
        await db.commit()

        # Invalidate all column mapping caches (we don't know which connection/db_type was affected)
        cache = get_mapping_cache()
        cache.invalidate_pattern("col_mappings:*")
        logger.debug(f"🗑️  Invalidated all column mapping caches after deletion")

        logger.info(f"Deleted column mapping: id={mapping_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete column mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete column mapping: {str(e)}"
        )


@router.get("/columns/stats", response_model=MappingStatsResponse)
async def get_column_mapping_stats(
    database_type: Optional[str] = Query(None, description="Filter by database type"),
    connection_name: Optional[str] = Query(None, description="Filter by connection name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get column mapping statistics

    Returns aggregated statistics about learned column mappings including
    total count, applications, success rates, and breakdowns by database type.
    """
    try:
        # Build filter conditions
        conditions = []
        params = {}

        if database_type:
            conditions.append("database_type = :database_type")
            params["database_type"] = database_type.lower()

        if connection_name:
            conditions.append("connection_name = :connection_name")
            params["connection_name"] = connection_name

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get total mappings and applications
        total_query = text(f"""
            SELECT
                COUNT(*) as total_mappings,
                COALESCE(SUM(times_applied), 0) as total_applications,
                COALESCE(AVG(success_rate), 0.0) as avg_success_rate
            FROM column_mappings
            {where_clause}
        """)

        result = await db.execute(total_query, params)
        row = result.fetchone()

        total_mappings = row[0] or 0
        total_applications = row[1] or 0
        avg_success_rate = row[2] or 0.0

        # Get most used mappings
        most_used_query = text(f"""
            SELECT
                source_column,
                target_column,
                table_name,
                connection_name,
                times_applied
            FROM column_mappings
            {where_clause}
            ORDER BY times_applied DESC
            LIMIT 10
        """)

        result = await db.execute(most_used_query, params)
        most_used = []
        for row in result.fetchall():
            most_used.append({
                "source": row[0],
                "target": row[1],
                "table": row[2],
                "connection": row[3],
                "times_applied": row[4]
            })

        # Get breakdown by database type
        by_db_query = text(f"""
            SELECT database_type, COUNT(*) as count
            FROM column_mappings
            {where_clause}
            GROUP BY database_type
        """)

        result = await db.execute(by_db_query, params)
        by_database_type = {row[0]: row[1] for row in result.fetchall()}

        # Get breakdown by connection
        by_conn_query = text(f"""
            SELECT connection_name, COUNT(*) as count
            FROM column_mappings
            {where_clause}
            GROUP BY connection_name
        """)

        result = await db.execute(by_conn_query, params)
        by_connection = {row[0] or "global": row[1] for row in result.fetchall()}

        return MappingStatsResponse(
            total_mappings=total_mappings,
            total_applications=total_applications,
            average_success_rate=round(avg_success_rate, 3),
            most_used=most_used,
            by_database_type=by_database_type,
            by_connection=by_connection
        )

    except Exception as e:
        logger.error(f"Failed to get column mapping stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# ============================================================================
# Table Mapping Endpoints
# ============================================================================

@router.get("/tables", response_model=List[TableMappingResponse])
async def get_table_mappings(
    connection_name: Optional[str] = Query(None, description="Filter by connection name"),
    database_type: Optional[str] = Query(None, description="Filter by database type"),
    mapping_type: Optional[str] = Query(None, description="Filter by mapping type (alias, synonym, etc.)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    List learned table mappings with optional filtering

    Returns table name mappings learned from user feedback, sorted by
    most recently used.
    """
    try:
        # Build query with filters
        conditions = []
        params = {"limit": limit, "offset": offset}

        if connection_name:
            conditions.append("connection_name = :connection_name")
            params["connection_name"] = connection_name

        if database_type:
            conditions.append("database_type = :database_type")
            params["database_type"] = database_type.lower()

        if mapping_type:
            conditions.append("mapping_type = :mapping_type")
            params["mapping_type"] = mapping_type

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT
                id,
                source_table,
                target_table,
                connection_name,
                database_type,
                mapping_type,
                description,
                confidence_score,
                times_applied,
                success_rate,
                created_by,
                created_at,
                last_applied_at
            FROM table_mappings
            {where_clause}
            ORDER BY last_applied_at DESC NULLS LAST, created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(query, params)
        rows = result.fetchall()

        mappings = []
        for row in rows:
            mappings.append(TableMappingResponse(
                id=row[0],
                source_table=row[1],
                target_table=row[2],
                connection_name=row[3],
                database_type=row[4],
                mapping_type=row[5],
                description=row[6],
                confidence_score=row[7],
                times_applied=row[8],
                success_rate=row[9],
                created_by=row[10],
                created_at=row[11],
                last_applied_at=row[12]
            ))

        logger.info(
            f"Retrieved {len(mappings)} table mappings "
            f"(connection={connection_name}, db_type={database_type}, type={mapping_type})"
        )

        return mappings

    except Exception as e:
        logger.error(f"Failed to get table mappings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table mappings: {str(e)}"
        )


@router.delete("/tables/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a table mapping

    Removes the learned table mapping from the system. Future queries
    will no longer apply this mapping.
    """
    try:
        # Check if mapping exists
        check_query = text("SELECT id FROM table_mappings WHERE id = :id")
        result = await db.execute(check_query, {"id": mapping_id})

        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table mapping {mapping_id} not found"
            )

        # Delete mapping
        delete_query = text("DELETE FROM table_mappings WHERE id = :id")
        await db.execute(delete_query, {"id": mapping_id})
        await db.commit()

        # Invalidate all table mapping caches (we don't know which connection/db_type was affected)
        cache = get_mapping_cache()
        cache.invalidate_pattern("tbl_mappings:*")
        logger.debug(f"🗑️  Invalidated all table mapping caches after deletion")

        logger.info(f"Deleted table mapping: id={mapping_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete table mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete table mapping: {str(e)}"
        )


@router.get("/tables/stats", response_model=MappingStatsResponse)
async def get_table_mapping_stats(
    database_type: Optional[str] = Query(None, description="Filter by database type"),
    connection_name: Optional[str] = Query(None, description="Filter by connection name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get table mapping statistics

    Returns aggregated statistics about learned table mappings including
    total count, applications, success rates, and breakdowns by database type.
    """
    try:
        # Build filter conditions
        conditions = []
        params = {}

        if database_type:
            conditions.append("database_type = :database_type")
            params["database_type"] = database_type.lower()

        if connection_name:
            conditions.append("connection_name = :connection_name")
            params["connection_name"] = connection_name

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get total mappings and applications
        total_query = text(f"""
            SELECT
                COUNT(*) as total_mappings,
                COALESCE(SUM(times_applied), 0) as total_applications,
                COALESCE(AVG(success_rate), 0.0) as avg_success_rate
            FROM table_mappings
            {where_clause}
        """)

        result = await db.execute(total_query, params)
        row = result.fetchone()

        total_mappings = row[0] or 0
        total_applications = row[1] or 0
        avg_success_rate = row[2] or 0.0

        # Get most used mappings
        most_used_query = text(f"""
            SELECT
                source_table,
                target_table,
                connection_name,
                mapping_type,
                times_applied
            FROM table_mappings
            {where_clause}
            ORDER BY times_applied DESC
            LIMIT 10
        """)

        result = await db.execute(most_used_query, params)
        most_used = []
        for row in result.fetchall():
            most_used.append({
                "source": row[0],
                "target": row[1],
                "connection": row[2],
                "type": row[3],
                "times_applied": row[4]
            })

        # Get breakdown by database type
        by_db_query = text(f"""
            SELECT database_type, COUNT(*) as count
            FROM table_mappings
            {where_clause}
            GROUP BY database_type
        """)

        result = await db.execute(by_db_query, params)
        by_database_type = {row[0]: row[1] for row in result.fetchall()}

        # Get breakdown by connection
        by_conn_query = text(f"""
            SELECT connection_name, COUNT(*) as count
            FROM table_mappings
            {where_clause}
            GROUP BY connection_name
        """)

        result = await db.execute(by_conn_query, params)
        by_connection = {row[0] or "global": row[1] for row in result.fetchall()}

        return MappingStatsResponse(
            total_mappings=total_mappings,
            total_applications=total_applications,
            average_success_rate=round(avg_success_rate, 3),
            most_used=most_used,
            by_database_type=by_database_type,
            by_connection=by_connection
        )

    except Exception as e:
        logger.error(f"Failed to get table mapping stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# ============================================================================
# Result Validation Pattern Endpoints
# ============================================================================

@router.get("/patterns", response_model=List[ResultPatternResponse])
async def get_result_patterns(
    pattern_type: Optional[str] = Query(
        None,
        description="Filter by pattern type (empty_result, missing_data, suspicious_values)"
    ),
    action: Optional[str] = Query(None, description="Filter by action (warn_user, suggest_fix, etc.)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    List learned result validation patterns with optional filtering

    Returns result validation patterns learned from user feedback, sorted by
    most recently triggered.
    """
    try:
        # Build query with filters
        conditions = []
        params = {"limit": limit, "offset": offset}

        if pattern_type:
            conditions.append("pattern_type = :pattern_type")
            params["pattern_type"] = pattern_type

        if action:
            conditions.append("action = :action")
            params["action"] = action

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = text(f"""
            SELECT
                id,
                pattern_type,
                pattern_description,
                matching_criteria,
                action,
                suggestion,
                times_triggered,
                times_helpful,
                confidence_score,
                created_at,
                last_triggered_at
            FROM result_validation_patterns
            {where_clause}
            ORDER BY last_triggered_at DESC NULLS LAST, created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(query, params)
        rows = result.fetchall()

        patterns = []
        for row in rows:
            # Parse JSON matching criteria
            try:
                matching_criteria = json.loads(row[3]) if row[3] else {}
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in matching_criteria for pattern {row[0]}")
                matching_criteria = {}

            patterns.append(ResultPatternResponse(
                id=row[0],
                pattern_type=row[1],
                pattern_description=row[2],
                matching_criteria=matching_criteria,
                action=row[4],
                suggestion=row[5],
                times_triggered=row[6],
                times_helpful=row[7],
                confidence_score=row[8],
                created_at=row[9],
                last_triggered_at=row[10]
            ))

        logger.info(
            f"Retrieved {len(patterns)} result patterns "
            f"(type={pattern_type}, action={action})"
        )

        return patterns

    except Exception as e:
        logger.error(f"Failed to get result patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get result patterns: {str(e)}"
        )


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a result validation pattern

    Removes the learned pattern from the system. Future queries will
    no longer trigger this validation pattern.
    """
    try:
        # Check if pattern exists
        check_query = text("SELECT id FROM result_validation_patterns WHERE id = :id")
        result = await db.execute(check_query, {"id": pattern_id})

        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result pattern {pattern_id} not found"
            )

        # Delete pattern
        delete_query = text("DELETE FROM result_validation_patterns WHERE id = :id")
        await db.execute(delete_query, {"id": pattern_id})
        await db.commit()

        # Invalidate all result pattern caches
        cache = get_mapping_cache()
        cache.invalidate_pattern("result_patterns:*")
        logger.debug(f"🗑️  Invalidated all result pattern caches after deletion")

        logger.info(f"Deleted result pattern: id={pattern_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete result pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete result pattern: {str(e)}"
        )


@router.post("/patterns/{pattern_id}/helpful", status_code=status.HTTP_200_OK)
async def mark_pattern_helpful(
    pattern_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a result validation pattern as helpful

    Increments the helpful counter for a pattern, indicating that it
    provided useful validation to the user.
    """
    try:
        # Check if pattern exists
        check_query = text("SELECT id FROM result_validation_patterns WHERE id = :id")
        result = await db.execute(check_query, {"id": pattern_id})

        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result pattern {pattern_id} not found"
            )

        # Increment helpful counter
        update_query = text("""
            UPDATE result_validation_patterns
            SET times_helpful = times_helpful + 1
            WHERE id = :id
        """)
        await db.execute(update_query, {"id": pattern_id})
        await db.commit()

        logger.info(f"Marked pattern {pattern_id} as helpful")

        return {"message": "Pattern marked as helpful", "pattern_id": pattern_id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to mark pattern helpful: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark pattern helpful: {str(e)}"
        )


@router.get("/patterns/stats", response_model=PatternStatsResponse)
async def get_result_pattern_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get result validation pattern statistics

    Returns aggregated statistics about learned patterns including
    total count, triggers, helpfulness rate, and breakdowns by type.
    """
    try:
        # Get total patterns and triggers
        total_query = text("""
            SELECT
                COUNT(*) as total_patterns,
                COALESCE(SUM(times_triggered), 0) as total_triggers,
                COALESCE(SUM(times_helpful), 0) as total_helpful
            FROM result_validation_patterns
        """)

        result = await db.execute(total_query)
        row = result.fetchone()

        total_patterns = row[0] or 0
        total_triggers = row[1] or 0
        total_helpful = row[2] or 0

        helpfulness_rate = (
            (total_helpful / total_triggers * 100) if total_triggers > 0 else 0.0
        )

        # Get breakdown by type
        by_type_query = text("""
            SELECT pattern_type, COUNT(*) as count
            FROM result_validation_patterns
            GROUP BY pattern_type
        """)

        result = await db.execute(by_type_query)
        by_type = {row[0]: row[1] for row in result.fetchall()}

        # Get breakdown by action
        by_action_query = text("""
            SELECT action, COUNT(*) as count
            FROM result_validation_patterns
            GROUP BY action
        """)

        result = await db.execute(by_action_query)
        by_action = {row[0]: row[1] for row in result.fetchall()}

        return PatternStatsResponse(
            total_patterns=total_patterns,
            total_triggers=total_triggers,
            total_helpful=total_helpful,
            helpfulness_rate=round(helpfulness_rate, 1),
            by_type=by_type,
            by_action=by_action
        )

    except Exception as e:
        logger.error(f"Failed to get result pattern stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
