"""Tests for TrackedLLMClient and OllamaClient backward compatibility."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.providers.base import (
    BaseLLMProvider,
    DataLocality,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)
from src.llm.tracked_client import TrackedLLMClient


# ── Fixtures ──


class StubProvider(BaseLLMProvider):
    """Minimal provider for testing TrackedLLMClient."""

    provider_name = "stub"
    data_locality = DataLocality.LOCAL

    def __init__(self):
        self.default_model = "stub-model"
        self.base_url = "http://stub:1234"
        self.client = True  # satisfies `if not ollama.client:` checks

    async def generate(self, prompt, model=None, system=None, temperature=0.1,
                       max_tokens=None, **kwargs):
        return LLMResponse(
            text=f"gen:{prompt[:10]}",
            raw_response={
                "response": f"gen:{prompt[:10]}",
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
            model=model or self.default_model,
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=10,
            output_tokens=5,
        )

    async def chat(self, messages, model=None, temperature=0.1,
                   max_tokens=None, **kwargs):
        text = f"chat:{len(messages)}msgs"
        return LLMResponse(
            text=text,
            raw_response={
                "message": {"content": text},
                "prompt_eval_count": 15,
                "eval_count": 8,
            },
            model=model or self.default_model,
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=15,
            output_tokens=8,
        )

    async def health_check(self):
        return ProviderHealth(healthy=True, provider=self.provider_name,
                              data_locality=self.data_locality.value)

    async def list_models(self):
        return [ModelInfo(name="stub-model", provider=self.provider_name)]


@pytest.fixture
def stub_provider():
    return StubProvider()


@pytest.fixture
def tracked(stub_provider):
    return TrackedLLMClient(stub_provider)


# ── Generate Tests ──


class TestTrackedGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_string_by_default(self, tracked):
        result = await tracked.generate("hello world")
        assert isinstance(result, str)
        assert result == "gen:hello worl"

    @pytest.mark.asyncio
    async def test_generate_returns_dict_with_full_response(self, tracked):
        result = await tracked.generate("hello", return_full_response=True)
        assert isinstance(result, dict)
        assert "response" in result
        assert result["prompt_eval_count"] == 10
        assert result["eval_count"] == 5

    @pytest.mark.asyncio
    async def test_generate_passes_model_and_temperature(self, stub_provider):
        tracked = TrackedLLMClient(stub_provider)
        result = await tracked.generate(
            "test", model="custom-model", temperature=0.5,
            return_full_response=True,
        )
        assert result["response"].startswith("gen:")

    @pytest.mark.asyncio
    async def test_generate_with_tracking(self, tracked):
        """When db is provided, tracking context manager should be invoked."""
        mock_db = AsyncMock()
        mock_tracking = MagicMock()
        mock_tracking.set_response = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_tracking)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.llm.tracked_client.llm_usage_tracker.track_call",
            return_value=mock_ctx,
        ) as mock_track:
            result = await tracked.generate(
                "hello", db=mock_db, agent_type="test_agent",
            )
            assert isinstance(result, str)
            mock_track.assert_called_once()
            call_kwargs = mock_track.call_args.kwargs
            assert call_kwargs["provider"] == "stub"
            assert call_kwargs["agent_type"] == "test_agent"
            mock_tracking.set_response.assert_called_once()


# ── Chat Tests ──


class TestTrackedChat:
    @pytest.mark.asyncio
    async def test_chat_returns_string_by_default(self, tracked):
        messages = [{"role": "user", "content": "hi"}]
        result = await tracked.chat(messages)
        assert isinstance(result, str)
        assert "1msgs" in result

    @pytest.mark.asyncio
    async def test_chat_returns_dict_with_full_response(self, tracked):
        messages = [{"role": "user", "content": "hi"}]
        result = await tracked.chat(messages, return_full_response=True)
        assert isinstance(result, dict)
        assert "message" in result
        assert result["prompt_eval_count"] == 15

    @pytest.mark.asyncio
    async def test_chat_with_tracking(self, tracked):
        mock_db = AsyncMock()
        mock_tracking = MagicMock()
        mock_tracking.set_response = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_tracking)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.llm.tracked_client.llm_usage_tracker.track_call",
            return_value=mock_ctx,
        ):
            messages = [{"role": "user", "content": "test"}]
            result = await tracked.chat(
                messages, db=mock_db, agent_type="chat_test",
            )
            assert isinstance(result, str)


# ── Backward Compatibility Tests ──


class TestBackwardCompat:
    def test_provider_name_property(self, tracked):
        assert tracked.provider_name == "stub"

    def test_base_url_property(self, tracked):
        assert tracked.base_url == "http://stub:1234"

    def test_model_property(self, tracked):
        assert tracked.model == "stub-model"

    def test_client_property(self, tracked):
        assert tracked.client is True

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self, tracked):
        result = await tracked.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_list_models_returns_strings(self, tracked):
        models = await tracked.list_models()
        assert models == ["stub-model"]

    @pytest.mark.asyncio
    async def test_pull_model_delegates(self, tracked, stub_provider):
        stub_provider.pull_model = AsyncMock(return_value=True)
        result = await tracked.pull_model("some-model")
        assert result is True
        stub_provider.pull_model.assert_called_once_with("some-model")

    @pytest.mark.asyncio
    async def test_pull_model_unsupported_returns_false(self, tracked):
        # StubProvider has no pull_model method
        if hasattr(tracked._provider, "pull_model"):
            delattr(tracked._provider, "pull_model")
        result = await tracked.pull_model("x")
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_delegates(self, tracked, stub_provider):
        stub_provider.connect = AsyncMock()
        await tracked.connect()
        stub_provider.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_delegates(self, tracked, stub_provider):
        stub_provider.disconnect = AsyncMock()
        await tracked.disconnect()
        stub_provider.disconnect.assert_called_once()


# ── OllamaClient Shim Tests ──


class TestOllamaClientShim:
    def test_ollama_client_is_tracked_client(self):
        from src.llm.ollama_client import OllamaClient
        assert issubclass(OllamaClient, TrackedLLMClient)

    def test_get_ollama_client_returns_ollama_client(self):
        with patch("src.llm.ollama_client._ollama_client", None):
            from src.llm.ollama_client import get_ollama_client, OllamaClient
            client = get_ollama_client()
            assert isinstance(client, OllamaClient)
            assert isinstance(client, TrackedLLMClient)
            assert client.provider_name == "ollama"

    def test_ollama_client_has_settings(self):
        with patch("src.llm.ollama_client._ollama_client", None):
            from src.llm.ollama_client import get_ollama_client
            client = get_ollama_client()
            assert client.settings is not None

    def test_ollama_client_base_url(self):
        with patch("src.llm.ollama_client._ollama_client", None):
            from src.llm.ollama_client import get_ollama_client
            client = get_ollama_client()
            assert "localhost" in client.base_url or "127.0.0.1" in client.base_url

    def test_imports_from_llm_package(self):
        """Verify the public API exports work."""
        from src.llm import (
            OllamaClient,
            get_ollama_client,
            SQLGenerator,
            TrackedLLMClient,
            BaseLLMProvider,
            DataLocality,
            LLMResponse,
            ProviderRegistry,
            get_provider_registry,
        )
        # All importable without error
        assert OllamaClient is not None
        assert BaseLLMProvider is not None
