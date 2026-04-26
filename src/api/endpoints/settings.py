"""System settings endpoints for Database Guru"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import SystemSettingsResponse, SystemSettingsUpdateRequest
from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.config.settings import Settings
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
            query_quality_level=50,  # Balanced default (0-100 scale)
            # Semantic Understanding Settings (all enabled by default)
            enable_intent_classification=True,  # Phase 1
            enable_dynamic_examples=True,  # Phase 2
            enable_semantic_validation=True,  # Phase 3
            # Per-Task Model Configuration (defaults to None = use default model)
            model_sql_generation=None,
            model_narratives=None,
            model_query_planning=None,
            model_error_correction=None,
            # Per-Task Timeouts (seconds)
            timeout_sql_generation=30,
            timeout_narratives=15,
            timeout_query_planning=20,
            timeout_error_correction=15,
            # Small Model Optimization Feature Flags
            enable_query_templates=True,
            enable_location_preprocessing=True,
            # Prompt Optimization (Phase 2.2)
            enable_prompt_optimization=False,  # OFF by default, user opt-in
            prompt_model_size="auto",
            enable_schema_compression=True,
            max_schema_tables=10,
            enable_example_selection=True,
            max_few_shot_examples=3,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info("Created default system settings")

    return settings


@router.get("/", response_model=SystemSettingsResponse)
async def get_app_settings(
    db: AsyncSession = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
):
    """
    Get current system settings

    Returns the singleton SystemSettings record with configuration for:
    - Auto-learning enabled/disabled
    - Confidence threshold (0.0-1.0)
    - Apply mode (immediate/deferred)
    - Test before learning
    - Audit logging settings
    - require_auth: whether the server requires authentication
    """
    try:
        settings = await get_or_create_settings(db)
        response = SystemSettingsResponse.model_validate(settings)
        response.require_auth = app_settings.REQUIRE_AUTH
        # Surface observability config so the admin UI can render deep-links
        # and conditionally enable the Health/metrics views (Phase 24).
        response.metrics_enabled = app_settings.METRICS_ENABLED
        response.metrics_endpoint_exposed = app_settings.METRICS_EXPOSE_ENDPOINT
        response.metrics_public_url = app_settings.METRICS_PUBLIC_URL or None
        response.otel_enabled = app_settings.OTEL_ENABLED
        response.otel_service_name = app_settings.OTEL_SERVICE_NAME or None
        response.otel_traces_sampler_ratio = app_settings.OTEL_TRACES_SAMPLER_RATIO
        response.jaeger_ui_url = app_settings.JAEGER_UI_URL or None
        response.grafana_url = app_settings.GRAFANA_URL or None
        response.admin_ui_enabled = app_settings.ADMIN_UI_ENABLED

        # Auth hardening flags (read-only) — see PASSWORD_AUTH_HARDENING_PLAN.md.
        response.auth_token_versioning_enabled = app_settings.AUTH_TOKEN_VERSIONING_ENABLED
        response.auth_invalidate_tokens_on_deactivate = app_settings.AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE
        response.auth_invalidate_tokens_on_logout = app_settings.AUTH_INVALIDATE_TOKENS_ON_LOGOUT
        response.auth_rate_limit_change_password = app_settings.AUTH_RATE_LIMIT_CHANGE_PASSWORD
        response.auth_change_password_per_user_per_minute = app_settings.AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE
        response.auth_rate_limit_login_lockout_enabled = app_settings.AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED
        response.auth_login_lockout_threshold = app_settings.AUTH_LOGIN_LOCKOUT_THRESHOLD
        response.auth_login_lockout_window_seconds = app_settings.AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS
        response.auth_password_reset_mode = app_settings.AUTH_PASSWORD_RESET_MODE
        response.auth_password_reset_token_ttl_minutes = app_settings.AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES
        response.auth_password_reset_base_url = app_settings.AUTH_PASSWORD_RESET_BASE_URL or None
        response.auth_password_history_depth = app_settings.AUTH_PASSWORD_HISTORY_DEPTH
        response.auth_require_admin_quorum = app_settings.AUTH_REQUIRE_ADMIN_QUORUM
        return response
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

        # Invalidate model router cache if model settings changed
        model_fields = ['model_sql_generation', 'model_narratives',
                        'model_query_planning', 'model_error_correction',
                        'timeout_sql_generation', 'timeout_narratives',
                        'timeout_query_planning', 'timeout_error_correction']
        if any(field in update_data for field in model_fields):
            from src.llm.model_router import invalidate_model_router
            invalidate_model_router()
            logger.info("Invalidated model router cache due to settings change")

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
    - query_quality_level: 50
    - enable_intent_classification: true
    - enable_dynamic_examples: true
    - enable_semantic_validation: true
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
        settings.query_quality_level = 50
        # Semantic Understanding Settings
        settings.enable_intent_classification = True
        settings.enable_dynamic_examples = True
        settings.enable_semantic_validation = True
        # Per-Task Model Configuration (reset to defaults)
        settings.model_sql_generation = None
        settings.model_narratives = None
        settings.model_query_planning = None
        settings.model_error_correction = None
        # Per-Task Timeouts
        settings.timeout_sql_generation = 30
        settings.timeout_narratives = 15
        settings.timeout_query_planning = 20
        settings.timeout_error_correction = 15
        # Small Model Optimization Feature Flags
        settings.enable_query_templates = True
        settings.enable_location_preprocessing = True
        # Prompt Optimization (Phase 2.2)
        settings.enable_prompt_optimization = False  # OFF by default
        settings.prompt_model_size = "auto"
        settings.enable_schema_compression = True
        settings.max_schema_tables = 10
        settings.enable_example_selection = True
        settings.max_few_shot_examples = 3

        # Invalidate model router cache
        from src.llm.model_router import invalidate_model_router
        invalidate_model_router()

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
