"""Provider registry — central lookup for all configured LLM providers."""
import logging
import threading
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
_registry_lock = threading.Lock()


def get_provider_registry(security_level: Optional[str] = None) -> ProviderRegistry:
    """Get or create the global provider registry (thread-safe)."""
    global _registry
    with _registry_lock:
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

    # Google Vertex AI (cloud_private)
    if settings.GOOGLE_VERTEX_ENABLED and settings.GOOGLE_VERTEX_PROJECT_ID:
        from src.llm.providers.google_vertex import GoogleVertexProvider
        registry.register(GoogleVertexProvider(
            project_id=settings.GOOGLE_VERTEX_PROJECT_ID,
            region=settings.GOOGLE_VERTEX_REGION,
            default_model=settings.GOOGLE_VERTEX_DEFAULT_MODEL,
            api_key=settings.GOOGLE_VERTEX_API_KEY,
        ))
        logger.info("Google Vertex AI provider registered")

    # AWS Bedrock (cloud_private)
    if settings.AWS_BEDROCK_ENABLED:
        from src.llm.providers.aws_bedrock import AWSBedrockProvider
        registry.register(AWSBedrockProvider(
            region=settings.AWS_BEDROCK_REGION,
            default_model=settings.AWS_BEDROCK_DEFAULT_MODEL,
            access_key_id=settings.AWS_BEDROCK_ACCESS_KEY_ID,
            secret_access_key=settings.AWS_BEDROCK_SECRET_ACCESS_KEY,
            session_token=settings.AWS_BEDROCK_SESSION_TOKEN,
            profile_name=settings.AWS_BEDROCK_PROFILE_NAME,
        ))
        logger.info("AWS Bedrock provider registered")

    logger.info(
        f"Provider registry initialized: {registry.list_available()} "
        f"(security_level={registry.security_level})"
    )
    return registry


# -- Provider name → class + constructor kwargs mapping --

_PROVIDER_FACTORIES: dict[str, tuple[str, str, dict]] = {
    # name → (module_path, class_name, default_kwargs)
    "ollama": ("src.llm.providers.ollama", "OllamaProvider", {}),
    "openai": ("src.llm.providers.openai_provider", "OpenAIProvider", {}),
    "anthropic": ("src.llm.providers.anthropic", "AnthropicProvider", {}),
    "azure_openai": ("src.llm.providers.azure_openai", "AzureOpenAIProvider", {}),
    "google_vertex": ("src.llm.providers.google_vertex", "GoogleVertexProvider", {}),
    "aws_bedrock": ("src.llm.providers.aws_bedrock", "AWSBedrockProvider", {}),
    "lm_studio": ("src.llm.providers.lm_studio", "LMStudioProvider", {}),
    "vllm": ("src.llm.providers.vllm", "VLLMProvider", {}),
}

# Maps DB config fields → provider constructor kwargs per provider
_PROVIDER_KWARG_MAP: dict[str, dict[str, str]] = {
    "ollama": {"endpoint": "base_url", "default_model": "default_model"},
    "openai": {"api_key": "api_key", "endpoint": "base_url", "default_model": "default_model"},
    "anthropic": {"api_key": "api_key", "default_model": "default_model"},
    "azure_openai": {"api_key": "api_key", "endpoint": "endpoint", "default_model": "default_model"},
    "google_vertex": {"api_key": "api_key", "default_model": "default_model"},
    "aws_bedrock": {"default_model": "default_model"},
    "lm_studio": {"endpoint": "base_url", "default_model": "default_model"},
    "vllm": {"api_key": "api_key", "endpoint": "base_url", "default_model": "default_model"},
}


async def rebuild_registry_from_db(db, settings=None) -> ProviderRegistry:
    """Rebuild the provider registry by merging env-based defaults with DB configs.

    Called after provider config mutations so that saved configs take effect
    at runtime without restarting the application.

    Steps:
    1. Re-initialise from env settings (baseline).
    2. Layer on any enabled DB-stored provider configs, overriding or adding
       providers as needed.
    """
    import importlib
    from sqlalchemy import select
    from src.database.models import LLMProviderConfig

    if settings is None:
        from src.config.settings import Settings
        settings = Settings()

    # Step 1: rebuild baseline from env
    registry = initialize_registry_from_settings()

    # Step 2: overlay DB-stored configs
    try:
        from src.services.provider_config_service import ProviderConfigService
        config_service = ProviderConfigService(settings)

        result = await db.execute(
            select(LLMProviderConfig).where(LLMProviderConfig.enabled == True)  # noqa: E712
        )
        db_configs = result.scalars().all()

        for cfg in db_configs:
            name = cfg.provider_name
            factory = _PROVIDER_FACTORIES.get(name)
            if factory is None:
                logger.warning(f"No provider factory for {name!r}, skipping DB config")
                continue

            # If the provider is already registered from env with the same name,
            # and the DB config has overrides, re-register with DB values.
            kwarg_map = _PROVIDER_KWARG_MAP.get(name, {})
            kwargs: dict[str, str] = {}

            # Decrypt API key if stored
            if cfg.api_key_encrypted:
                decrypted = config_service.decrypt_key(cfg.api_key_encrypted)
                if decrypted and "api_key" in kwarg_map:
                    kwargs[kwarg_map["api_key"]] = decrypted

            if cfg.endpoint and "endpoint" in kwarg_map:
                kwargs[kwarg_map["endpoint"]] = cfg.endpoint

            if cfg.default_model and "default_model" in kwarg_map:
                kwargs[kwarg_map["default_model"]] = cfg.default_model

            # Extra config passthrough (e.g. deployment_name for Azure, project_id for Vertex)
            if cfg.extra_config and isinstance(cfg.extra_config, dict):
                kwargs.update(cfg.extra_config)

            # Only re-register if we have meaningful overrides or provider is not yet registered
            if kwargs or name not in registry.list_available():
                try:
                    module = importlib.import_module(factory[0])
                    cls = getattr(module, factory[1])
                    provider = cls(**kwargs)
                    registry.register(provider)
                    logger.info(f"Provider {name!r} registered/updated from DB config")
                except Exception as e:
                    logger.warning(f"Failed to register provider {name!r} from DB: {e}")

        # Also handle disabled providers — unregister if DB explicitly disables
        result_disabled = await db.execute(
            select(LLMProviderConfig).where(LLMProviderConfig.enabled == False)  # noqa: E712
        )
        for cfg in result_disabled.scalars().all():
            if cfg.provider_name in registry.list_available() and cfg.provider_name != "ollama":
                registry.unregister(cfg.provider_name)
                logger.info(f"Provider {cfg.provider_name!r} unregistered (disabled in DB)")

    except Exception as e:
        logger.error(f"Failed to rebuild registry from DB: {e}")

    # Invalidate model router so it picks up new providers
    from src.llm.model_router import invalidate_model_router
    invalidate_model_router()

    logger.info(
        f"Provider registry rebuilt: {registry.list_available()} "
        f"(security_level={registry.security_level})"
    )
    return registry
