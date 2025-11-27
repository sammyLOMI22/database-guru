"""
Index Recommendations API Endpoints

Provides REST API for database index recommendations:
- GET /index-recommendations - List recommendations with filters
- GET /index-recommendations/{id} - Get single recommendation
- GET /index-recommendations/stats - Get statistics
- POST /index-recommendations/analyze - Analyze a query
- PUT /index-recommendations/{id} - Update recommendation status
- DELETE /index-recommendations/{id} - Delete recommendation

Part of Phase 4: Database Index Recommendations
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.services.index_advisor import IndexAdvisor
from src.database.models import IndexRecommendation
from src.models.schemas import (
    IndexRecommendationResponse,
    IndexRecommendationUpdate,
    IndexRecommendationStats,
    AnalyzeSlowQueryRequest,
)
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/index-recommendations", tags=["index-recommendations"])


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[IndexRecommendationResponse])
async def list_recommendations(
    connection_id: Optional[int] = Query(None, description="Filter by connection ID"),
    status: Optional[str] = Query(
        None,
        description="Filter by status",
        regex="^(pending|accepted|rejected|applied|failed)$"
    ),
    priority: Optional[str] = Query(
        None,
        description="Filter by priority",
        regex="^(high|medium|low)$"
    ),
    database_type: Optional[str] = Query(None, description="Filter by database type"),
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
) -> List[IndexRecommendationResponse]:
    """
    List index recommendations with optional filters.

    Supports filtering by:
    - connection_id: Database connection
    - status: pending, accepted, rejected, applied, failed
    - priority: high, medium, low
    - database_type: postgresql, mysql, sqlite
    - table_name: Specific table
    """
    try:
        advisor = IndexAdvisor(db)

        # Build query with filters
        query = select(IndexRecommendation)

        filters = []
        if connection_id is not None:
            filters.append(IndexRecommendation.connection_id == connection_id)
        if status:
            filters.append(IndexRecommendation.status == status)
        if priority:
            filters.append(IndexRecommendation.priority == priority)
        if database_type:
            filters.append(IndexRecommendation.database_type == database_type)
        if table_name:
            filters.append(IndexRecommendation.table_name == table_name)

        if filters:
            from sqlalchemy import and_
            query = query.where(and_(*filters))

        # Order by priority and creation date
        query = query.order_by(
            IndexRecommendation.priority.desc(),
            IndexRecommendation.created_at.desc()
        ).limit(limit).offset(offset)

        result = await db.execute(query)
        recommendations = result.scalars().all()

        return [
            IndexRecommendationResponse.from_orm(rec)
            for rec in recommendations
        ]

    except Exception as e:
        logger.error(f"Error listing recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=IndexRecommendationStats)
async def get_recommendation_stats(
    connection_id: Optional[int] = Query(None, description="Filter by connection ID"),
    db: AsyncSession = Depends(get_db)
) -> IndexRecommendationStats:
    """
    Get statistics about index recommendations.

    Returns counts by status, priority, database type, and performance metrics.
    """
    try:
        advisor = IndexAdvisor(db)
        stats = await advisor.get_recommendation_stats(connection_id=connection_id)

        return IndexRecommendationStats(**stats)

    except Exception as e:
        logger.error(f"Error getting recommendation stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recommendation_id}", response_model=IndexRecommendationResponse)
async def get_recommendation(
    recommendation_id: int,
    db: AsyncSession = Depends(get_db)
) -> IndexRecommendationResponse:
    """
    Get a single index recommendation by ID.
    """
    try:
        query = select(IndexRecommendation).where(
            IndexRecommendation.id == recommendation_id
        )
        result = await db.execute(query)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Recommendation {recommendation_id} not found"
            )

        return IndexRecommendationResponse.from_orm(recommendation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=IndexRecommendationResponse)
async def analyze_slow_query(
    request: AnalyzeSlowQueryRequest,
    db: AsyncSession = Depends(get_db)
) -> IndexRecommendationResponse:
    """
    Analyze a slow query and generate index recommendation.

    This endpoint allows manual triggering of index analysis for any query.
    Set auto_save=true to automatically save the recommendation.
    """
    try:
        advisor = IndexAdvisor(db)

        recommendation = await advisor.analyze_query(
            connection_id=request.connection_id,
            query_sql=request.query_sql,
            execution_time_ms=request.execution_time_ms or 1000.0,
            query_id=None
        )

        if not recommendation:
            raise HTTPException(
                status_code=400,
                detail="No index recommendation could be generated for this query"
            )

        return IndexRecommendationResponse.from_orm(recommendation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{recommendation_id}", response_model=IndexRecommendationResponse)
async def update_recommendation(
    recommendation_id: int,
    update: IndexRecommendationUpdate,
    db: AsyncSession = Depends(get_db)
) -> IndexRecommendationResponse:
    """
    Update recommendation status and metadata.

    Use this to mark recommendations as:
    - accepted: User reviewed and approves
    - rejected: User reviewed and declines
    - applied: Index was created in database
    - failed: Index creation failed
    """
    try:
        # Get existing recommendation
        query = select(IndexRecommendation).where(
            IndexRecommendation.id == recommendation_id
        )
        result = await db.execute(query)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Recommendation {recommendation_id} not found"
            )

        # Update fields
        update_data = update.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(recommendation, field, value)

        # Set applied_at timestamp if status is applied
        if update.status == "applied":
            from datetime import datetime
            recommendation.applied_at = datetime.utcnow()

        await db.commit()
        await db.refresh(recommendation)

        return IndexRecommendationResponse.from_orm(recommendation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{recommendation_id}", status_code=204)
async def delete_recommendation(
    recommendation_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an index recommendation.

    Use this to remove recommendations that are no longer relevant.
    """
    try:
        # Check if recommendation exists
        query = select(IndexRecommendation).where(
            IndexRecommendation.id == recommendation_id
        )
        result = await db.execute(query)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Recommendation {recommendation_id} not found"
            )

        # Delete recommendation
        delete_query = delete(IndexRecommendation).where(
            IndexRecommendation.id == recommendation_id
        )
        await db.execute(delete_query)
        await db.commit()

        logger.info(f"Deleted recommendation {recommendation_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Bulk Operations (Optional - for future enhancement)
# ============================================================================

@router.post("/bulk-update", response_model=dict)
async def bulk_update_recommendations(
    recommendation_ids: List[int],
    status: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Bulk update multiple recommendations at once.

    Useful for batch accepting or rejecting recommendations.
    """
    try:
        updated_count = 0

        for rec_id in recommendation_ids:
            query = select(IndexRecommendation).where(
                IndexRecommendation.id == rec_id
            )
            result = await db.execute(query)
            recommendation = result.scalar_one_or_none()

            if recommendation:
                recommendation.status = status
                updated_count += 1

        await db.commit()

        return {
            "updated": updated_count,
            "requested": len(recommendation_ids)
        }

    except Exception as e:
        logger.error(f"Error bulk updating recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connection/{connection_id}", status_code=204)
async def delete_connection_recommendations(
    connection_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete all recommendations for a specific database connection.

    Use when removing a database connection to clean up orphaned recommendations.
    """
    try:
        delete_query = delete(IndexRecommendation).where(
            IndexRecommendation.connection_id == connection_id
        )
        result = await db.execute(delete_query)
        await db.commit()

        logger.info(
            f"Deleted {result.rowcount} recommendations for connection {connection_id}"
        )

    except Exception as e:
        logger.error(f"Error deleting connection recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
