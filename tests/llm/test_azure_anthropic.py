"""Tests for Azure OpenAI and Anthropic providers (Phase 15.3)."""
import pytest
from unittest.mock import AsyncMock, patch

import httpx

from src.llm.providers.base import DataLocality, LLMResponse, ModelInfo, ProviderHealth
from src.llm.providers.azure_openai import AzureOpenAIProvider
from src.llm.providers.anthropic import AnthropicProvider, ANTHROPIC_MODELS
from src.llm.providers.registry import DataSecurityError, ProviderRegistry


# ── Mock Response Helpers ──


def _make_httpx_response(data: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("POST", "http://test"),
    )


def _azure_chat_response(content="Hello!", prompt_tokens=10, completion_tokens=5):
    return {
        "id": "chatcmpl-abc",
        "model": "gpt-4o",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content},
             "finish_reason": "stop"}
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _anthropic_messages_response(
    content="Hello!", input_tokens=10, output_tokens=5, model="claude-sonnet-4-20250514"
):
    return {
        "id": "msg_abc",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": content}],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "stop_reason": "end_turn",
    }


# ══════════════════════════════════════════════════════════
#  Azure OpenAI Tests
# ══════════════════════════════════════════════════════════


class TestAzureOpenAIProperties:
    def test_provider_name_and_locality(self):
        p = AzureOpenAIProvider(
            endpoint="https://myresource.openai.azure.com",
            api_key="key-123",
            deployment_name="gpt-4o-deploy",
        )
        assert p.provider_name == "azure_openai"
        assert p.data_locality == DataLocality.CLOUD_PRIVATE
        assert p.default_model == "gpt-4o-deploy"

    def test_custom_default_model(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="deploy1",
            default_model="custom-model",
        )
        assert p.default_model == "custom-model"

    def test_headers(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="my-azure-key",
            deployment_name="d",
        )
        headers = p._build_headers()
        assert headers["api-key"] == "my-azure-key"
        assert "Authorization" not in headers

    def test_deployment_url(self):
        p = AzureOpenAIProvider(
            endpoint="https://myresource.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
            api_version="2024-02-15-preview",
        )
        url = p._deployment_url()
        assert "/openai/deployments/gpt4/chat/completions" in url
        assert "api-version=2024-02-15-preview" in url

    def test_deployment_url_custom_deployment(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="default-deploy",
        )
        url = p._deployment_url("other-deploy")
        assert "/deployments/other-deploy/" in url


class TestAzureOpenAIChat:
    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
        )
        mock_resp = _make_httpx_response(_azure_chat_response("SQL result"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.chat([{"role": "user", "content": "hi"}])
        assert isinstance(result, LLMResponse)
        assert result.text == "SQL result"
        assert result.provider == "azure_openai"
        assert result.data_locality == "cloud_private"
        assert result.input_tokens == 10
        assert result.output_tokens == 5

    @pytest.mark.asyncio
    async def test_chat_uses_deployment_url(self):
        p = AzureOpenAIProvider(
            endpoint="https://myres.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
        )
        mock_resp = _make_httpx_response(_azure_chat_response())
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        await p.chat([{"role": "user", "content": "test"}])
        call_url = mock_client.post.call_args[0][0]
        assert "/deployments/gpt4/chat/completions" in call_url


class TestAzureOpenAIGenerate:
    @pytest.mark.asyncio
    async def test_generate_wraps_as_chat(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
        )
        mock_resp = _make_httpx_response(_azure_chat_response("generated"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.generate("What is SQL?", system="You are an expert")
        assert result.text == "generated"

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1]["json"]
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"


class TestAzureOpenAIHealth:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
        )
        mock_resp = _make_httpx_response(_azure_chat_response())
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.health_check()
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        p.client = mock_client

        result = await p.health_check()
        assert result.healthy is False


class TestAzureOpenAIModels:
    @pytest.mark.asyncio
    async def test_list_models_from_deployments(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="gpt4",
        )
        mock_resp = _make_httpx_response({
            "data": [
                {"id": "gpt4-deploy"},
                {"id": "gpt35-deploy"},
            ]
        })
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        models = await p.list_models()
        assert len(models) == 2
        assert models[0].name == "gpt4-deploy"

    @pytest.mark.asyncio
    async def test_list_models_fallback_on_error(self):
        p = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="my-deploy",
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("fail"))
        p.client = mock_client

        models = await p.list_models()
        assert len(models) == 1
        assert models[0].name == "my-deploy"


# ══════════════════════════════════════════════════════════
#  Anthropic Tests
# ══════════════════════════════════════════════════════════


class TestAnthropicProperties:
    def test_provider_name_and_locality(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        assert p.provider_name == "anthropic"
        assert p.data_locality == DataLocality.CLOUD_PUBLIC
        assert "claude" in p.default_model

    def test_headers(self):
        p = AnthropicProvider(api_key="sk-ant-test123")
        headers = p._build_headers()
        assert headers["x-api-key"] == "sk-ant-test123"
        assert headers["anthropic-version"] == "2023-06-01"
        assert "Authorization" not in headers


class TestAnthropicChat:
    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        mock_resp = _make_httpx_response(
            _anthropic_messages_response("Claude says hi")
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.chat([{"role": "user", "content": "hello"}])
        assert isinstance(result, LLMResponse)
        assert result.text == "Claude says hi"
        assert result.provider == "anthropic"
        assert result.data_locality == "cloud_public"
        assert result.input_tokens == 10
        assert result.output_tokens == 5

    @pytest.mark.asyncio
    async def test_chat_extracts_system_from_messages(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        mock_resp = _make_httpx_response(_anthropic_messages_response("ok"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        await p.chat([
            {"role": "system", "content": "You are a SQL expert"},
            {"role": "user", "content": "Write a query"},
        ])

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1]["json"]
        # System should be top-level, not in messages
        assert payload["system"] == "You are a SQL expert"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chat_multi_content_blocks(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        raw = {
            "id": "msg_abc",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-4-20250514",
            "content": [
                {"type": "text", "text": "Part 1. "},
                {"type": "text", "text": "Part 2."},
            ],
            "usage": {"input_tokens": 5, "output_tokens": 10},
        }
        mock_resp = _make_httpx_response(raw)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.chat([{"role": "user", "content": "hi"}])
        assert result.text == "Part 1. Part 2."

    @pytest.mark.asyncio
    async def test_chat_empty_content(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        raw = {
            "content": [],
            "usage": {"input_tokens": 5, "output_tokens": 0},
        }
        mock_resp = _make_httpx_response(raw)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.chat([{"role": "user", "content": "hi"}])
        assert result.text == ""


class TestAnthropicGenerate:
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        mock_resp = _make_httpx_response(_anthropic_messages_response("ok"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.generate("query", system="Be helpful")
        assert result.text == "ok"

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1]["json"]
        assert payload["system"] == "Be helpful"
        assert payload["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_default_max_tokens(self):
        p = AnthropicProvider(api_key="sk-ant-test", max_tokens_default=2048)
        mock_resp = _make_httpx_response(_anthropic_messages_response("ok"))
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        await p.generate("test")
        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1]["json"]
        assert payload["max_tokens"] == 2048


class TestAnthropicHealth:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        mock_resp = _make_httpx_response(_anthropic_messages_response())
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p.client = mock_client

        result = await p.health_check()
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        p.client = mock_client

        result = await p.health_check()
        assert result.healthy is False


class TestAnthropicModels:
    @pytest.mark.asyncio
    async def test_list_models_returns_catalog(self):
        p = AnthropicProvider(api_key="sk-ant-test")
        models = await p.list_models()
        assert len(models) == len(ANTHROPIC_MODELS)
        assert all(isinstance(m, ModelInfo) for m in models)
        assert all(m.provider == "anthropic" for m in models)


# ══════════════════════════════════════════════════════════
#  Security Level Integration Tests
# ══════════════════════════════════════════════════════════


class TestSecurityLevels:
    def test_azure_allowed_at_cloud_private(self):
        registry = ProviderRegistry(security_level="cloud_private")
        azure = AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="d",
        )
        registry.register(azure)
        assert registry.get("azure_openai") is azure

    def test_azure_blocked_at_local_only(self):
        registry = ProviderRegistry(security_level="local_only")
        registry.register(AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="d",
        ))
        with pytest.raises(DataSecurityError):
            registry.get("azure_openai")

    def test_anthropic_blocked_at_cloud_private(self):
        registry = ProviderRegistry(security_level="cloud_private")
        registry.register(AnthropicProvider(api_key="sk-ant-test"))
        with pytest.raises(DataSecurityError):
            registry.get("anthropic")

    def test_anthropic_allowed_at_unrestricted(self):
        registry = ProviderRegistry(security_level="unrestricted")
        anthropic = AnthropicProvider(api_key="sk-ant-test")
        registry.register(anthropic)
        assert registry.get("anthropic") is anthropic

    def test_mixed_providers_list_allowed(self):
        registry = ProviderRegistry(security_level="cloud_private")
        registry.register(AzureOpenAIProvider(
            endpoint="https://x.openai.azure.com",
            api_key="k",
            deployment_name="d",
        ))
        registry.register(AnthropicProvider(api_key="sk-ant-test"))
        allowed = registry.list_allowed()
        assert "azure_openai" in allowed
        assert "anthropic" not in allowed


# ══════════════════════════════════════════════════════════
#  Registry Auto-Registration Tests
# ══════════════════════════════════════════════════════════


class TestRegistryAutoRegistration:
    @patch("src.llm.providers.registry._registry", None)
    def test_registers_azure_and_anthropic(self):
        from src.llm.providers.registry import initialize_registry_from_settings
        with patch("src.config.settings.Settings") as MockSettings:
            s = MockSettings.return_value
            s.DATA_SECURITY_LEVEL = "unrestricted"
            s.OLLAMA_BASE_URL = "http://localhost:11434"
            s.OLLAMA_MODEL = "llama3.2:latest"
            s.OPENAI_ENABLED = False
            s.OPENAI_API_KEY = None
            s.LM_STUDIO_ENABLED = False
            s.VLLM_ENABLED = False
            s.AZURE_OPENAI_ENABLED = True
            s.AZURE_OPENAI_ENDPOINT = "https://myres.openai.azure.com"
            s.AZURE_OPENAI_API_KEY = "azure-key"
            s.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt4-deploy"
            s.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            s.ANTHROPIC_ENABLED = True
            s.ANTHROPIC_API_KEY = "sk-ant-key"
            s.ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-20250514"
            s.GOOGLE_VERTEX_ENABLED = False
            s.GOOGLE_VERTEX_PROJECT_ID = None
            s.AWS_BEDROCK_ENABLED = False

            registry = initialize_registry_from_settings()
            available = sorted(registry.list_available())
            assert "azure_openai" in available
            assert "anthropic" in available
            assert "ollama" in available

    @patch("src.llm.providers.registry._registry", None)
    def test_azure_not_registered_without_deployment(self):
        from src.llm.providers.registry import initialize_registry_from_settings
        with patch("src.config.settings.Settings") as MockSettings:
            s = MockSettings.return_value
            s.DATA_SECURITY_LEVEL = "unrestricted"
            s.OLLAMA_BASE_URL = "http://localhost:11434"
            s.OLLAMA_MODEL = "llama3.2:latest"
            s.OPENAI_ENABLED = False
            s.OPENAI_API_KEY = None
            s.LM_STUDIO_ENABLED = False
            s.VLLM_ENABLED = False
            s.AZURE_OPENAI_ENABLED = True
            s.AZURE_OPENAI_ENDPOINT = "https://myres.openai.azure.com"
            s.AZURE_OPENAI_API_KEY = "azure-key"
            s.AZURE_OPENAI_DEPLOYMENT_NAME = None  # Missing
            s.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            s.ANTHROPIC_ENABLED = False
            s.ANTHROPIC_API_KEY = None
            s.GOOGLE_VERTEX_ENABLED = False
            s.GOOGLE_VERTEX_PROJECT_ID = None
            s.AWS_BEDROCK_ENABLED = False

            registry = initialize_registry_from_settings()
            assert "azure_openai" not in registry.list_available()
