"""Per-Task Model Router

Routes LLM tasks to appropriate models based on task type and user configuration.
This enables using specialized models (like duckdb-nsql for SQL) while using
general-purpose models for other tasks (like narratives).

Usage:
    router = await get_model_router(db_session)
    model = router.get_model_for_task(TaskType.SQL_GENERATION)
    timeout = router.get_timeout_for_task(TaskType.SQL_GENERATION)
    model_size = router.get_model_size(TaskType.SQL_GENERATION)

Part of: Small Model Optimization Phase
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.config.settings import Settings

# Import model size detection from prompt_optimizer (Phase 2.2)
from src.llm.prompt_optimizer import (
    ModelSize,
    get_model_size_for_model,
    get_model_family,
    ModelFamily,
)

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of LLM tasks that can use different models."""
    SQL_GENERATION = "sql_generation"
    NARRATIVES = "narratives"
    QUERY_PLANNING = "query_planning"
    ERROR_CORRECTION = "error_correction"
    # Phase 12: Lineage Intelligence
    LINEAGE_NARRATIVE = "lineage_narrative"
    IMPACT_ANALYSIS = "impact_analysis"
    SCHEMA_HEALTH = "schema_health"
    LINEAGE_CONVERSATION = "lineage_conversation"
    PATTERN_INTELLIGENCE = "pattern_intelligence"


@dataclass
class TaskConfig:
    """Configuration for a specific LLM task."""
    model: str
    timeout: int
    task_type: TaskType

    def __repr__(self) -> str:
        return f"TaskConfig(task={self.task_type.value}, model={self.model}, timeout={self.timeout}s)"


class ModelRouter:
    """
    Routes LLM tasks to appropriate models based on configuration.

    Supports per-task model configuration:
    - SQL Generation: Use specialized SQL models (duckdb-nsql, sqlcoder)
    - Narratives: Use general-purpose models (llama3.2, gemma)
    - Query Planning: Use reasoning-capable models
    - Error Correction: Use code-focused models

    Falls back to default model when per-task model is not configured.
    """

    # Default timeouts per task type (seconds)
    DEFAULT_TIMEOUTS = {
        TaskType.SQL_GENERATION: 30,
        TaskType.NARRATIVES: 15,
        TaskType.QUERY_PLANNING: 20,
        TaskType.ERROR_CORRECTION: 15,
        # Phase 12: Lineage Intelligence
        TaskType.LINEAGE_NARRATIVE: 15,
        TaskType.IMPACT_ANALYSIS: 20,
        TaskType.SCHEMA_HEALTH: 30,
        TaskType.LINEAGE_CONVERSATION: 15,
        TaskType.PATTERN_INTELLIGENCE: 20,
    }

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model_settings: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the model router.

        Args:
            settings: Application settings (for default model)
            model_settings: Per-task model configuration from database
                Expected keys:
                - model_sql_generation, model_narratives, etc.
                - timeout_sql_generation, timeout_narratives, etc.
        """
        self.settings = settings or Settings()
        self.model_settings = model_settings or {}
        self._default_model = self.settings.OLLAMA_MODEL

        logger.info(
            f"ModelRouter initialized: default_model={self._default_model}, "
            f"per_task_config={bool(model_settings)}"
        )

    @property
    def default_model(self) -> str:
        """Get the default model used when no per-task model is configured."""
        return self._default_model

    def get_model_for_task(self, task: TaskType) -> str:
        """
        Get the configured model for a specific task.

        Falls back to default model if per-task model is not configured.

        Args:
            task: The type of LLM task

        Returns:
            Model name to use for this task
        """
        key = f"model_{task.value}"
        per_task_model = self.model_settings.get(key)

        if per_task_model:
            logger.debug(f"Using per-task model for {task.value}: {per_task_model}")
            return per_task_model

        logger.debug(f"Using default model for {task.value}: {self._default_model}")
        return self._default_model

    def get_timeout_for_task(self, task: TaskType) -> int:
        """
        Get the configured timeout for a specific task.

        Falls back to default timeout if per-task timeout is not configured.

        Args:
            task: The type of LLM task

        Returns:
            Timeout in seconds
        """
        key = f"timeout_{task.value}"
        per_task_timeout = self.model_settings.get(key)

        if per_task_timeout is not None:
            return per_task_timeout

        return self.DEFAULT_TIMEOUTS.get(task, 30)

    def get_config_for_task(self, task: TaskType) -> TaskConfig:
        """
        Get the complete configuration for a specific task.

        Args:
            task: The type of LLM task

        Returns:
            TaskConfig with model and timeout
        """
        return TaskConfig(
            model=self.get_model_for_task(task),
            timeout=self.get_timeout_for_task(task),
            task_type=task
        )

    def is_per_task_configured(self, task: TaskType) -> bool:
        """Check if a per-task model is explicitly configured."""
        key = f"model_{task.value}"
        return bool(self.model_settings.get(key))

    def get_model_size(self, task: Optional[TaskType] = None) -> ModelSize:
        """
        Get the model size for a task (or default model).

        Uses the model configured for the task and detects its size
        based on model name patterns (e.g., "7b" → MEDIUM).

        Args:
            task: Optional task type. If None, uses default model.

        Returns:
            ModelSize enum value (SMALL, MEDIUM, or LARGE)
        """
        model = self.get_model_for_task(task) if task else self._default_model
        return get_model_size_for_model(model)

    def get_model_family(self, task: Optional[TaskType] = None) -> ModelFamily:
        """
        Get the model family for a task (or default model).

        Detects the model family (Llama, Qwen, etc.) from the model name.

        Args:
            task: Optional task type. If None, uses default model.

        Returns:
            ModelFamily enum value
        """
        model = self.get_model_for_task(task) if task else self._default_model
        return get_model_family(model)

    def get_all_configs(self) -> Dict[TaskType, TaskConfig]:
        """Get configurations for all task types."""
        return {task: self.get_config_for_task(task) for task in TaskType}

    def to_dict(self) -> Dict[str, Any]:
        """Convert router configuration to dictionary for debugging/logging."""
        return {
            "default_model": self._default_model,
            "default_model_size": self.get_model_size().value,
            "default_model_family": self.get_model_family().value,
            "tasks": {
                task.value: {
                    "model": self.get_model_for_task(task),
                    "timeout": self.get_timeout_for_task(task),
                    "is_custom": self.is_per_task_configured(task),
                    "model_size": self.get_model_size(task).value,
                    "model_family": self.get_model_family(task).value,
                }
                for task in TaskType
            }
        }


# Global router instance (lazy-initialized)
_model_router: Optional[ModelRouter] = None


def get_model_router_sync(
    settings: Optional[Settings] = None,
    model_settings: Optional[Dict[str, Any]] = None
) -> ModelRouter:
    """
    Get a ModelRouter instance synchronously.

    Use this when you don't have access to a database session,
    or when you only need default model behavior.
    """
    global _model_router

    if _model_router is None or model_settings is not None:
        _model_router = ModelRouter(settings, model_settings)

    return _model_router


async def get_model_router(db_session=None) -> ModelRouter:
    """
    Get a ModelRouter instance with database-loaded settings.

    Args:
        db_session: Optional database session for loading settings

    Returns:
        ModelRouter configured with per-task models from database
    """
    global _model_router

    settings = Settings()
    model_settings = {}

    if db_session:
        try:
            # Import here to avoid circular imports
            from src.api.endpoints.settings import get_or_create_settings

            sys_settings = await get_or_create_settings(db_session)

            # Extract model settings from database record
            model_settings = {
                'model_sql_generation': sys_settings.model_sql_generation,
                'model_narratives': sys_settings.model_narratives,
                'model_query_planning': sys_settings.model_query_planning,
                'model_error_correction': sys_settings.model_error_correction,
                'timeout_sql_generation': sys_settings.timeout_sql_generation,
                'timeout_narratives': sys_settings.timeout_narratives,
                'timeout_query_planning': sys_settings.timeout_query_planning,
                'timeout_error_correction': sys_settings.timeout_error_correction,
                # Phase 12: Lineage Intelligence
                'model_lineage_narrative': getattr(sys_settings, 'model_lineage_narrative', None),
                'model_impact_analysis': getattr(sys_settings, 'model_impact_analysis', None),
                'model_schema_health': getattr(sys_settings, 'model_schema_health', None),
                'model_lineage_conversation': getattr(sys_settings, 'model_lineage_conversation', None),
                'model_pattern_intelligence': getattr(sys_settings, 'model_pattern_intelligence', None),
                'timeout_lineage_narrative': getattr(sys_settings, 'timeout_lineage_narrative', 15),
                'timeout_impact_analysis': getattr(sys_settings, 'timeout_impact_analysis', 20),
                'timeout_schema_health': getattr(sys_settings, 'timeout_schema_health', 30),
                'timeout_lineage_conversation': getattr(sys_settings, 'timeout_lineage_conversation', 15),
                'timeout_pattern_intelligence': getattr(sys_settings, 'timeout_pattern_intelligence', 20),
            }

            logger.debug(f"Loaded model settings from database: {model_settings}")

        except Exception as e:
            logger.warning(f"Failed to load model settings from database: {e}")
            # Fall back to defaults

    # Always create a fresh router with current settings
    _model_router = ModelRouter(settings, model_settings)
    return _model_router


def invalidate_model_router():
    """Invalidate the cached model router (call after settings change)."""
    global _model_router
    _model_router = None
    logger.info("Model router cache invalidated")
