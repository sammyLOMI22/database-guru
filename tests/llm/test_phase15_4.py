"""Tests for Phase 15.4: ModelRouter enhancements, ProviderConfigService, API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime

from cryptography.fernet import Fernet
from src.llm.model_router import ModelRouter, TaskType, TaskConfig
from src.services.provider_config_service import ProviderConfigService, generate_encryption_key
from src.llm.providers.base import DataLocality, LLMResponse


# ══════════════════════════════════════════════════════════════
# ModelRouter — Provider Routing
# ══════════════════════════════════════════════════════════════


class TestModelRouterProviderRouting:
    """Test provider routing additions to ModelRouter."""

    def _make_router(self, model_settings=None):
        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        return ModelRouter(settings=settings, model_settings=model_settings)

    def test_default_provider_is_ollama(self):
        router = self._make_router()
        assert router._default_provider == "ollama"

    def test_default_provider_from_settings(self):
        router = self._make_router({"default_provider": "openai"})
        assert router._default_provider == "openai"

    def test_get_provider_for_task_default(self):
        router = self._make_router()
        assert router.get_provider_for_task(TaskType.SQL_GENERATION) == "ollama"

    def test_get_provider_for_task_per_task(self):
        router = self._make_router({"provider_sql_generation": "openai"})
        assert router.get_provider_for_task(TaskType.SQL_GENERATION) == "openai"
        # Other tasks still use default
        assert router.get_provider_for_task(TaskType.NARRATIVES) == "ollama"

    def test_get_fallback_chain_empty_default(self):
        router = self._make_router()
        assert router.get_fallback_chain(TaskType.SQL_GENERATION) == []

    def test_get_fallback_chain_configured(self):
        chain = [{"provider": "ollama", "model": "llama3.2:latest"}]
        router = self._make_router({"fallback_sql_generation": chain})
        assert router.get_fallback_chain(TaskType.SQL_GENERATION) == chain

    def test_get_fallback_chain_non_list_returns_empty(self):
        router = self._make_router({"fallback_sql_generation": "invalid"})
        assert router.get_fallback_chain(TaskType.SQL_GENERATION) == []

    def test_task_config_includes_provider(self):
        router = self._make_router({"provider_narratives": "anthropic"})
        config = router.get_config_for_task(TaskType.NARRATIVES)
        assert config.provider == "anthropic"
        assert isinstance(config.fallback_chain, list)

    def test_task_config_includes_fallback_chain(self):
        chain = [{"provider": "ollama", "model": "llama3.2:latest"}]
        router = self._make_router({
            "provider_sql_generation": "openai",
            "fallback_sql_generation": chain,
        })
        config = router.get_config_for_task(TaskType.SQL_GENERATION)
        assert config.provider == "openai"
        assert config.fallback_chain == chain

    def test_to_dict_includes_provider_info(self):
        router = self._make_router({"provider_sql_generation": "openai"})
        d = router.to_dict()
        assert d["default_provider"] == "ollama"
        assert d["tasks"]["sql_generation"]["provider"] == "openai"
        assert "fallback_chain" in d["tasks"]["sql_generation"]


class TestModelRouterExecuteWithFallback:
    """Test execute_with_fallback()."""

    @pytest.mark.asyncio
    async def test_execute_primary_success(self):
        fake_provider = AsyncMock()
        fake_provider.provider_name = "ollama"
        fake_provider.default_model = "llama3.2:latest"
        fake_provider.data_locality = DataLocality.LOCAL
        fake_response = LLMResponse(
            text="SELECT 1",
            raw_response={},
            model="llama3.2:latest",
            provider="ollama",
            data_locality="local",
        )
        fake_provider.generate.return_value = fake_response

        mock_registry = MagicMock()
        mock_registry.get.return_value = fake_provider

        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        router = ModelRouter(settings=settings)

        with patch("src.llm.providers.registry.get_provider_registry", return_value=mock_registry):
            result = await router.execute_with_fallback(
                TaskType.SQL_GENERATION, prompt="Generate SQL"
            )

        assert result.text == "SELECT 1"
        fake_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_falls_back_on_failure(self):
        failing_provider = AsyncMock()
        failing_provider.provider_name = "openai"
        failing_provider.default_model = "gpt-4o"
        failing_provider.data_locality = DataLocality.CLOUD_PUBLIC
        failing_provider.generate.side_effect = Exception("API down")

        fallback_provider = AsyncMock()
        fallback_provider.provider_name = "ollama"
        fallback_provider.default_model = "llama3.2:latest"
        fallback_provider.data_locality = DataLocality.LOCAL
        fallback_response = LLMResponse(
            text="fallback result",
            raw_response={},
            model="llama3.2:latest",
            provider="ollama",
            data_locality="local",
        )
        fallback_provider.generate.return_value = fallback_response

        def mock_get(name, enforce_security=True):
            if name == "openai":
                return failing_provider
            return fallback_provider

        mock_registry = MagicMock()
        mock_registry.get.side_effect = mock_get

        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        router = ModelRouter(
            settings=settings,
            model_settings={
                "provider_sql_generation": "openai",
                "fallback_sql_generation": [{"provider": "ollama", "model": "llama3.2:latest"}],
            },
        )

        with patch("src.llm.providers.registry.get_provider_registry", return_value=mock_registry):
            result = await router.execute_with_fallback(
                TaskType.SQL_GENERATION, prompt="Generate SQL"
            )

        assert result.text == "fallback result"
        assert failing_provider.generate.call_count == 1
        assert fallback_provider.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_skips_security_blocked_provider(self):
        from src.llm.providers.registry import DataSecurityError

        fallback_provider = AsyncMock()
        fallback_provider.provider_name = "ollama"
        fallback_provider.default_model = "llama3.2:latest"
        fallback_provider.data_locality = DataLocality.LOCAL
        fallback_provider.generate.return_value = LLMResponse(
            text="local result", raw_response={}, model="llama3.2:latest",
            provider="ollama", data_locality="local",
        )

        def mock_get(name, enforce_security=True):
            if name == "openai" and enforce_security:
                raise DataSecurityError("blocked")
            return fallback_provider

        mock_registry = MagicMock()
        mock_registry.get.side_effect = mock_get

        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        router = ModelRouter(
            settings=settings,
            model_settings={
                "provider_sql_generation": "openai",
                "fallback_sql_generation": [{"provider": "ollama"}],
            },
        )

        with patch("src.llm.providers.registry.get_provider_registry", return_value=mock_registry):
            result = await router.execute_with_fallback(
                TaskType.SQL_GENERATION, prompt="test"
            )

        assert result.text == "local result"

    @pytest.mark.asyncio
    async def test_execute_all_fail_raises(self):
        failing_provider = AsyncMock()
        failing_provider.provider_name = "ollama"
        failing_provider.default_model = "llama3.2:latest"
        failing_provider.data_locality = DataLocality.LOCAL
        failing_provider.generate.side_effect = Exception("model not found")

        mock_registry = MagicMock()
        mock_registry.get.return_value = failing_provider

        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        router = ModelRouter(settings=settings)

        with patch("src.llm.providers.registry.get_provider_registry", return_value=mock_registry):
            with pytest.raises(Exception, match="model not found"):
                await router.execute_with_fallback(
                    TaskType.SQL_GENERATION, prompt="test"
                )

    @pytest.mark.asyncio
    async def test_execute_chat_mode(self):
        fake_provider = AsyncMock()
        fake_provider.provider_name = "ollama"
        fake_provider.default_model = "llama3.2:latest"
        fake_provider.data_locality = DataLocality.LOCAL
        fake_provider.chat.return_value = LLMResponse(
            text="chat result", raw_response={}, model="llama3.2:latest",
            provider="ollama", data_locality="local",
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = fake_provider

        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        router = ModelRouter(settings=settings)

        with patch("src.llm.providers.registry.get_provider_registry", return_value=mock_registry):
            result = await router.execute_with_fallback(
                TaskType.NARRATIVES,
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result.text == "chat result"
        fake_provider.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_prompt_or_messages_raises(self):
        fake_provider = AsyncMock()
        fake_provider.provider_name = "ollama"
        fake_provider.default_model = "llama3.2:latest"
        fake_provider.data_locality = DataLocality.LOCAL

        mock_registry = MagicMock()
        mock_registry.get.return_value = fake_provider

        settings = MagicMock()
        settings.OLLAMA_MODEL = "llama3.2:latest"
        router = ModelRouter(settings=settings)

        with patch("src.llm.providers.registry.get_provider_registry", return_value=mock_registry):
            with pytest.raises(ValueError, match="Either prompt or messages"):
                await router.execute_with_fallback(TaskType.SQL_GENERATION)


# ══════════════════════════════════════════════════════════════
# ProviderConfigService
# ══════════════════════════════════════════════════════════════


class TestProviderConfigServiceEncryption:
    """Test encrypt/decrypt/mask functionality."""

    def test_encrypt_decrypt_with_key(self):
        key = generate_encryption_key()
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = key
        svc = ProviderConfigService(settings)

        encrypted = svc.encrypt_key("sk-test-key-123")
        assert encrypted != "sk-test-key-123"

        decrypted = svc.decrypt_key(encrypted)
        assert decrypted == "sk-test-key-123"

    def test_encrypt_no_key_raises_error(self):
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = None
        svc = ProviderConfigService(settings)

        with pytest.raises(ValueError, match="LLM_ENCRYPTION_KEY is not configured"):
            svc.encrypt_key("sk-test")

    def test_decrypt_no_key_returns_plaintext(self):
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = None
        svc = ProviderConfigService(settings)

        result = svc.decrypt_key("sk-test")
        assert result == "sk-test"

    def test_decrypt_wrong_key_returns_none(self):
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        settings1 = MagicMock()
        settings1.LLM_ENCRYPTION_KEY = key1
        svc1 = ProviderConfigService(settings1)

        settings2 = MagicMock()
        settings2.LLM_ENCRYPTION_KEY = key2
        svc2 = ProviderConfigService(settings2)

        encrypted = svc1.encrypt_key("secret")
        result = svc2.decrypt_key(encrypted)
        assert result is None

    def test_decrypt_empty_returns_none(self):
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = None
        svc = ProviderConfigService(settings)
        assert svc.decrypt_key("") is None
        assert svc.decrypt_key(None) is None

    def test_mask_key_short(self):
        assert ProviderConfigService.mask_key("abc") == "***"

    def test_mask_key_long(self):
        result = ProviderConfigService.mask_key("sk-abcdefghij1234")
        assert result == "***...1234"

    def test_mask_key_none(self):
        assert ProviderConfigService.mask_key(None) is None
        assert ProviderConfigService.mask_key("") is None

    def test_generate_encryption_key(self):
        key = generate_encryption_key()
        assert isinstance(key, str)
        assert len(key) > 20

    def test_invalid_encryption_key_logs_error(self):
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = "not-a-valid-fernet-key"
        svc = ProviderConfigService(settings)
        assert svc._fernet is None


class TestProviderConfigServiceCRUD:
    """Test CRUD operations with mocked DB session."""

    _TEST_FERNET_KEY = Fernet.generate_key().decode()

    def _make_service(self, with_encryption=False):
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = self._TEST_FERNET_KEY if with_encryption else None
        return ProviderConfigService(settings)

    @pytest.mark.asyncio
    async def test_list_configs(self):
        svc = self._make_service()

        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.provider_name = "openai"
        mock_config.enabled = True
        mock_config.data_locality = "cloud_public"
        mock_config.api_key_encrypted = "sk-test123456789"
        mock_config.endpoint = "https://api.openai.com"
        mock_config.default_model = "gpt-4o"
        mock_config.extra_config = None
        mock_config.created_at = datetime(2026, 1, 1)
        mock_config.updated_at = datetime(2026, 1, 1)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_config]
        db.execute.return_value = result_mock

        configs = await svc.list_configs(db)
        assert len(configs) == 1
        assert configs[0]["provider_name"] == "openai"
        assert configs[0]["has_api_key"] is True
        assert configs[0]["api_key_masked"] == "***...6789"

    @pytest.mark.asyncio
    async def test_get_config_not_found(self):
        svc = self._make_service()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await svc.get_config(db, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_config_creates_new(self):
        svc = self._make_service(with_encryption=True)
        db = AsyncMock()

        # First query returns None (not found)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        config = await svc.upsert_config(
            db, provider_name="anthropic", enabled=True,
            data_locality="cloud_public", api_key="sk-ant-123",
        )
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self):
        svc = self._make_service()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await svc.delete_config(db, "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_config_found(self):
        svc = self._make_service()
        db = AsyncMock()
        mock_config = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_config
        db.execute.return_value = result_mock

        result = await svc.delete_config(db, "openai")
        assert result is True
        db.delete.assert_called_once_with(mock_config)


class TestProviderConfigServiceRouting:
    """Test task routing CRUD."""

    def _make_service(self):
        settings = MagicMock()
        settings.LLM_ENCRYPTION_KEY = None
        return ProviderConfigService(settings)

    @pytest.mark.asyncio
    async def test_list_routing(self):
        svc = self._make_service()
        mock_route = MagicMock()
        mock_route.id = 1
        mock_route.task_type = "sql_generation"
        mock_route.primary_provider = "openai"
        mock_route.primary_model = "gpt-4o"
        mock_route.fallback_chain = [{"provider": "ollama"}]
        mock_route.created_at = datetime(2026, 1, 1)
        mock_route.updated_at = datetime(2026, 1, 1)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_route]
        db.execute.return_value = result_mock

        routes = await svc.list_routing(db)
        assert len(routes) == 1
        assert routes[0]["task_type"] == "sql_generation"
        assert routes[0]["primary_provider"] == "openai"
        assert routes[0]["fallback_chain"] == [{"provider": "ollama"}]

    @pytest.mark.asyncio
    async def test_delete_routing_not_found(self):
        svc = self._make_service()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await svc.delete_routing(db, "nonexistent_task")
        assert result is False


# ══════════════════════════════════════════════════════════════
# TaskConfig dataclass
# ══════════════════════════════════════════════════════════════


class TestTaskConfig:
    def test_repr_with_provider(self):
        tc = TaskConfig(
            model="gpt-4o", timeout=30,
            task_type=TaskType.SQL_GENERATION, provider="openai",
        )
        r = repr(tc)
        assert "provider=openai" in r
        assert "model=gpt-4o" in r

    def test_repr_without_provider(self):
        tc = TaskConfig(
            model="llama3.2:latest", timeout=30,
            task_type=TaskType.SQL_GENERATION,
        )
        r = repr(tc)
        assert "provider=" not in r

    def test_default_fallback_chain_is_empty(self):
        tc = TaskConfig(model="m", timeout=10, task_type=TaskType.NARRATIVES)
        assert tc.fallback_chain == []
