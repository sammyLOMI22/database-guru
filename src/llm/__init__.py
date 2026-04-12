"""LLM package for Database Guru"""
import logging
from typing import Optional

from src.llm.ollama_client import OllamaClient, get_ollama_client
from src.llm.sql_generator import SQLGenerator
from src.llm.tracked_client import TrackedLLMClient
from src.llm.providers.base import BaseLLMProvider, DataLocality, LLMResponse
from src.llm.providers.registry import ProviderRegistry, get_provider_registry

_logger = logging.getLogger(__name__)


def get_llm_client(
    provider_name: Optional[str] = None,
    task_type: Optional[str] = None,
) -> TrackedLLMClient:
    """Get an LLM client from the provider registry.

    Args:
        provider_name: Specific provider to use (e.g. "openai", "anthropic").
            If None, uses the default provider (first registered, typically Ollama).
        task_type: Optional task type string (e.g. "sql_generation"). If provided
            and provider_name is None, resolves the provider from the cached
            ModelRouter's per-task routing configuration.

    Returns:
        TrackedLLMClient wrapping the requested provider.

    Falls back to ``get_ollama_client()`` if the registry is empty or the
    requested provider is not found.
    """
    # Resolve provider from task routing if no explicit provider given
    if provider_name is None and task_type is not None:
        try:
            from src.llm.model_router import get_model_router_sync, TaskType
            router = get_model_router_sync()
            task_enum = TaskType(task_type)
            provider_name = router.get_provider_for_task(task_enum)
        except (ValueError, Exception) as e:
            _logger.debug(f"Task-based provider lookup failed for {task_type!r}: {e}")

    try:
        registry = get_provider_registry()
        if provider_name:
            provider = registry.get(provider_name)
            return TrackedLLMClient(provider)

        # Default: first allowed provider
        allowed = registry.list_allowed()
        if allowed:
            provider = registry.get(allowed[0])
            return TrackedLLMClient(provider)
    except Exception as e:
        _logger.debug(f"Registry lookup failed, falling back to Ollama: {e}")

    # Fallback: legacy singleton
    return get_ollama_client()


__all__ = [
    "OllamaClient",
    "get_ollama_client",
    "get_llm_client",
    "SQLGenerator",
    "TrackedLLMClient",
    "BaseLLMProvider",
    "DataLocality",
    "LLMResponse",
    "ProviderRegistry",
    "get_provider_registry",
]
