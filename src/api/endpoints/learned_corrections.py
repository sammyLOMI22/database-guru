"""API endpoints for managing learned corrections"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from src.database.connection import get_db
from src.database.models import LearnedCorrection
from src.llm.correction_learner import CorrectionLearner
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learned-corrections", tags=["learned-corrections"])


# Response models
class LearnedCorrectionResponse(BaseModel):
    id: int
    error_type: str
    error_pattern: str
    database_type: str
    original_sql: str
    original_error: str
    corrected_sql: str
    correction_description: Optional[str]
    table_pattern: Optional[str]
    column_pattern: Optional[str]
    times_applied: int
    success_rate: float
    confidence_score: float
    learned_at: str
    last_applied_at: Optional[str]

    class Config:
        from_attributes = True


class LearningStatsResponse(BaseModel):
    total_corrections: int
    by_error_type: dict
    top_corrections: List[dict]
    learning_enabled: bool


class DeleteCorrectionRequest(BaseModel):
    correction_id: int


@router.get("/", response_model=List[LearnedCorrectionResponse])
async def get_learned_corrections(
    db: Session = Depends(get_db),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    database_type: Optional[str] = Query(None, description="Filter by database type"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    Get all learned corrections with optional filters

    Args:
        error_type: Filter by error type (optional)
        database_type: Filter by database type (optional)
        min_confidence: Minimum confidence score (default: 0.0)
        limit: Maximum number of results (default: 100)

    Returns:
        List of learned corrections
    """
    try:
        query = db.query(LearnedCorrection).filter(
            LearnedCorrection.confidence_score >= min_confidence
        )

        if error_type:
            query = query.filter(LearnedCorrection.error_type == error_type)

        if database_type:
            query = query.filter(LearnedCorrection.database_type == database_type)

        corrections = query.order_by(
            LearnedCorrection.confidence_score.desc(),
            LearnedCorrection.times_applied.desc()
        ).limit(limit).all()

        # Convert to response model
        results = []
        for correction in corrections:
            results.append(LearnedCorrectionResponse(
                id=correction.id,
                error_type=correction.error_type,
                error_pattern=correction.error_pattern,
                database_type=correction.database_type,
                original_sql=correction.original_sql,
                original_error=correction.original_error,
                corrected_sql=correction.corrected_sql,
                correction_description=correction.correction_description,
                table_pattern=correction.table_pattern,
                column_pattern=correction.column_pattern,
                times_applied=correction.times_applied,
                success_rate=correction.success_rate,
                confidence_score=correction.confidence_score,
                learned_at=correction.learned_at.isoformat(),
                last_applied_at=correction.last_applied_at.isoformat() if correction.last_applied_at else None
            ))

        return results

    except Exception as e:
        logger.error(f"Failed to get learned corrections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{correction_id}", response_model=LearnedCorrectionResponse)
async def get_correction_by_id(
    correction_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific learned correction by ID

    Args:
        correction_id: ID of the correction

    Returns:
        Learned correction details
    """
    try:
        correction = db.query(LearnedCorrection).filter(
            LearnedCorrection.id == correction_id
        ).first()

        if not correction:
            raise HTTPException(status_code=404, detail="Correction not found")

        return LearnedCorrectionResponse(
            id=correction.id,
            error_type=correction.error_type,
            error_pattern=correction.error_pattern,
            database_type=correction.database_type,
            original_sql=correction.original_sql,
            original_error=correction.original_error,
            corrected_sql=correction.corrected_sql,
            correction_description=correction.correction_description,
            table_pattern=correction.table_pattern,
            column_pattern=correction.column_pattern,
            times_applied=correction.times_applied,
            success_rate=correction.success_rate,
            confidence_score=correction.confidence_score,
            learned_at=correction.learned_at.isoformat(),
            last_applied_at=correction.last_applied_at.isoformat() if correction.last_applied_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get correction {correction_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=LearningStatsResponse)
async def get_learning_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the learning system

    Returns:
        Learning statistics including total corrections, breakdown by type, and top corrections
    """
    try:
        learner = CorrectionLearner(db_session=db, enable_learning=True)
        stats = await learner.get_learning_stats()

        return LearningStatsResponse(
            total_corrections=stats["total_corrections"],
            by_error_type=stats["by_error_type"],
            top_corrections=stats["top_corrections"],
            learning_enabled=stats["learning_enabled"]
        )

    except Exception as e:
        logger.error(f"Failed to get learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{correction_id}")
async def delete_correction(
    correction_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a learned correction

    Args:
        correction_id: ID of the correction to delete

    Returns:
        Success message
    """
    try:
        correction = db.query(LearnedCorrection).filter(
            LearnedCorrection.id == correction_id
        ).first()

        if not correction:
            raise HTTPException(status_code=404, detail="Correction not found")

        db.delete(correction)
        db.commit()

        logger.info(f"Deleted correction {correction_id}")

        return {
            "success": True,
            "message": f"Correction {correction_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete correction {correction_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_all_corrections(
    db: Session = Depends(get_db),
    confirm: bool = Query(False, description="Must be true to confirm reset")
):
    """
    Reset all learned corrections (DANGEROUS - requires confirmation)

    Args:
        confirm: Must be True to confirm the reset

    Returns:
        Success message with count of deleted corrections
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset all corrections"
        )

    try:
        count = db.query(LearnedCorrection).count()
        db.query(LearnedCorrection).delete()
        db.commit()

        logger.warning(f"Reset all learned corrections (deleted {count} corrections)")

        return {
            "success": True,
            "message": f"Reset complete - deleted {count} corrections",
            "deleted_count": count
        }

    except Exception as e:
        logger.error(f"Failed to reset corrections: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/similar")
async def search_similar_corrections(
    error_type: str = Query(..., description="Error type to search for"),
    database_type: str = Query(..., description="Database type"),
    error_message: str = Query(..., description="Error message to match against"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Search for corrections similar to a given error

    Args:
        error_type: Type of error
        database_type: Database type
        error_message: Error message to find similar corrections for
        limit: Maximum results to return

    Returns:
        List of similar corrections
    """
    try:
        from src.llm.self_correcting_agent import ErrorType

        # Convert string to ErrorType enum
        try:
            error_type_enum = ErrorType(error_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid error_type. Must be one of: {[e.value for e in ErrorType]}"
            )

        learner = CorrectionLearner(db_session=db, enable_learning=True)
        corrections = await learner.find_applicable_corrections(
            error_type=error_type_enum,
            error_message=error_message,
            database_type=database_type,
            limit=limit
        )

        return {
            "success": True,
            "count": len(corrections),
            "corrections": corrections
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search for similar corrections: {e}")
        raise HTTPException(status_code=500, detail=str(e))
