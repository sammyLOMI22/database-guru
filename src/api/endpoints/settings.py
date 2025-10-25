"""System settings endpoints for Database Guru"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import SystemSettingsResponse, SystemSettingsUpdateRequest
from src.api.dependencies import get_db
from src.database.models import SystemSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


async def get_or_create_settings(db: AsyncSession) -> SystemSettings:
    """Get system settings or create default if not exists (singleton pattern)"""
    result = await db.execute(select(SystemSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = SystemSettings(
            auto_learning_enabled=False,
            confidence_threshold=0.80,
            apply_mode="immediate",
            test_before_learning=True,
            validation_mode="strict",
            require_result_comparison=True,
            enable_audit_log=True,
            max_audit_log_days=90,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info("Created default system settings")

    return settings


@router.get("/", response_model=SystemSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """
    Get current system settings

    Returns the singleton SystemSettings record with configuration for:
    - Auto-learning enabled/disabled
    - Confidence threshold (0.0-1.0)
    - Apply mode (immediate/deferred)
    - Test before learning
    - Audit logging settings
    """
    try:
        settings = await get_or_create_settings(db)
        return settings
    except Exception as e:
        logger.error(f"Failed to get settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@router.put("/", response_model=SystemSettingsResponse)
async def update_settings(
    request: SystemSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update system settings

    Only updates the fields that are provided (partial update).
    All fields are optional.

    Example:
    ```json
    {
        "auto_learning_enabled": true,
        "confidence_threshold": 0.85
    }
    ```
    """
    try:
        settings = await get_or_create_settings(db)

        # Update only provided fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

        await db.commit()
        await db.refresh(settings)

        logger.info(f"Updated system settings: {update_data}")
        return settings

    except Exception as e:
        logger.error(f"Failed to update settings: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.post("/reset", response_model=SystemSettingsResponse)
async def reset_settings(db: AsyncSession = Depends(get_db)):
    """
    Reset system settings to defaults

    Resets all settings to their default values:
    - auto_learning_enabled: false
    - confidence_threshold: 0.80
    - apply_mode: "immediate"
    - test_before_learning: true
    - validation_mode: "strict"
    - require_result_comparison: true
    - enable_audit_log: true
    - max_audit_log_days: 90
    """
    try:
        settings = await get_or_create_settings(db)

        # Reset to defaults
        settings.auto_learning_enabled = False
        settings.confidence_threshold = 0.80
        settings.apply_mode = "immediate"
        settings.test_before_learning = True
        settings.validation_mode = "strict"
        settings.require_result_comparison = True
        settings.enable_audit_log = True
        settings.max_audit_log_days = 90

        await db.commit()
        await db.refresh(settings)

        logger.info("Reset system settings to defaults")
        return settings

    except Exception as e:
        logger.error(f"Failed to reset settings: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset settings: {str(e)}"
        )
