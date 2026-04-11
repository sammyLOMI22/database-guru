"""Provider config service — load/save provider configurations with encrypted API keys."""
import logging
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.database.models import LLMProviderConfig, LLMTaskRouting

logger = logging.getLogger(__name__)


class ProviderConfigService:
    """Manages LLM provider configurations in the database.

    API keys are encrypted at rest using Fernet symmetric encryption.
    The encryption key comes from LLM_ENCRYPTION_KEY in settings.
    If no key is configured, a warning is logged and keys are stored
    as plaintext (development only).
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._fernet: Optional[Fernet] = None
        key = self._settings.LLM_ENCRYPTION_KEY
        if key:
            try:
                self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception as e:
                logger.error(f"Invalid LLM_ENCRYPTION_KEY: {e}")
        else:
            logger.warning(
                "LLM_ENCRYPTION_KEY not set — API keys will not be encrypted at rest. "
                "Set a Fernet key for production use."
            )

    def encrypt_key(self, plaintext: str) -> str:
        """Encrypt an API key for storage."""
        if self._fernet:
            return self._fernet.encrypt(plaintext.encode()).decode()
        return plaintext

    def decrypt_key(self, ciphertext: str) -> Optional[str]:
        """Decrypt a stored API key."""
        if not ciphertext:
            return None
        if self._fernet:
            try:
                return self._fernet.decrypt(ciphertext.encode()).decode()
            except InvalidToken:
                logger.error("Failed to decrypt API key — wrong encryption key?")
                return None
        return ciphertext

    @staticmethod
    def mask_key(key: Optional[str]) -> Optional[str]:
        """Mask an API key for display (never expose full key in responses)."""
        if not key:
            return None
        if len(key) <= 8:
            return "***"
        return f"***...{key[-4:]}"

    # -- CRUD for Provider Configs --

    async def list_configs(self, db: AsyncSession) -> list[dict[str, Any]]:
        """List all provider configurations (keys masked)."""
        result = await db.execute(select(LLMProviderConfig))
        configs = result.scalars().all()
        return [self._config_to_dict(c) for c in configs]

    async def get_config(self, db: AsyncSession, provider_name: str) -> Optional[dict[str, Any]]:
        """Get a single provider config (key masked)."""
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider_name == provider_name
            )
        )
        config = result.scalar_one_or_none()
        if config is None:
            return None
        return self._config_to_dict(config)

    async def upsert_config(
        self,
        db: AsyncSession,
        provider_name: str,
        enabled: bool = False,
        data_locality: str = "local",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        default_model: Optional[str] = None,
        extra_config: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Create or update a provider configuration."""
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider_name == provider_name
            )
        )
        config = result.scalar_one_or_none()

        if config is None:
            config = LLMProviderConfig(provider_name=provider_name)
            db.add(config)

        config.enabled = enabled
        config.data_locality = data_locality
        config.endpoint = endpoint
        config.default_model = default_model
        config.extra_config = extra_config

        if api_key is not None:
            config.api_key_encrypted = self.encrypt_key(api_key)

        await db.flush()
        return self._config_to_dict(config)

    async def delete_config(self, db: AsyncSession, provider_name: str) -> bool:
        """Delete a provider configuration."""
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider_name == provider_name
            )
        )
        config = result.scalar_one_or_none()
        if config is None:
            return False
        await db.delete(config)
        await db.flush()
        return True

    async def get_decrypted_key(self, db: AsyncSession, provider_name: str) -> Optional[str]:
        """Get a decrypted API key (for internal use only — never expose via API)."""
        result = await db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider_name == provider_name
            )
        )
        config = result.scalar_one_or_none()
        if config is None or not config.api_key_encrypted:
            return None
        return self.decrypt_key(config.api_key_encrypted)

    def _config_to_dict(self, config: LLMProviderConfig) -> dict[str, Any]:
        """Convert a config model to dict with masked key."""
        decrypted = self.decrypt_key(config.api_key_encrypted) if config.api_key_encrypted else None
        return {
            "id": config.id,
            "provider_name": config.provider_name,
            "enabled": config.enabled,
            "data_locality": config.data_locality,
            "api_key_masked": self.mask_key(decrypted),
            "has_api_key": bool(config.api_key_encrypted),
            "endpoint": config.endpoint,
            "default_model": config.default_model,
            "extra_config": config.extra_config,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }

    # -- CRUD for Task Routing --

    async def list_routing(self, db: AsyncSession) -> list[dict[str, Any]]:
        """List all task routing configurations."""
        result = await db.execute(select(LLMTaskRouting))
        routes = result.scalars().all()
        return [self._routing_to_dict(r) for r in routes]

    async def upsert_routing(
        self,
        db: AsyncSession,
        task_type: str,
        primary_provider: str,
        primary_model: Optional[str] = None,
        fallback_chain: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """Create or update a task routing entry."""
        result = await db.execute(
            select(LLMTaskRouting).where(LLMTaskRouting.task_type == task_type)
        )
        route = result.scalar_one_or_none()

        if route is None:
            route = LLMTaskRouting(task_type=task_type)
            db.add(route)

        route.primary_provider = primary_provider
        route.primary_model = primary_model
        route.fallback_chain = fallback_chain

        await db.flush()
        return self._routing_to_dict(route)

    async def delete_routing(self, db: AsyncSession, task_type: str) -> bool:
        """Delete a task routing entry."""
        result = await db.execute(
            select(LLMTaskRouting).where(LLMTaskRouting.task_type == task_type)
        )
        route = result.scalar_one_or_none()
        if route is None:
            return False
        await db.delete(route)
        await db.flush()
        return True

    @staticmethod
    def _routing_to_dict(route: LLMTaskRouting) -> dict[str, Any]:
        return {
            "id": route.id,
            "task_type": route.task_type,
            "primary_provider": route.primary_provider,
            "primary_model": route.primary_model,
            "fallback_chain": route.fallback_chain,
            "created_at": route.created_at.isoformat() if route.created_at else None,
            "updated_at": route.updated_at.isoformat() if route.updated_at else None,
        }


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key. Use this to create LLM_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode()
