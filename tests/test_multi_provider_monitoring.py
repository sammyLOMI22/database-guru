"""Tests for Phase 17: Multi-Provider Monitoring Integration."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Token Extraction Tests
# =============================================================================

class TestTokenExtraction:
    """Test extract_tokens() covers all providers."""

    def setup_method(self):
        from src.services.llm_usage_tracker import LLMUsageTracker
        self.tracker = LLMUsageTracker()

    def test_ollama_extraction(self):
        response = {"prompt_eval_count": 100, "eval_count": 50, "response": "hi"}
        inp, out = self.tracker.extract_tokens(response, "ollama")
        assert inp == 100
        assert out == 50

    def test_openai_extraction(self):
        response = {"usage": {"prompt_tokens": 200, "completion_tokens": 80}}
        inp, out = self.tracker.extract_tokens(response, "openai")
        assert inp == 200
        assert out == 80

    def test_azure_openai_extraction(self):
        response = {"usage": {"prompt_tokens": 150, "completion_tokens": 60}}
        inp, out = self.tracker.extract_tokens(response, "azure_openai")
        assert inp == 150
        assert out == 60

    def test_anthropic_extraction(self):
        response = {"usage": {"input_tokens": 300, "output_tokens": 120}}
        inp, out = self.tracker.extract_tokens(response, "anthropic")
        assert inp == 300
        assert out == 120

    def test_google_vertex_extraction(self):
        response = {"usageMetadata": {"promptTokenCount": 250, "candidatesTokenCount": 90}}
        inp, out = self.tracker.extract_tokens(response, "google_vertex")
        assert inp == 250
        assert out == 90

    def test_aws_bedrock_extraction(self):
        response = {"usage": {"inputTokens": 180, "outputTokens": 70}}
        inp, out = self.tracker.extract_tokens(response, "aws_bedrock")
        assert inp == 180
        assert out == 70

    def test_lm_studio_extraction(self):
        response = {"usage": {"prompt_tokens": 100, "completion_tokens": 40}}
        inp, out = self.tracker.extract_tokens(response, "lm_studio")
        assert inp == 100
        assert out == 40

    def test_vllm_extraction(self):
        response = {"usage": {"prompt_tokens": 100, "completion_tokens": 40}}
        inp, out = self.tracker.extract_tokens(response, "vllm")
        assert inp == 100
        assert out == 40

    def test_unknown_provider_returns_none(self):
        response = {"usage": {"tokens": 100}}
        inp, out = self.tracker.extract_tokens(response, "unknown_provider")
        assert inp is None
        assert out is None

    def test_empty_response_returns_none(self):
        inp, out = self.tracker.extract_tokens({}, "openai")
        assert inp is None
        assert out is None

    def test_none_response_returns_none(self):
        inp, out = self.tracker.extract_tokens(None, "openai")
        assert inp is None
        assert out is None

    def test_missing_usage_fields(self):
        response = {"usage": {}}
        inp, out = self.tracker.extract_tokens(response, "openai")
        assert inp is None
        assert out is None


# =============================================================================
# LLMCostService Tests
# =============================================================================

class TestLLMCostService:
    """Test the cost service methods."""

    @pytest.mark.asyncio
    async def test_ensure_default_configs_is_noop(self):
        """ensure_default_configs should be a no-op now."""
        from src.services.llm_cost_service import LLMCostService
        db = AsyncMock(spec=AsyncSession)
        await LLMCostService.ensure_default_configs(db)
        # Should not interact with DB at all
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_all_configs(self):
        from src.services.llm_cost_service import LLMCostService
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            MagicMock(model_name="gpt-4o", provider="openai"),
            MagicMock(model_name="llama3", provider="ollama"),
        ]
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        configs = await LLMCostService.get_all_configs(db)
        assert len(configs) == 2
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unpriced_models(self):
        from src.services.llm_cost_service import LLMCostService
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(model_name="new-model", provider="openai", call_count=42, total_tokens=10000),
        ]
        db.execute.return_value = mock_result

        unpriced = await LLMCostService.get_unpriced_models(db)
        assert len(unpriced) == 1
        assert unpriced[0]["model_name"] == "new-model"
        assert unpriced[0]["call_count"] == 42

    @pytest.mark.asyncio
    async def test_upsert_model_config_creates_new(self):
        from src.services.llm_cost_service import LLMCostService
        from src.database.models import LLMModelConfig

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # not found
        db.execute.return_value = mock_result

        config = await LLMCostService.upsert_model_config(
            db,
            model_name="test-model",
            provider="openai",
            cost_per_1m_input_tokens=2.50,
            cost_per_1m_output_tokens=10.00,
        )
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_model_config_updates_existing(self):
        from src.services.llm_cost_service import LLMCostService

        existing = MagicMock()
        existing.provider = "openai"
        existing.cost_per_1m_input_tokens = 5.0
        existing.cost_per_1m_output_tokens = 15.0

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        db.execute.return_value = mock_result

        await LLMCostService.upsert_model_config(
            db,
            model_name="gpt-4o",
            provider="openai",
            cost_per_1m_input_tokens=2.50,
            cost_per_1m_output_tokens=10.00,
        )
        assert existing.cost_per_1m_input_tokens == 2.50
        assert existing.cost_per_1m_output_tokens == 10.00
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_model_config_found(self):
        from src.services.llm_cost_service import LLMCostService

        existing = MagicMock()
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        db.execute.return_value = mock_result

        deleted = await LLMCostService.delete_model_config(db, "gpt-4o", "openai")
        assert deleted is True
        db.delete.assert_called_once_with(existing)

    @pytest.mark.asyncio
    async def test_delete_model_config_not_found(self):
        from src.services.llm_cost_service import LLMCostService

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        deleted = await LLMCostService.delete_model_config(db, "nonexistent", "openai")
        assert deleted is False
        db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_model_config_race_falls_back_to_update(self):
        """If INSERT races and hits IntegrityError, retry should find the row and UPDATE."""
        from sqlalchemy.exc import IntegrityError
        from src.services.llm_cost_service import LLMCostService

        db = AsyncMock(spec=AsyncSession)

        # First lookup: not found → insert path
        first_lookup = MagicMock()
        first_lookup.scalar_one_or_none.return_value = None
        # Second lookup (after rollback): now found → update path
        existing = MagicMock()
        existing.provider = "openai"
        second_lookup = MagicMock()
        second_lookup.scalar_one_or_none.return_value = existing

        db.execute.side_effect = [first_lookup, second_lookup]
        db.commit.side_effect = [
            IntegrityError("stmt", {}, Exception("duplicate")),
            None,
        ]

        result = await LLMCostService.upsert_model_config(
            db,
            model_name="gpt-4o",
            provider="openai",
            cost_per_1m_input_tokens=2.50,
            cost_per_1m_output_tokens=10.00,
        )
        assert result is existing
        assert existing.cost_per_1m_input_tokens == 2.50
        db.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_calculate_cost_no_config_returns_zero(self):
        from src.services.llm_cost_service import LLMCostService

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        cost = await LLMCostService.calculate_cost(db, "unknown-model", 1000, 500)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_calculate_cost_with_config(self):
        from src.services.llm_cost_service import LLMCostService

        config = MagicMock()
        config.cost_per_1m_input_tokens = 2.50
        config.cost_per_1m_output_tokens = 10.00

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        db.execute.return_value = mock_result

        cost = await LLMCostService.calculate_cost(db, "gpt-4o", 1_000_000, 500_000)
        assert cost == pytest.approx(7.50)  # 2.50 + 5.00


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestByProviderEndpoint:
    """Test the enhanced /by-provider endpoint includes cost."""

    def test_by_provider_includes_cost(self):
        from src.api.endpoints.llm_usage import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                provider="openai",
                total_calls=10,
                total_input_tokens=5000,
                total_output_tokens=2000,
                avg_response_time_ms=350.0,
                total_cost=0.05,
            ),
            MagicMock(
                provider="ollama",
                total_calls=50,
                total_input_tokens=25000,
                total_output_tokens=10000,
                avg_response_time_ms=800.0,
                total_cost=0.0,
            ),
        ]
        mock_db.execute.return_value = mock_result

        from src.api.dependencies import get_db
        app.dependency_overrides[get_db] = lambda: mock_db
        client = TestClient(app)
        response = client.get("/llm/usage/by-provider?days=7")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "total_cost_usd" in data[0]
        assert data[0]["total_cost_usd"] == 0.05
        assert data[1]["total_cost_usd"] == 0.0


class TestCostSummaryEndpoint:
    """Test the /cost-summary endpoint."""

    def test_cost_summary_returns_structure(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        mock_db = AsyncMock(spec=AsyncSession)
        # First call: overall totals
        totals_row = MagicMock(
            total_cost=1.25,
            total_input_tokens=50000,
            total_output_tokens=20000,
            total_calls=100,
        )
        totals_result = MagicMock()
        totals_result.one.return_value = totals_row

        # Second call: daily breakdown
        daily_result = MagicMock()
        daily_result.all.return_value = [
            MagicMock(date="2026-04-10", cost=0.50, calls=40, tokens=30000),
            MagicMock(date="2026-04-11", cost=0.75, calls=60, tokens=40000),
        ]

        # Third call: by provider
        provider_result = MagicMock()
        provider_result.all.return_value = [
            MagicMock(provider="openai", cost=1.00),
            MagicMock(provider="ollama", cost=0.25),
        ]

        mock_db.execute.side_effect = [totals_result, daily_result, provider_result]

        app.dependency_overrides[get_db] = lambda: mock_db
        client = TestClient(app)
        response = client.get("/llm/usage/cost-summary?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 30
        assert data["total_cost_usd"] == 1.25
        assert data["total_calls"] == 100
        assert data["avg_cost_per_call"] == pytest.approx(0.0125)
        assert len(data["daily_costs"]) == 2
        assert data["daily_costs"][0]["date"] == "2026-04-10"
        assert "openai" in data["by_provider"]
        assert data["by_provider"]["openai"] == 1.00


class TestProviderComparisonEndpoint:
    """Test the /provider-comparison endpoint."""

    def test_provider_comparison_returns_structure(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                provider="openai", agent_type="sql_generator",
                calls=50, avg_latency=320.0, total_cost=0.10,
                avg_tokens=1200.0, success_count=48,
            ),
            MagicMock(
                provider="ollama", agent_type="sql_generator",
                calls=100, avg_latency=800.0, total_cost=0.0,
                avg_tokens=1100.0, success_count=95,
            ),
        ]
        mock_db.execute.return_value = mock_result

        app.dependency_overrides[get_db] = lambda: mock_db
        client = TestClient(app)
        response = client.get("/llm/usage/provider-comparison?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7
        assert "sql_generator" in data["by_agent_type"]
        assert "openai" in data["by_agent_type"]["sql_generator"]
        openai_stats = data["by_agent_type"]["sql_generator"]["openai"]
        assert openai_stats["calls"] == 50
        assert openai_stats["success_rate"] == pytest.approx(96.0)


class TestModelConfigEndpoints:
    """Test the model config CRUD endpoints."""

    def test_list_model_configs(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.model_name = "gpt-4o"
        mock_config.display_name = "GPT-4o"
        mock_config.provider = "openai"
        mock_config.cost_per_1m_input_tokens = 2.50
        mock_config.cost_per_1m_output_tokens = 10.00
        mock_config.is_active = True

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.llm_cost_service.LLMCostService.get_all_configs", new_callable=AsyncMock, return_value=[mock_config]):
            app.dependency_overrides[get_db] = lambda: mock_db
            client = TestClient(app)
            response = client.get("/llm/usage/model-configs")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_name"] == "gpt-4o"

    def test_list_unpriced_models(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        unpriced = [{"model_name": "new-model", "provider": "anthropic", "call_count": 10, "total_tokens": 5000}]
        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.llm_cost_service.LLMCostService.get_unpriced_models", new_callable=AsyncMock, return_value=unpriced):
            app.dependency_overrides[get_db] = lambda: mock_db
            client = TestClient(app)
            response = client.get("/llm/usage/unpriced-models")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_name"] == "new-model"
        assert data[0]["call_count"] == 10

    def test_create_model_config(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from src.auth.dependencies import require_admin
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.model_name = "new-model"
        mock_config.display_name = "New Model"
        mock_config.provider = "openai"
        mock_config.cost_per_1m_input_tokens = 1.00
        mock_config.cost_per_1m_output_tokens = 3.00
        mock_config.is_active = True

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.llm_cost_service.LLMCostService.upsert_model_config", new_callable=AsyncMock, return_value=mock_config):
            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[require_admin] = lambda: MagicMock(is_admin=True)
            client = TestClient(app)
            response = client.post("/llm/usage/model-configs", json={
                "model_name": "new-model",
                "provider": "openai",
                "cost_per_1m_input_tokens": 1.00,
                "cost_per_1m_output_tokens": 3.00,
                "display_name": "New Model",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "new-model"

    def test_create_model_config_requires_admin(self):
        """Unauthenticated requests to POST /model-configs must be rejected."""
        from src.api.endpoints.llm_usage import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post("/llm/usage/model-configs", json={
            "model_name": "new-model",
            "provider": "openai",
            "cost_per_1m_input_tokens": 1.00,
            "cost_per_1m_output_tokens": 3.00,
        })
        assert response.status_code == 401

    def test_create_model_config_rejects_negative_cost(self):
        from src.api.endpoints.llm_usage import router
        from src.auth.dependencies import require_admin
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_admin] = lambda: MagicMock(is_admin=True)
        client = TestClient(app)
        response = client.post("/llm/usage/model-configs", json={
            "model_name": "new-model",
            "provider": "openai",
            "cost_per_1m_input_tokens": -1.00,
            "cost_per_1m_output_tokens": 3.00,
        })
        assert response.status_code == 422

    def test_delete_model_config_success(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from src.auth.dependencies import require_admin
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.llm_cost_service.LLMCostService.delete_model_config", new_callable=AsyncMock, return_value=True):
            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[require_admin] = lambda: MagicMock(is_admin=True)
            client = TestClient(app)
            response = client.delete("/llm/usage/model-configs/openai/gpt-4o")

        assert response.status_code == 200

    def test_delete_model_config_not_found(self):
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from src.auth.dependencies import require_admin
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.llm_cost_service.LLMCostService.delete_model_config", new_callable=AsyncMock, return_value=False):
            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[require_admin] = lambda: MagicMock(is_admin=True)
            client = TestClient(app)
            response = client.delete("/llm/usage/model-configs/openai/nonexistent")

        assert response.status_code == 404

    def test_delete_model_config_requires_admin(self):
        from src.api.endpoints.llm_usage import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.delete("/llm/usage/model-configs/openai/gpt-4o")
        assert response.status_code == 401

    def test_delete_model_config_with_slash_in_model_name(self):
        """Model IDs from HF/local providers contain slashes (e.g. meta-llama/Llama-3-70b)."""
        from src.api.endpoints.llm_usage import router
        from src.api.dependencies import get_db
        from src.auth.dependencies import require_admin
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        mock_db = AsyncMock(spec=AsyncSession)

        captured = {}

        async def fake_delete(db, model_name, provider):
            captured["model_name"] = model_name
            captured["provider"] = provider
            return True

        with patch(
            "src.services.llm_cost_service.LLMCostService.delete_model_config",
            new=fake_delete,
        ):
            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[require_admin] = lambda: MagicMock(is_admin=True)
            client = TestClient(app)
            response = client.delete(
                "/llm/usage/model-configs/vllm/meta-llama%2FLlama-3-70b"
            )

        assert response.status_code == 200
        assert captured["provider"] == "vllm"
        assert captured["model_name"] == "meta-llama/Llama-3-70b"
