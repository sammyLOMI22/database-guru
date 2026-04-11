"""Provider registry — central lookup for all configured LLM providers."""
import logging
from typing import Optional

from src.llm.providers.base import (
    BaseLLMProvider,
    DataLocality,
    ProviderHealth,
    is_locality_allowed,
)

logger = logging.getLogger(__name__)


class ProviderNotFoundError(Exception):
    """Raised when a requested provider is not registered."""


class DataSecurityError(Exception):
    """Raised when a provider's data locality exceeds the allowed security level."""


class ProviderRegistry:
    """Central registry for LLM providers.

    Manages provider instances, enforces data security level,
    and provides lookup/health-check utilities.
    """

    def __init__(self, security_level: str = "local_only"):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._security_level = security_level

    @property
    def security_level(self) -> str:
        return self._security_level

    @security_level.setter
    def security_level(self, value: str) -> None:
        if value not in ("local_only", "cloud_private", "unrestricted"):
            raise ValueError(f"Invalid security level: {value!r}")
        self._security_level = value
        logger.info(f"Provider registry security level set to: {value}")

    def register(self, provider: BaseLLMProvider) -> None:
        """Register a provider instance."""
        name = provider.provider_name
        self._providers[name] = provider
        logger.info(
            f"Registered LLM provider: {name} "
            f"(data_locality={provider.data_locality.value})"
        )

    def unregister(self, name: str) -> None:
        """Remove a provider from the registry."""
        self._providers.pop(name, None)

    def get(self, name: str, enforce_security: bool = True) -> BaseLLMProvider:
        """Get a provider by name.

        Args:
            name: Provider name (e.g. "ollama", "openai").
            enforce_security: If True (default), raises DataSecurityError
                when the provider's data locality exceeds the security level.

        Raises:
            ProviderNotFoundError: If the provider is not registered.
            DataSecurityError: If the provider is blocked by security level.
        """
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotFoundError(
                f"LLM provider {name!r} is not registered. "
                f"Available: {list(self._providers.keys())}"
            )

        if enforce_security and not is_locality_allowed(
            provider.data_locality, self._security_level
        ):
            raise DataSecurityError(
                f"Provider {name!r} (data_locality={provider.data_locality.value}) "
                f"is blocked by DATA_SECURITY_LEVEL={self._security_level!r}. "
                f"Change the security level to allow this provider."
            )

        return provider

    def list_available(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def list_allowed(self) -> list[str]:
        """List provider names that are allowed by the current security level."""
        return [
            name
            for name, p in self._providers.items()
            if is_locality_allowed(p.data_locality, self._security_level)
        ]

    def get_all(self) -> dict[str, BaseLLMProvider]:
        """Get all registered providers (no security filtering)."""
        return dict(self._providers)

    async def health_check_all(self) -> list[ProviderHealth]:
        """Run health checks on all registered providers."""
        results = []
        for provider in self._providers.values():
            try:
                result = await provider.health_check()
                results.append(result)
            except Exception as e:
                results.append(
                    ProviderHealth(
                        healthy=False,
                        provider=provider.provider_name,
                        data_locality=provider.data_locality.value,
                        message=str(e),
                    )
                )
        return results


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_provider_registry(security_level: Optional[str] = None) -> ProviderRegistry:
    """Get or create the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry(security_level=security_level or "local_only")
    elif security_level is not None:
        _registry.security_level = security_level
    return _registry


def initialize_registry_from_settings() -> ProviderRegistry:
    """Create and populate the provider registry from application settings.

    Registers Ollama (always) and any enabled providers (OpenAI, LM Studio, vLLM).
    Called at application startup.
    """
    from src.config.settings import Settings
    from src.llm.providers.ollama import OllamaProvider

    settings = Settings()
    registry = get_provider_registry(security_level=settings.DATA_SECURITY_LEVEL)

    # Ollama is always registered (default local provider)
    registry.register(OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        default_model=settings.OLLAMA_MODEL,
    ))

    # OpenAI (cloud_public)
    if settings.OPENAI_ENABLED and settings.OPENAI_API_KEY:
        from src.llm.providers.openai_provider import OpenAIProvider
        registry.register(OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            default_model=settings.OPENAI_DEFAULT_MODEL,
            org_id=settings.OPENAI_ORG_ID,
            base_url=settings.OPENAI_BASE_URL,
        ))
        logger.info("OpenAI provider registered")

    # LM Studio (local)
    if settings.LM_STUDIO_ENABLED:
        from src.llm.providers.lm_studio import LMStudioProvider
        registry.register(LMStudioProvider(
            base_url=settings.LM_STUDIO_BASE_URL,
            default_model=settings.LM_STUDIO_DEFAULT_MODEL,
        ))
        logger.info("LM Studio provider registered")

    # vLLM (local)
    if settings.VLLM_ENABLED:
        from src.llm.providers.vllm import VLLMProvider
        registry.register(VLLMProvider(
            base_url=settings.VLLM_BASE_URL,
            default_model=settings.VLLM_DEFAULT_MODEL,
            api_key=settings.VLLM_API_KEY,
        ))
        logger.info("vLLM provider registered")

    # Azure OpenAI (cloud_private)
    if (settings.AZURE_OPENAI_ENABLED
            and settings.AZURE_OPENAI_ENDPOINT
            and settings.AZURE_OPENAI_API_KEY
            and settings.AZURE_OPENAI_DEPLOYMENT_NAME):
        from src.llm.providers.azure_openai import AzureOpenAIProvider
        registry.register(AzureOpenAIProvider(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        ))
        logger.info("Azure OpenAI provider registered")

    # Anthropic (cloud_public)
    if settings.ANTHROPIC_ENABLED and settings.ANTHROPIC_API_KEY:
        from src.llm.providers.anthropic import AnthropicProvider
        registry.register(AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            default_model=settings.ANTHROPIC_DEFAULT_MODEL,
        ))
        logger.info("Anthropic provider registered")

    logger.info(
        f"Provider registry initialized: {registry.list_available()} "
        f"(security_level={registry.security_level})"
    )
    return registry
