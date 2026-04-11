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
