"""User feedback endpoints for continuous learning"""
import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackApplyRequest,
    FeedbackStatsResponse
)
from src.api.dependencies.common import get_db
from src.database.models import UserFeedback, QueryHistory, DatabaseConnection, SystemSettings
from src.llm.correction_learner import CorrectionLearner
from src.llm.self_correcting_agent import ErrorType, ErrorDiagnostics
from src.llm.feedback_validator import FeedbackValidator
from src.core.executor import SQLExecutor
from src.core.user_db_connector import UserDatabaseConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit user feedback on a query

    Users can:
    - Correct SQL queries
    - Report column/table name issues
    - Flag result problems
    - Provide domain knowledge

    The feedback is stored and can later be applied to the learning system.

    **Smart Auto-Learning (Option 3):**
    If auto-learning is enabled, the system will automatically apply high-confidence feedback:
    - High confidence (≥90%) → Auto-apply immediately
    - Medium confidence (70-89%) → Queue for batch processing (deferred mode)
    - Low confidence (<70%) → Manual review required

    Settings can be configured via /api/settings endpoint.
    """
    try:
        # Verify query exists
        stmt = select(QueryHistory).where(QueryHistory.id == feedback.query_id)
        result = await db.execute(stmt)
        query = result.scalar_one_or_none()

        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query {feedback.query_id} not found"
            )

        # Create feedback record
        feedback_record = UserFeedback(
            query_id=feedback.query_id,
            feedback_type=feedback.feedback_type,
            original_sql=query.generated_sql,
            corrected_sql=feedback.corrected_sql,
            correction_description=feedback.correction_description,
            correction_details=feedback.correction_details,
            user_confidence=feedback.user_confidence,
            user_notes=feedback.user_notes
        )

        db.add(feedback_record)
        await db.commit()
        await db.refresh(feedback_record)

        logger.info(
            f"User feedback submitted: id={feedback_record.id}, "
            f"type={feedback.feedback_type}, query_id={feedback.query_id}, "
            f"confidence={feedback.user_confidence}"
        )

        # Get system settings for auto-learning
        settings_stmt = select(SystemSettings).limit(1)
        settings_result = await db.execute(settings_stmt)
        settings = settings_result.scalar_one_or_none()

        # Auto-learning logic (Option 3: Smart Auto-Learning)
        if settings and settings.auto_learning_enabled and feedback.corrected_sql:
            confidence_threshold = settings.confidence_threshold
            apply_mode = settings.apply_mode
            test_before_learning = settings.test_before_learning

            logger.info(
                f"Auto-learning enabled: threshold={confidence_threshold}, "
                f"mode={apply_mode}, test={test_before_learning}"
            )

            # High confidence: Apply immediately
            if feedback.user_confidence >= 0.90:
                logger.info(
                    f"🚀 High confidence feedback (≥90%), attempting auto-apply... "
                    f"(feedback_id={feedback_record.id})"
                )
                try:
                    # Validate correction if required (ENHANCED VALIDATION)
                    validation_passed = False
                    validation_reason = "Validation skipped"
                    validation_details = None

                    if test_before_learning:
                        logger.info(f"🔍 Validating user correction with comprehensive testing...")

                        # Get security settings
                        allow_destructive = getattr(settings, 'allow_destructive_auto_learn', False)
                        if allow_destructive:
                            logger.warning(
                                "⚠️  DANGER: allow_destructive_auto_learn=True! "
                                "Destructive operations can be auto-learned. This should NEVER be enabled in production!"
                            )

                        validator = FeedbackValidator(db_session=db, allow_destructive=allow_destructive)
                        validation_mode = getattr(settings, 'validation_mode', 'strict')

                        validation_passed, validation_reason, validation_details = await validator.validate_correction(
                            query=query,
                            corrected_sql=feedback.corrected_sql,
                            validation_mode=validation_mode
                        )

                        if not validation_passed:
                            logger.warning(
                                f"⚠️ Auto-apply REJECTED by validator: {validation_reason}\n"
                                f"   Validation details: {validation_details}"
                            )
                            # Store validation failure reason in user notes
                            feedback_record.user_notes = (
                                f"{feedback_record.user_notes or ''}\n\n"
                                f"[AUTO-APPLY REJECTED] {validation_reason}"
                            ).strip()
                            await db.commit()
                        else:
                            logger.info(
                                f"✅ Validation PASSED: {validation_reason}\n"
                                f"   Details: {validation_details}"
                            )
                    else:
                        # Skip validation (not recommended!)
                        validation_passed = True
                        validation_reason = "Validation disabled by settings"
                        logger.warning("⚠️ Validation SKIPPED - test_before_learning is OFF (not recommended)")

                    # Apply to learning system if validation passed
                    if validation_passed:
                        learner = CorrectionLearner(db_session=db, enable_learning=True)

                        # Determine error type
                        error_type = ErrorType.UNKNOWN
                        if query.error_message:
                            error_type = ErrorDiagnostics.categorize_error(query.error_message)

                        # Create learned correction
                        learned_id = await learner.learn_from_correction(
                            error_type=error_type,
                            original_sql=feedback_record.original_sql,
                            original_error=query.error_message or "User-reported issue",
                            corrected_sql=feedback_record.corrected_sql,
                            database_type=query.database_type,
                            was_successful=True
                        )

                        # Update feedback record
                        feedback_record.applied_successfully = True
                        feedback_record.applied_at = datetime.utcnow()
                        feedback_record.learned_correction_id = learned_id

                        await db.commit()
                        await db.refresh(feedback_record)

                        logger.info(
                            f"✨ AUTO-APPLIED: High confidence feedback automatically learned! "
                            f"feedback_id={feedback_record.id}, learned_correction_id={learned_id}"
                        )

                except Exception as auto_apply_error:
                    logger.error(
                        f"⚠️ Auto-apply failed, feedback saved for manual review: {auto_apply_error}",
                        exc_info=True
                    )
                    # Don't raise - just log and continue

            # Medium confidence: Queue for batch processing (deferred mode)
            elif feedback.user_confidence >= 0.70 and apply_mode == "deferred":
                logger.info(
                    f"📋 Medium confidence feedback (70-89%), queued for batch processing "
                    f"(feedback_id={feedback_record.id})"
                )
                # Feedback is already saved, admin can review and apply in batch

            # Low confidence: Manual review required
            else:
                logger.info(
                    f"👁️ Low confidence feedback (<70%), manual review required "
                    f"(feedback_id={feedback_record.id})"
                )

        return FeedbackResponse.model_validate(feedback_record)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.post("/apply", response_model=FeedbackResponse)
async def apply_feedback_to_learning(
    request: FeedbackApplyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply user feedback to the learning system

    This:
    1. Optionally tests the corrected SQL to ensure it works
    2. Adds the correction to the learned_corrections table
    3. Makes the correction available for automatic application in future queries

    The system will now automatically apply this correction when similar errors occur.
    """
    try:
        # Get feedback
        stmt = select(UserFeedback).where(UserFeedback.id == request.feedback_id)
        result = await db.execute(stmt)
        feedback = result.scalar_one_or_none()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {request.feedback_id} not found"
            )

        if feedback.applied_successfully:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback already applied to learning system"
            )

        # Get original query for context
        query = await db.get(QueryHistory, feedback.query_id)

        # Test correction if requested
        tested_successfully = False
        if request.test_before_learning and feedback.corrected_sql:
            logger.info(f"Testing user correction before learning (feedback_id={feedback.id})...")

            # Get active connection
            stmt = select(DatabaseConnection).where(DatabaseConnection.is_active == True)
            result = await db.execute(stmt)
            active_conn = result.scalar_one_or_none()

            if active_conn:
                async with UserDatabaseConnector.get_user_db_session(active_conn) as user_db:
                    executor = SQLExecutor(max_rows=10, timeout_seconds=30)
                    test_result = await executor.execute_query(
                        session=user_db,
                        sql=feedback.corrected_sql
                    )
                    tested_successfully = test_result["success"]

                    if not tested_successfully:
                        error_msg = test_result.get('error', 'Unknown error')
                        logger.warning(
                            f"User correction failed testing: {error_msg} "
                            f"(feedback_id={feedback.id})"
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Corrected SQL failed to execute: {error_msg}"
                        )
            else:
                logger.warning("No active connection for testing correction")

        # Learn from feedback
        learner = CorrectionLearner(db_session=db, enable_learning=True)

        # Determine error type from original query
        error_type = ErrorType.UNKNOWN
        if query.error_message:
            error_type = ErrorDiagnostics.categorize_error(query.error_message)

        # Create learned correction
        learned_id = await learner.learn_from_correction(
            error_type=error_type,
            original_sql=feedback.original_sql,
            original_error=query.error_message or "User-reported issue",
            corrected_sql=feedback.corrected_sql or feedback.original_sql,
            database_type=query.database_type,
            was_successful=True
        )

        # Update feedback record
        feedback.applied_successfully = True
        feedback.applied_at = datetime.utcnow()
        feedback.learned_correction_id = learned_id

        await db.commit()
        await db.refresh(feedback)

        logger.info(
            f"✨ Learned from user feedback: feedback_id={feedback.id}, "
            f"learned_correction_id={learned_id}"
        )

        return FeedbackResponse.model_validate(feedback)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to apply feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply feedback: {str(e)}"
        )


@router.get("/query/{query_id}", response_model=List[FeedbackResponse])
async def get_query_feedback(
    query_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all feedback for a specific query"""
    try:
        stmt = (
            select(UserFeedback)
            .where(UserFeedback.query_id == query_id)
            .order_by(desc(UserFeedback.created_at))
        )
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()

        return [FeedbackResponse.model_validate(f) for f in feedbacks]

    except Exception as e:
        logger.error(f"Failed to get feedback for query {query_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback: {str(e)}"
        )


@router.get("/recent", response_model=List[FeedbackResponse])
async def get_recent_feedback(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get recent feedback submissions"""
    try:
        stmt = (
            select(UserFeedback)
            .order_by(desc(UserFeedback.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()

        return [FeedbackResponse.model_validate(f) for f in feedbacks]

    except Exception as e:
        logger.error(f"Failed to get recent feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent feedback: {str(e)}"
        )


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    """Get feedback statistics"""
    try:
        # Total feedback count
        total_result = await db.execute(select(func.count(UserFeedback.id)))
        total = total_result.scalar() or 0

        # Applied count
        applied_result = await db.execute(
            select(func.count(UserFeedback.id))
            .where(UserFeedback.applied_successfully == True)
        )
        applied = applied_result.scalar() or 0

        # By type
        type_result = await db.execute(
            select(UserFeedback.feedback_type, func.count(UserFeedback.id))
            .group_by(UserFeedback.feedback_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        return FeedbackStatsResponse(
            total_feedback=total,
            applied_to_learning=applied,
            pending=total - applied,
            by_type=by_type
        )

    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a feedback entry"""
    try:
        stmt = select(UserFeedback).where(UserFeedback.id == feedback_id)
        result = await db.execute(stmt)
        feedback = result.scalar_one_or_none()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {feedback_id} not found"
            )

        await db.delete(feedback)
        await db.commit()

        logger.info(f"Feedback deleted: id={feedback_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete feedback: {str(e)}"
        )
