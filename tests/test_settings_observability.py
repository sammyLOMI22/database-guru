"""Tests for Phase 24 observability fields exposed via /api/settings."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.endpoints.settings import router
from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings


def _settings_obj(**overrides):
    """Build a SystemSettings-shaped object the response model can validate."""
    base = dict(
        id=1,
        auto_learning_enabled=False,
        confidence_threshold=0.8,
        apply_mode="immediate",
        test_before_learning=True,
        validation_mode="strict",
        require_result_comparison=True,
        enable_audit_log=True,
        max_audit_log_days=90,
        query_quality_level=50,
        enable_intent_classification=True,
        enable_dynamic_examples=True,
        enable_semantic_validation=True,
        model_sql_generation=None,
        model_narratives=None,
        model_query_planning=None,
        model_error_correction=None,
        timeout_sql_generation=30,
        timeout_narratives=15,
        timeout_query_planning=20,
        timeout_error_correction=15,
        enable_query_templates=True,
        enable_location_preprocessing=True,
        enable_prompt_optimization=False,
        prompt_model_size="auto",
        enable_schema_compression=True,
        max_schema_tables=10,
        enable_example_selection=True,
        max_few_shot_examples=3,
        enable_multi_db_validation=True,
        multi_db_validation_threshold=0.6,
        model_lineage_narrative=None,
        model_impact_analysis=None,
        model_schema_health=None,
        model_lineage_conversation=None,
        model_pattern_intelligence=None,
        timeout_lineage_narrative=15,
        timeout_impact_analysis=20,
        timeout_schema_health=30,
        timeout_lineage_conversation=15,
        timeout_pattern_intelligence=20,
        created_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_app(app_settings) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_settings] = lambda: app_settings
    return app


class TestObservabilitySettingsExposure:
    def test_defaults_when_observability_off(self):
        app_settings = SimpleNamespace(
            REQUIRE_AUTH=False,
            METRICS_ENABLED=False,
            METRICS_EXPOSE_ENDPOINT=False,
            METRICS_PUBLIC_URL="",
            OTEL_ENABLED=False,
            OTEL_SERVICE_NAME="database-guru",
            OTEL_TRACES_SAMPLER_RATIO=0.1,
            JAEGER_UI_URL="",
            GRAFANA_URL="",
        )
        app = _build_app(app_settings)
        with patch(
            "src.api.endpoints.settings.get_or_create_settings",
            new=AsyncMock(return_value=_settings_obj()),
        ):
            client = TestClient(app)
            resp = client.get("/api/settings/")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["metrics_enabled"] is False
        assert body["metrics_endpoint_exposed"] is False
        assert body["metrics_public_url"] is None
        assert body["otel_enabled"] is False
        assert body["jaeger_ui_url"] is None
        assert body["grafana_url"] is None
        # Service name + sampler ratio still surface for context
        assert body["otel_service_name"] == "database-guru"
        assert body["otel_traces_sampler_ratio"] == 0.1

    def test_links_when_observability_configured(self):
        app_settings = SimpleNamespace(
            REQUIRE_AUTH=False,
            METRICS_ENABLED=True,
            METRICS_EXPOSE_ENDPOINT=True,
            METRICS_PUBLIC_URL="http://prom.example.com/metrics",
            OTEL_ENABLED=True,
            OTEL_SERVICE_NAME="database-guru",
            OTEL_TRACES_SAMPLER_RATIO=0.25,
            JAEGER_UI_URL="http://jaeger.example.com",
            GRAFANA_URL="http://grafana.example.com/d/abc",
        )
        app = _build_app(app_settings)
        with patch(
            "src.api.endpoints.settings.get_or_create_settings",
            new=AsyncMock(return_value=_settings_obj()),
        ):
            client = TestClient(app)
            resp = client.get("/api/settings/")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["metrics_enabled"] is True
        assert body["metrics_endpoint_exposed"] is True
        assert body["metrics_public_url"] == "http://prom.example.com/metrics"
        assert body["otel_enabled"] is True
        assert body["otel_traces_sampler_ratio"] == 0.25
        assert body["jaeger_ui_url"] == "http://jaeger.example.com"
        assert body["grafana_url"] == "http://grafana.example.com/d/abc"
