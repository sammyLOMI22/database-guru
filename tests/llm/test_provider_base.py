"""Tests for the LLM provider abstraction layer (Phase 15.1)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.providers.base import (
    BaseLLMProvider,
    DataLocality,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
    is_locality_allowed,
)
from src.llm.providers.types import ChatMessage, ProviderConfig
from src.llm.providers.registry import (
    DataSecurityError,
    ProviderNotFoundError,
    ProviderRegistry,
    get_provider_registry,
)


# ── Fixtures ──


class FakeLocalProvider(BaseLLMProvider):
    """Concrete provider for testing (local)."""

    provider_name = "fake_local"
    data_locality = DataLocality.LOCAL

    def __init__(self):
        self.generate_calls = []
        self.chat_calls = []

    async def generate(self, prompt, model=None, system=None, temperature=0.1,
                       max_tokens=None, **kwargs):
        self.generate_calls.append(prompt)
        return LLMResponse(
            text=f"Generated: {prompt[:20]}",
            raw_response={"response": f"Generated: {prompt[:20]}",
                          "prompt_eval_count": 10, "eval_count": 5},
            model=model or "fake-model",
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=10,
            output_tokens=5,
        )

    async def chat(self, messages, model=None, temperature=0.1,
                   max_tokens=None, **kwargs):
        self.chat_calls.append(messages)
        text = f"Chat response to {len(messages)} messages"
        return LLMResponse(
            text=text,
            raw_response={"message": {"content": text},
                          "prompt_eval_count": 15, "eval_count": 8},
            model=model or "fake-model",
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=15,
            output_tokens=8,
        )

    async def health_check(self):
        return ProviderHealth(
            healthy=True,
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            message="OK",
        )

    async def list_models(self):
        return [ModelInfo(name="fake-model", provider=self.provider_name)]


class FakeCloudProvider(BaseLLMProvider):
    """Concrete provider for testing (cloud public)."""

    provider_name = "fake_cloud"
    data_locality = DataLocality.CLOUD_PUBLIC

    async def generate(self, prompt, model=None, system=None, temperature=0.1,
                       max_tokens=None, **kwargs):
        return LLMResponse(
            text="cloud response",
            raw_response={},
            model=model or "cloud-model",
            provider=self.provider_name,
            data_locality=self.data_locality.value,
        )

    async def chat(self, messages, model=None, temperature=0.1,
                   max_tokens=None, **kwargs):
        return LLMResponse(
            text="cloud chat",
            raw_response={},
            model=model or "cloud-model",
            provider=self.provider_name,
            data_locality=self.data_locality.value,
        )

    async def health_check(self):
        return ProviderHealth(
            healthy=True, provider=self.provider_name,
            data_locality=self.data_locality.value,
        )

    async def list_models(self):
        return [ModelInfo(name="cloud-model", provider=self.provider_name)]


class FakeCloudPrivateProvider(BaseLLMProvider):
    """Concrete provider for testing (cloud private)."""

    provider_name = "fake_private"
    data_locality = DataLocality.CLOUD_PRIVATE

    async def generate(self, prompt, **kwargs):
        return LLMResponse(text="private", raw_response={}, model="m",
                           provider=self.provider_name,
                           data_locality=self.data_locality.value)

    async def chat(self, messages, **kwargs):
        return LLMResponse(text="private", raw_response={}, model="m",
                           provider=self.provider_name,
                           data_locality=self.data_locality.value)

    async def health_check(self):
        return ProviderHealth(healthy=True, provider=self.provider_name,
                              data_locality=self.data_locality.value)

    async def list_models(self):
        return []


# ── DataLocality / Security Level Tests ──


class TestDataLocality:
    def test_local_only_allows_local(self):
        assert is_locality_allowed(DataLocality.LOCAL, "local_only") is True

    def test_local_only_blocks_cloud_private(self):
        assert is_locality_allowed(DataLocality.CLOUD_PRIVATE, "local_only") is False

    def test_local_only_blocks_cloud_public(self):
        assert is_locality_allowed(DataLocality.CLOUD_PUBLIC, "local_only") is False

    def test_cloud_private_allows_local(self):
        assert is_locality_allowed(DataLocality.LOCAL, "cloud_private") is True

    def test_cloud_private_allows_private(self):
        assert is_locality_allowed(DataLocality.CLOUD_PRIVATE, "cloud_private") is True

    def test_cloud_private_blocks_public(self):
        assert is_locality_allowed(DataLocality.CLOUD_PUBLIC, "cloud_private") is False

    def test_unrestricted_allows_all(self):
        assert is_locality_allowed(DataLocality.LOCAL, "unrestricted") is True
        assert is_locality_allowed(DataLocality.CLOUD_PRIVATE, "unrestricted") is True
        assert is_locality_allowed(DataLocality.CLOUD_PUBLIC, "unrestricted") is True

    def test_unknown_level_defaults_to_local_only(self):
        assert is_locality_allowed(DataLocality.LOCAL, "bogus") is True
        assert is_locality_allowed(DataLocality.CLOUD_PUBLIC, "bogus") is False


# ── LLMResponse Tests ──


class TestLLMResponse:
    def test_fields(self):
        r = LLMResponse(
            text="hello", raw_response={"key": "val"}, model="m",
            provider="p", data_locality="local",
            input_tokens=10, output_tokens=5,
        )
        assert r.text == "hello"
        assert r.provider == "p"
        assert r.data_locality == "local"
        assert r.input_tokens == 10

    def test_optional_tokens(self):
        r = LLMResponse(text="x", raw_response={}, model="m",
                        provider="p", data_locality="local")
        assert r.input_tokens is None
        assert r.output_tokens is None


# ── ProviderRegistry Tests ──


class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry(security_level="unrestricted")
        provider = FakeLocalProvider()
        registry.register(provider)
        assert registry.get("fake_local") is provider

    def test_get_not_found_raises(self):
        registry = ProviderRegistry()
        with pytest.raises(ProviderNotFoundError):
            registry.get("nonexistent")

    def test_security_blocks_cloud_in_local_only(self):
        registry = ProviderRegistry(security_level="local_only")
        registry.register(FakeCloudProvider())
        with pytest.raises(DataSecurityError):
            registry.get("fake_cloud")

    def test_security_allows_local_in_local_only(self):
        registry = ProviderRegistry(security_level="local_only")
        local = FakeLocalProvider()
        registry.register(local)
        assert registry.get("fake_local") is local

    def test_security_allows_cloud_in_unrestricted(self):
        registry = ProviderRegistry(security_level="unrestricted")
        cloud = FakeCloudProvider()
        registry.register(cloud)
        assert registry.get("fake_cloud") is cloud

    def test_bypass_security_with_flag(self):
        registry = ProviderRegistry(security_level="local_only")
        cloud = FakeCloudProvider()
        registry.register(cloud)
        # enforce_security=False bypasses the check
        assert registry.get("fake_cloud", enforce_security=False) is cloud

    def test_list_available(self):
        registry = ProviderRegistry()
        registry.register(FakeLocalProvider())
        registry.register(FakeCloudProvider())
        assert sorted(registry.list_available()) == ["fake_cloud", "fake_local"]

    def test_list_allowed_filters_by_security(self):
        registry = ProviderRegistry(security_level="local_only")
        registry.register(FakeLocalProvider())
        registry.register(FakeCloudProvider())
        assert registry.list_allowed() == ["fake_local"]

    def test_list_allowed_cloud_private_level(self):
        registry = ProviderRegistry(security_level="cloud_private")
        registry.register(FakeLocalProvider())
        registry.register(FakeCloudPrivateProvider())
        registry.register(FakeCloudProvider())
        assert sorted(registry.list_allowed()) == ["fake_local", "fake_private"]

    def test_unregister(self):
        registry = ProviderRegistry()
        registry.register(FakeLocalProvider())
        registry.unregister("fake_local")
        assert registry.list_available() == []

    def test_set_invalid_security_level_raises(self):
        registry = ProviderRegistry()
        with pytest.raises(ValueError):
            registry.security_level = "invalid_level"

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        registry = ProviderRegistry(security_level="unrestricted")
        registry.register(FakeLocalProvider())
        registry.register(FakeCloudProvider())
        results = await registry.health_check_all()
        assert len(results) == 2
        assert all(r.healthy for r in results)


# ── BaseLLMProvider Contract Tests ──


class TestBaseLLMProviderContract:
    @pytest.mark.asyncio
    async def test_generate_returns_llm_response(self):
        provider = FakeLocalProvider()
        result = await provider.generate("hello")
        assert isinstance(result, LLMResponse)
        assert result.text.startswith("Generated:")
        assert result.provider == "fake_local"
        assert result.data_locality == "local"

    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self):
        provider = FakeLocalProvider()
        messages = [{"role": "user", "content": "hi"}]
        result = await provider.chat(messages)
        assert isinstance(result, LLMResponse)
        assert result.provider == "fake_local"

    @pytest.mark.asyncio
    async def test_health_check_returns_provider_health(self):
        provider = FakeLocalProvider()
        result = await provider.health_check()
        assert isinstance(result, ProviderHealth)
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_list_models_returns_model_info(self):
        provider = FakeLocalProvider()
        models = await provider.list_models()
        assert len(models) == 1
        assert isinstance(models[0], ModelInfo)

    @pytest.mark.asyncio
    async def test_embeddings_default_returns_none(self):
        provider = FakeCloudProvider()
        result = await provider.embeddings("test")
        assert result is None

    def test_repr(self):
        provider = FakeLocalProvider()
        assert "fake_local" in repr(provider)
        assert "local" in repr(provider)


# ── ProviderConfig / ChatMessage Tests ──


class TestTypes:
    def test_provider_config_defaults(self):
        cfg = ProviderConfig(provider_name="test")
        assert cfg.enabled is False
        assert cfg.api_key is None
        assert cfg.extra == {}

    def test_chat_message_typing(self):
        msg: ChatMessage = {"role": "user", "content": "hello"}
        assert msg["role"] == "user"
