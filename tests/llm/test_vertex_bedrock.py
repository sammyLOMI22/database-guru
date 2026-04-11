"""Tests for Phase 15.5: Google Vertex AI + AWS Bedrock providers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.providers.base import DataLocality, LLMResponse, ModelInfo, ProviderHealth
from src.llm.providers.google_vertex import GoogleVertexProvider, VERTEX_MODELS
from src.llm.providers.aws_bedrock import AWSBedrockProvider, BEDROCK_MODELS


# ══════════════════════════════════════════════════════════════
# Google Vertex AI
# ══════════════════════════════════════════════════════════════


class TestGoogleVertexProperties:
    def test_provider_name(self):
        p = GoogleVertexProvider(project_id="my-project")
        assert p.provider_name == "google_vertex"

    def test_data_locality_cloud_private(self):
        p = GoogleVertexProvider(project_id="my-project")
        assert p.data_locality == DataLocality.CLOUD_PRIVATE

    def test_default_model(self):
        p = GoogleVertexProvider(project_id="p", default_model="gemini-2.5-pro")
        assert p.default_model == "gemini-2.5-pro"

    def test_base_url(self):
        p = GoogleVertexProvider(project_id="p", region="europe-west4")
        assert "europe-west4" in p._base_url

    def test_model_url(self):
        p = GoogleVertexProvider(project_id="my-project", region="us-central1")
        url = p._model_url("gemini-2.5-flash")
        assert "/projects/my-project/" in url
        assert "/locations/us-central1/" in url
        assert "/models/gemini-2.5-flash:generateContent" in url


class TestGoogleVertexMessageConversion:
    def test_messages_to_contents_basic(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Help me"},
        ]
        contents, system = GoogleVertexProvider._messages_to_contents(messages)
        assert system is None
        assert len(contents) == 3
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"  # assistant -> model
        assert contents[0]["parts"][0]["text"] == "Hello"

    def test_messages_to_contents_with_system(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        contents, system = GoogleVertexProvider._messages_to_contents(messages)
        assert system == "You are helpful"
        assert len(contents) == 1


class TestGoogleVertexChat:
    @pytest.mark.asyncio
    async def test_chat_success(self):
        p = GoogleVertexProvider(project_id="proj")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "SELECT 1"}]
                }
            }],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
            },
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        p.client = mock_client

        result = await p.chat(
            messages=[{"role": "user", "content": "Generate SQL"}]
        )
        assert result.text == "SELECT 1"
        assert result.provider == "google_vertex"
        assert result.data_locality == "cloud_private"
        assert result.input_tokens == 10
        assert result.output_tokens == 5


class TestGoogleVertexGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        p = GoogleVertexProvider(project_id="proj")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "result"}]}}],
            "usageMetadata": {},
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        p.client = mock_client

        result = await p.generate(prompt="test", system="Be helpful")
        assert result.text == "result"
        # Verify system instruction was included in the payload
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "systemInstruction" in payload


class TestGoogleVertexHealth:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        p = GoogleVertexProvider(project_id="proj")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        p.client = mock_client

        health = await p.health_check()
        assert health.healthy is True
        assert health.provider == "google_vertex"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        p = GoogleVertexProvider(project_id="proj")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        p.client = mock_client

        health = await p.health_check()
        assert health.healthy is False
        assert "Connection refused" in health.message


class TestGoogleVertexModels:
    @pytest.mark.asyncio
    async def test_list_models_returns_catalog(self):
        p = GoogleVertexProvider(project_id="proj")
        models = await p.list_models()
        assert len(models) == len(VERTEX_MODELS)
        assert all(isinstance(m, ModelInfo) for m in models)
        assert models[0].provider == "google_vertex"


class TestGoogleVertexResponseParsing:
    def test_extract_text_empty_candidates(self):
        assert GoogleVertexProvider._extract_text({}) == ""
        assert GoogleVertexProvider._extract_text({"candidates": []}) == ""

    def test_extract_text_multiple_parts(self):
        raw = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello "}, {"text": "World"}]
                }
            }]
        }
        assert GoogleVertexProvider._extract_text(raw) == "Hello World"

    def test_extract_tokens(self):
        raw = {"usageMetadata": {"promptTokenCount": 15, "candidatesTokenCount": 20}}
        inp, out = GoogleVertexProvider._extract_tokens(raw)
        assert inp == 15
        assert out == 20

    def test_extract_tokens_missing(self):
        inp, out = GoogleVertexProvider._extract_tokens({})
        assert inp is None
        assert out is None


# ══════════════════════════════════════════════════════════════
# AWS Bedrock
# ══════════════════════════════════════════════════════════════


class TestAWSBedrockProperties:
    def test_provider_name(self):
        p = AWSBedrockProvider()
        assert p.provider_name == "aws_bedrock"

    def test_data_locality_cloud_private(self):
        p = AWSBedrockProvider()
        assert p.data_locality == DataLocality.CLOUD_PRIVATE

    def test_default_model(self):
        p = AWSBedrockProvider(default_model="amazon.nova-pro-v1:0")
        assert p.default_model == "amazon.nova-pro-v1:0"

    def test_region(self):
        p = AWSBedrockProvider(region="eu-west-1")
        assert p.region == "eu-west-1"


class TestAWSBedrockMessageConversion:
    def test_messages_to_converse_basic(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        converse_msgs, system = AWSBedrockProvider._messages_to_converse(messages)
        assert system is None
        assert len(converse_msgs) == 2
        assert converse_msgs[0]["role"] == "user"
        assert converse_msgs[0]["content"] == [{"text": "Hello"}]

    def test_messages_to_converse_with_system(self):
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]
        converse_msgs, system = AWSBedrockProvider._messages_to_converse(messages)
        assert system == [{"text": "Be helpful"}]
        assert len(converse_msgs) == 1


class TestAWSBedrockChat:
    @pytest.mark.asyncio
    async def test_chat_success(self):
        p = AWSBedrockProvider()
        mock_response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "SELECT 1"}],
                }
            },
            "usage": {"inputTokens": 10, "outputTokens": 3},
        }

        with patch.object(p, "_converse_raw", new_callable=AsyncMock, return_value=mock_response):
            result = await p.chat(
                messages=[{"role": "user", "content": "Generate SQL"}]
            )

        assert result.text == "SELECT 1"
        assert result.provider == "aws_bedrock"
        assert result.data_locality == "cloud_private"
        assert result.input_tokens == 10
        assert result.output_tokens == 3


class TestAWSBedrockGenerate:
    @pytest.mark.asyncio
    async def test_generate_with_system(self):
        p = AWSBedrockProvider()
        mock_response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "result"}],
                }
            },
            "usage": {},
        }

        with patch.object(p, "_converse_raw", new_callable=AsyncMock, return_value=mock_response) as mock_converse:
            result = await p.generate(prompt="test", system="Be helpful")

        assert result.text == "result"
        call_kwargs = mock_converse.call_args
        assert call_kwargs.kwargs["system"] == [{"text": "Be helpful"}]


class TestAWSBedrockHealth:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        p = AWSBedrockProvider()
        mock_response = {
            "output": {"message": {"content": [{"text": "hi"}]}},
            "usage": {},
        }
        with patch.object(p, "_get_boto3_client"), \
             patch.object(p, "_converse_raw", new_callable=AsyncMock, return_value=mock_response):
            health = await p.health_check()
        assert health.healthy is True
        assert health.provider == "aws_bedrock"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        p = AWSBedrockProvider()
        with patch.object(p, "_get_boto3_client", side_effect=Exception("No credentials")):
            health = await p.health_check()
        assert health.healthy is False
        assert "No credentials" in health.message


class TestAWSBedrockModels:
    @pytest.mark.asyncio
    async def test_list_models_fallback_to_catalog(self):
        p = AWSBedrockProvider()
        # Simulate boto3 client failing — should fall back to hardcoded catalog
        with patch.dict("sys.modules", {"boto3": MagicMock(client=MagicMock(side_effect=Exception("no creds")))}):
            models = await p.list_models()
        assert len(models) == len(BEDROCK_MODELS)
        assert all(isinstance(m, ModelInfo) for m in models)


class TestAWSBedrockResponseParsing:
    def test_extract_text(self):
        raw = {
            "output": {
                "message": {
                    "content": [{"text": "Hello "}, {"text": "World"}]
                }
            }
        }
        assert AWSBedrockProvider._extract_text(raw) == "Hello World"

    def test_extract_text_empty(self):
        assert AWSBedrockProvider._extract_text({}) == ""
        assert AWSBedrockProvider._extract_text({"output": {}}) == ""

    def test_extract_tokens(self):
        raw = {"usage": {"inputTokens": 15, "outputTokens": 20}}
        inp, out = AWSBedrockProvider._extract_tokens(raw)
        assert inp == 15
        assert out == 20


# ══════════════════════════════════════════════════════════════
# Security + Registry Integration
# ══════════════════════════════════════════════════════════════


class TestVertexBedrockSecurity:
    def test_vertex_is_cloud_private(self):
        from src.llm.providers.base import is_locality_allowed
        p = GoogleVertexProvider(project_id="p")
        assert is_locality_allowed(p.data_locality, "cloud_private") is True
        assert is_locality_allowed(p.data_locality, "local_only") is False
        assert is_locality_allowed(p.data_locality, "unrestricted") is True

    def test_bedrock_is_cloud_private(self):
        from src.llm.providers.base import is_locality_allowed
        p = AWSBedrockProvider()
        assert is_locality_allowed(p.data_locality, "cloud_private") is True
        assert is_locality_allowed(p.data_locality, "local_only") is False
        assert is_locality_allowed(p.data_locality, "unrestricted") is True


class TestVertexBedrockRegistry:
    def test_registry_registers_vertex(self):
        from src.llm.providers.registry import ProviderRegistry
        registry = ProviderRegistry(security_level="cloud_private")
        p = GoogleVertexProvider(project_id="proj")
        registry.register(p)
        assert "google_vertex" in registry.list_available()
        assert "google_vertex" in registry.list_allowed()

    def test_registry_registers_bedrock(self):
        from src.llm.providers.registry import ProviderRegistry
        registry = ProviderRegistry(security_level="cloud_private")
        p = AWSBedrockProvider()
        registry.register(p)
        assert "aws_bedrock" in registry.list_available()
        assert "aws_bedrock" in registry.list_allowed()

    def test_registry_blocks_vertex_in_local_only(self):
        from src.llm.providers.registry import ProviderRegistry, DataSecurityError
        registry = ProviderRegistry(security_level="local_only")
        p = GoogleVertexProvider(project_id="proj")
        registry.register(p)
        assert "google_vertex" in registry.list_available()
        assert "google_vertex" not in registry.list_allowed()
        with pytest.raises(DataSecurityError):
            registry.get("google_vertex")

    def test_initialize_registry_with_vertex_and_bedrock(self):
        from src.llm.providers.registry import initialize_registry_from_settings

        mock_settings = MagicMock()
        mock_settings.DATA_SECURITY_LEVEL = "cloud_private"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_MODEL = "llama3.2:latest"
        mock_settings.OPENAI_ENABLED = False
        mock_settings.LM_STUDIO_ENABLED = False
        mock_settings.VLLM_ENABLED = False
        mock_settings.AZURE_OPENAI_ENABLED = False
        mock_settings.ANTHROPIC_ENABLED = False
        mock_settings.GOOGLE_VERTEX_ENABLED = True
        mock_settings.GOOGLE_VERTEX_PROJECT_ID = "my-project"
        mock_settings.GOOGLE_VERTEX_REGION = "us-central1"
        mock_settings.GOOGLE_VERTEX_DEFAULT_MODEL = "gemini-2.5-flash"
        mock_settings.GOOGLE_VERTEX_API_KEY = None
        mock_settings.AWS_BEDROCK_ENABLED = True
        mock_settings.AWS_BEDROCK_REGION = "us-east-1"
        mock_settings.AWS_BEDROCK_DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        mock_settings.AWS_BEDROCK_ACCESS_KEY_ID = None
        mock_settings.AWS_BEDROCK_SECRET_ACCESS_KEY = None
        mock_settings.AWS_BEDROCK_SESSION_TOKEN = None
        mock_settings.AWS_BEDROCK_PROFILE_NAME = None

        with patch("src.config.settings.Settings", return_value=mock_settings):
            registry = initialize_registry_from_settings()

        assert "ollama" in registry.list_available()
        assert "google_vertex" in registry.list_available()
        assert "aws_bedrock" in registry.list_available()
