"""Per-Task Model Router

Routes LLM tasks to appropriate models and providers based on task type
and user configuration. Supports per-task provider routing with fallback
chains that respect data security levels.

Usage:
    router = await get_model_router(db_session)
    model = router.get_model_for_task(TaskType.SQL_GENERATION)
    timeout = router.get_timeout_for_task(TaskType.SQL_GENERATION)
    model_size = router.get_model_size(TaskType.SQL_GENERATION)

    # Provider routing (Phase 15)
    provider_name = router.get_provider_for_task(TaskType.SQL_GENERATION)
    response = await router.execute_with_fallback(
        TaskType.SQL_GENERATION, prompt="SELECT ...", messages=[...]
    )

Part of: Small Model Optimization Phase + Phase 15 LLM Provider Expansion
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

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
    # Phase 20: Migration Toolkit
    MIGRATION_PLANNER = "migration_planner"
    # Phase 22: Performance Guru
    EXPLAIN_ANALYSIS = "explain_analysis"
    # Phase 25: Graph Mode (Neo4j)
    GRAPH_SCHEMA_SUMMARY = "graph_schema_summary"
    CYPHER_GENERATION = "cypher_generation"
    CYPHER_EXPLANATION = "cypher_explanation"
    GRAPH_MODELING_ADVICE = "graph_modeling_advice"


@dataclass
class TaskConfig:
    """Configuration for a specific LLM task."""
    model: str
    timeout: int
    task_type: TaskType
    provider: Optional[str] = None  # Phase 15: provider name (None = use default)
    fallback_chain: list[dict] = field(default_factory=list)  # [{provider, model}]

    def __repr__(self) -> str:
        parts = f"task={self.task_type.value}, model={self.model}, timeout={self.timeout}s"
        if self.provider:
            parts += f", provider={self.provider}"
        return f"TaskConfig({parts})"


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
        # Phase 20: Migration Toolkit
        TaskType.MIGRATION_PLANNER: 30,
        # Phase 22: Performance Guru
        TaskType.EXPLAIN_ANALYSIS: 25,
        # Phase 25: Graph Mode (Neo4j)
        TaskType.GRAPH_SCHEMA_SUMMARY: 15,
        TaskType.CYPHER_GENERATION: 25,
        TaskType.CYPHER_EXPLANATION: 15,
        TaskType.GRAPH_MODELING_ADVICE: 20,
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
                - provider_sql_generation, provider_narratives, etc. (Phase 15)
                - fallback_sql_generation, etc. (Phase 15, list of {provider, model})
        """
        self.settings = settings or Settings()
        self.model_settings = model_settings or {}
        self._default_model = self.settings.OLLAMA_MODEL
        self._default_provider: Optional[str] = self.model_settings.get(
            "default_provider", "ollama"
        )

        logger.info(
            f"ModelRouter initialized: default_model={self._default_model}, "
            f"default_provider={self._default_provider}, "
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

    def get_provider_for_task(self, task: TaskType) -> Optional[str]:
        """Get the configured provider name for a task, or None for default."""
        key = f"provider_{task.value}"
        provider = self.model_settings.get(key)
        if provider:
            logger.debug(f"Using per-task provider for {task.value}: {provider}")
            return provider
        return self._default_provider

    def get_fallback_chain(self, task: TaskType) -> list[dict]:
        """Get the fallback chain for a task.

        Returns list of {provider, model} dicts in priority order.
        """
        key = f"fallback_{task.value}"
        chain = self.model_settings.get(key)
        return chain if isinstance(chain, list) else []

    def get_config_for_task(self, task: TaskType) -> TaskConfig:
        """
        Get the complete configuration for a specific task.

        Args:
            task: The type of LLM task

        Returns:
            TaskConfig with model, timeout, provider, and fallback chain
        """
        return TaskConfig(
            model=self.get_model_for_task(task),
            timeout=self.get_timeout_for_task(task),
            task_type=task,
            provider=self.get_provider_for_task(task),
            fallback_chain=self.get_fallback_chain(task),
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

    async def execute_with_fallback(
        self,
        task: TaskType,
        prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs,
    ) -> "LLMResponse":
        """Execute an LLM call with automatic fallback through the chain.

        Tries the primary provider first, then each fallback in order.
        Respects data security levels — a fallback that violates the
        security level is skipped (never falls "up" to a less-secure tier).

        Args:
            task: Task type for routing.
            prompt: Plain text prompt (for generate-style calls).
            messages: Chat messages list (for chat-style calls).
            **kwargs: Additional arguments passed to the provider.

        Returns:
            LLMResponse from the first successful provider.

        Raises:
            Exception: If all providers in the chain fail.
        """
        from src.llm.providers.registry import (
            get_provider_registry,
            DataSecurityError,
            ProviderNotFoundError,
        )
        from src.llm.providers.base import LLMResponse

        config = self.get_config_for_task(task)
        registry = get_provider_registry()

        # Build ordered list: primary + fallbacks
        attempts: list[tuple[str, Optional[str]]] = [
            (config.provider or self._default_provider or "ollama", config.model)
        ]
        for fb in config.fallback_chain:
            if isinstance(fb, dict):
                attempts.append((fb.get("provider", "ollama"), fb.get("model")))

        last_error: Optional[Exception] = None

        for provider_name, model in attempts:
            try:
                provider = registry.get(provider_name, enforce_security=True)
            except (ProviderNotFoundError, DataSecurityError) as e:
                logger.warning(
                    f"Skipping provider {provider_name!r} for task {task.value}: {e}"
                )
                last_error = e
                continue

            try:
                use_model = model or provider.default_model
                if messages:
                    response = await provider.chat(
                        messages=messages,
                        model=use_model,
                        **kwargs,
                    )
                elif prompt:
                    response = await provider.generate(
                        prompt=prompt,
                        model=use_model,
                        **kwargs,
                    )
                else:
                    raise ValueError("Either prompt or messages must be provided")

                logger.info(
                    f"Task {task.value} completed via provider {provider_name!r} "
                    f"(model={use_model})"
                )
                return response

            except Exception as e:
                logger.warning(
                    f"Provider {provider_name!r} failed for task {task.value}: {e}"
                )
                last_error = e
                continue

        raise last_error or RuntimeError(
            f"No providers available for task {task.value}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert router configuration to dictionary for debugging/logging."""
        return {
            "default_model": self._default_model,
            "default_provider": self._default_provider,
            "default_model_size": self.get_model_size().value,
            "default_model_family": self.get_model_family().value,
            "tasks": {
                task.value: {
                    "model": self.get_model_for_task(task),
                    "provider": self.get_provider_for_task(task),
                    "timeout": self.get_timeout_for_task(task),
                    "is_custom": self.is_per_task_configured(task),
                    "model_size": self.get_model_size(task).value,
                    "model_family": self.get_model_family(task).value,
                    "fallback_chain": self.get_fallback_chain(task),
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
                # Phase 20: Migration Toolkit
                'model_migration_planner': getattr(sys_settings, 'model_migration_planner', None),
                'timeout_migration_planner': getattr(sys_settings, 'timeout_migration_planner', 30),
                # Phase 22: Performance Guru
                'model_explain_analysis': getattr(sys_settings, 'model_explain_analysis', None),
                'timeout_explain_analysis': getattr(sys_settings, 'timeout_explain_analysis', 25),
            }

            logger.debug(f"Loaded model settings from database: {model_settings}")

        except Exception as e:
            logger.warning(f"Failed to load model settings from database: {e}")
            # Fall back to defaults

        # Phase 15: Load per-task provider routing from LLMTaskRouting table
        try:
            from sqlalchemy import select
            from src.database.models import LLMTaskRouting

            result = await db_session.execute(select(LLMTaskRouting))
            routes = result.scalars().all()
            for route in routes:
                model_settings[f"provider_{route.task_type}"] = route.primary_provider
                if route.primary_model:
                    model_settings[f"model_{route.task_type}"] = route.primary_model
                if route.fallback_chain:
                    model_settings[f"fallback_{route.task_type}"] = route.fallback_chain
            if routes:
                logger.debug(f"Loaded {len(routes)} task routing rules from database")
        except Exception as e:
            logger.warning(f"Failed to load task routing from database: {e}")

    # Always create a fresh router with current settings
    _model_router = ModelRouter(settings, model_settings)
    return _model_router


def invalidate_model_router():
    """Invalidate the cached model router (call after settings change)."""
    global _model_router
    _model_router = None
    logger.info("Model router cache invalidated")
