"""Tests for OpenAI-compatible providers (Phase 15.2)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.llm.providers.base import DataLocality, LLMResponse, ModelInfo, ProviderHealth
from src.llm.providers.openai_compat import OpenAICompatibleProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.providers.lm_studio import LMStudioProvider
from src.llm.providers.vllm import VLLMProvider
from src.llm.providers.registry import (
    DataSecurityError,
    ProviderRegistry,
    initialize_registry_from_settings,
)


# ── Mock HTTP Responses ──


def _mock_chat_response(content="Hello!", model="gpt-4o", prompt_tokens=10, completion_tokens=5):
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _mock_models_response():
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model"},
            {"id": "gpt-3.5-turbo", "object": "model"},
        ],
    }


def _mock_embeddings_response():
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0}
        ],
    }


def _make_httpx_response(data: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("POST", "http://test"),
    )


# ── Subclass Properties Tests ──


class TestProviderProperties:
    def test_openai_is_cloud_public(self):
        p = OpenAIProvider(api_key="sk-test")
        assert p.provider_name == "openai"
        assert p.data_locality == DataLocality.CLOUD_PUBLIC
        assert p.default_model == "gpt-4o"
        assert p.base_url == "https://api.openai.com"

    def test_openai_custom_config(self):
        p = OpenAIProvider(
            api_key="sk-test",
            default_model="gpt-3.5-turbo",
            org_id="org-123",
            base_url="https://custom.openai.com",
        )
        assert p.default_model == "gpt-3.5-turbo"
        assert p.org_id == "org-123"
        assert p.base_url == "https://custom.openai.com"

    def test_lm_studio_is_local(self):
        p = LMStudioProvider()
        assert p.provider_name == "lm_studio"
        assert p.data_locality == DataLocality.LOCAL
        assert p.base_url == "http://localhost:1234"
        assert p.api_key is None

    def test_vllm_is_local(self):
        p = VLLMProvider()
        assert p.provider_name == "vllm"
        assert p.data_locality == DataLocality.LOCAL
        assert p.base_url == "http://localhost:8000"

    def test_vllm_with_api_key(self):
        p = VLLMProvider(api_key="token-123")
        assert p.api_key == "token-123"


# ── Headers Tests ──


class TestHeaders:
    def test_openai_headers_include_auth(self):
        p = OpenAIProvider(api_key="sk-test123", org_id="org-456")
        headers = p._build_headers()
        assert headers["Authorization"] == "Bearer sk-test123"
        assert headers["OpenAI-Organization"] == "org-456"

    def test_lm_studio_headers_no_auth(self):
        p = LMStudioProvider()
        headers = p._build_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

    def test_vllm_headers_optional_auth(self):
        p = VLLMProvider(api_key="tok")
        headers = p._build_headers()
        assert headers["Authorization"] == "Bearer tok"

        p2 = VLLMProvider()
        headers2 = p2._build_headers()
        assert "Authorization" not in headers2


# ── Chat Completions Tests ──


class TestChatCompletions:
    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response(_mock_chat_response("SQL result"))

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        result = await provider.chat(
            messages=[{"role": "user", "content": "hello"}],
            model="gpt-4o",
        )

        assert isinstance(result, LLMResponse)
        assert result.text == "SQL result"
        assert result.provider == "openai"
        assert result.data_locality == "cloud_public"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_chat_passes_temperature_and_max_tokens(self):
        provider = LMStudioProvider()
        mock_response = _make_httpx_response(_mock_chat_response("ok"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        await provider.chat(
            messages=[{"role": "user", "content": "test"}],
            temperature=0.7,
            max_tokens=100,
        )

        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_chat_empty_choices(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response({"choices": [], "usage": {}})
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        result = await provider.chat([{"role": "user", "content": "hi"}])
        assert result.text == ""


# ── Generate Tests (wraps chat) ──


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_wraps_as_chat(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response(_mock_chat_response("generated"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        result = await provider.generate("What is SQL?")
        assert result.text == "generated"

        # Verify it was sent as a chat message
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response(_mock_chat_response("ok"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        await provider.generate("query", system="You are a SQL expert")

        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a SQL expert"
        assert messages[1]["role"] == "user"


# ── Health Check Tests ──


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response(_mock_models_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        result = await provider.health_check()
        assert isinstance(result, ProviderHealth)
        assert result.healthy is True
        assert result.provider == "openai"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        provider = LMStudioProvider()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        provider.client = mock_client

        result = await provider.health_check()
        assert result.healthy is False
        assert "refused" in result.message


# ── List Models Tests ──


class TestListModels:
    @pytest.mark.asyncio
    async def test_list_models(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response(_mock_models_response())
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        models = await provider.list_models()
        assert len(models) == 2
        assert all(isinstance(m, ModelInfo) for m in models)
        assert models[0].name == "gpt-4o"
        assert models[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_list_models_error_returns_empty(self):
        provider = VLLMProvider()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("fail"))
        provider.client = mock_client

        models = await provider.list_models()
        assert models == []


# ── Embeddings Tests ──


class TestEmbeddings:
    @pytest.mark.asyncio
    async def test_embeddings(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_response = _make_httpx_response(_mock_embeddings_response())
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider.client = mock_client

        result = await provider.embeddings("test text")
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embeddings_error_returns_none(self):
        provider = OpenAIProvider(api_key="sk-test")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("fail"))
        provider.client = mock_client

        result = await provider.embeddings("test")
        assert result is None


# ── Security Level Integration Tests ──


class TestSecurityIntegration:
    def test_local_only_blocks_openai(self):
        registry = ProviderRegistry(security_level="local_only")
        registry.register(OpenAIProvider(api_key="sk-test"))
        with pytest.raises(DataSecurityError):
            registry.get("openai")

    def test_local_only_allows_lm_studio(self):
        registry = ProviderRegistry(security_level="local_only")
        lm = LMStudioProvider()
        registry.register(lm)
        assert registry.get("lm_studio") is lm

    def test_local_only_allows_vllm(self):
        registry = ProviderRegistry(security_level="local_only")
        v = VLLMProvider()
        registry.register(v)
        assert registry.get("vllm") is v

    def test_unrestricted_allows_openai(self):
        registry = ProviderRegistry(security_level="unrestricted")
        openai = OpenAIProvider(api_key="sk-test")
        registry.register(openai)
        assert registry.get("openai") is openai

    def test_list_allowed_with_mixed_providers(self):
        registry = ProviderRegistry(security_level="local_only")
        registry.register(LMStudioProvider())
        registry.register(VLLMProvider())
        registry.register(OpenAIProvider(api_key="sk-test"))
        allowed = registry.list_allowed()
        assert sorted(allowed) == ["lm_studio", "vllm"]
        assert "openai" not in allowed


# ── Registry Auto-Registration Tests ──


class TestInitializeRegistry:
    @patch("src.llm.providers.registry._registry", None)
    def test_default_registers_ollama_only(self):
        with patch("src.config.settings.Settings") as MockSettings:
            s = MockSettings.return_value
            s.DATA_SECURITY_LEVEL = "local_only"
            s.OLLAMA_BASE_URL = "http://localhost:11434"
            s.OLLAMA_MODEL = "llama3.2:latest"
            s.OPENAI_ENABLED = False
            s.OPENAI_API_KEY = None
            s.LM_STUDIO_ENABLED = False
            s.VLLM_ENABLED = False
            s.AZURE_OPENAI_ENABLED = False
            s.AZURE_OPENAI_ENDPOINT = None
            s.AZURE_OPENAI_API_KEY = None
            s.AZURE_OPENAI_DEPLOYMENT_NAME = None
            s.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            s.ANTHROPIC_ENABLED = False
            s.ANTHROPIC_API_KEY = None

            registry = initialize_registry_from_settings()
            assert "ollama" in registry.list_available()
            assert len(registry.list_available()) == 1

    @patch("src.llm.providers.registry._registry", None)
    def test_registers_enabled_providers(self):
        with patch("src.config.settings.Settings") as MockSettings:
            s = MockSettings.return_value
            s.DATA_SECURITY_LEVEL = "unrestricted"
            s.OLLAMA_BASE_URL = "http://localhost:11434"
            s.OLLAMA_MODEL = "llama3.2:latest"
            s.OPENAI_ENABLED = True
            s.OPENAI_API_KEY = "sk-test"
            s.OPENAI_DEFAULT_MODEL = "gpt-4o"
            s.OPENAI_ORG_ID = None
            s.OPENAI_BASE_URL = "https://api.openai.com"
            s.LM_STUDIO_ENABLED = True
            s.LM_STUDIO_BASE_URL = "http://localhost:1234"
            s.LM_STUDIO_DEFAULT_MODEL = "default"
            s.VLLM_ENABLED = True
            s.VLLM_BASE_URL = "http://localhost:8000"
            s.VLLM_DEFAULT_MODEL = "default"
            s.VLLM_API_KEY = None
            s.AZURE_OPENAI_ENABLED = False
            s.AZURE_OPENAI_ENDPOINT = None
            s.AZURE_OPENAI_API_KEY = None
            s.AZURE_OPENAI_DEPLOYMENT_NAME = None
            s.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            s.ANTHROPIC_ENABLED = False
            s.ANTHROPIC_API_KEY = None

            registry = initialize_registry_from_settings()
            available = sorted(registry.list_available())
            assert available == ["lm_studio", "ollama", "openai", "vllm"]

    @patch("src.llm.providers.registry._registry", None)
    def test_openai_not_registered_without_api_key(self):
        with patch("src.config.settings.Settings") as MockSettings:
            s = MockSettings.return_value
            s.DATA_SECURITY_LEVEL = "unrestricted"
            s.OLLAMA_BASE_URL = "http://localhost:11434"
            s.OLLAMA_MODEL = "llama3.2:latest"
            s.OPENAI_ENABLED = True
            s.OPENAI_API_KEY = None  # No API key
            s.LM_STUDIO_ENABLED = False
            s.VLLM_ENABLED = False
            s.AZURE_OPENAI_ENABLED = False
            s.AZURE_OPENAI_ENDPOINT = None
            s.AZURE_OPENAI_API_KEY = None
            s.AZURE_OPENAI_DEPLOYMENT_NAME = None
            s.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            s.ANTHROPIC_ENABLED = False
            s.ANTHROPIC_API_KEY = None

            registry = initialize_registry_from_settings()
            assert "openai" not in registry.list_available()

    @patch("src.llm.providers.registry._registry", None)
    def test_security_level_from_settings(self):
        with patch("src.config.settings.Settings") as MockSettings:
            s = MockSettings.return_value
            s.DATA_SECURITY_LEVEL = "cloud_private"
            s.OLLAMA_BASE_URL = "http://localhost:11434"
            s.OLLAMA_MODEL = "llama3.2:latest"
            s.OPENAI_ENABLED = False
            s.OPENAI_API_KEY = None
            s.LM_STUDIO_ENABLED = False
            s.VLLM_ENABLED = False
            s.AZURE_OPENAI_ENABLED = False
            s.AZURE_OPENAI_ENDPOINT = None
            s.AZURE_OPENAI_API_KEY = None
            s.AZURE_OPENAI_DEPLOYMENT_NAME = None
            s.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            s.ANTHROPIC_ENABLED = False
            s.ANTHROPIC_API_KEY = None

            registry = initialize_registry_from_settings()
            assert registry.security_level == "cloud_private"


# ── Connect / Disconnect Tests ──


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_connect_creates_client(self):
        provider = LMStudioProvider()
        assert provider.client is None
        await provider.connect()
        assert provider.client is not None
        await provider.disconnect()
        assert provider.client is None

    @pytest.mark.asyncio
    async def test_ensure_client_lazy_init(self):
        provider = VLLMProvider()
        assert provider.client is None
        await provider._ensure_client()
        assert provider.client is not None
        await provider.disconnect()
