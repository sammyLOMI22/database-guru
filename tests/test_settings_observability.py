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
from src.auth.dependencies import get_optional_user


def _admin_user():
    """Return a tiny admin-shaped object the endpoint accepts.

    SystemSettingsResponse only checks ``user.is_admin``; using a SimpleNamespace
    avoids importing the SQLAlchemy User and constructing a session.
    """
    return SimpleNamespace(id=1, username="admin", is_admin=True, is_active=True)


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


def _with_auth_defaults(ns: SimpleNamespace, **overrides) -> SimpleNamespace:
    """Stamp the auth-hardening fields onto an app_settings stub.

    Endpoint reads these unconditionally now; tests can override individual
    flags but most assert the default-off shape.
    """
    defaults = dict(
        AUTH_TOKEN_VERSIONING_ENABLED=False,
        AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE=False,
        AUTH_INVALIDATE_TOKENS_ON_LOGOUT=False,
        AUTH_RATE_LIMIT_CHANGE_PASSWORD=False,
        AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE=5,
        AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=False,
        AUTH_LOGIN_LOCKOUT_THRESHOLD=5,
        AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS=900,
        AUTH_PASSWORD_RESET_MODE="temp_password",
        AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES=15,
        AUTH_PASSWORD_RESET_BASE_URL="",
        AUTH_PASSWORD_HISTORY_DEPTH=0,
        AUTH_REQUIRE_ADMIN_QUORUM=False,
    )
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(ns, k, v)
    return ns


def _build_app(app_settings, *, as_admin: bool = True) -> FastAPI:
    # Auto-stamp auth-hardening defaults if the test didn't set them — these
    # plumb through /api/settings now and would NPE on a bare SimpleNamespace.
    if not hasattr(app_settings, "AUTH_TOKEN_VERSIONING_ENABLED"):
        _with_auth_defaults(app_settings)
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_settings] = lambda: app_settings
    # Auth-hardening fields on the response are admin-gated. Tests that
    # care about those fields run as admin; tests that exercise the public
    # observability subset can pass ``as_admin=False`` to verify the gate.
    app.dependency_overrides[get_optional_user] = (
        (lambda: _admin_user()) if as_admin else (lambda: None)
    )
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
            ADMIN_UI_ENABLED=True,
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
            ADMIN_UI_ENABLED=True,
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
        assert body["admin_ui_enabled"] is True

    def test_auth_hardening_defaults_off(self):
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
            ADMIN_UI_ENABLED=True,
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
        assert body["auth_token_versioning_enabled"] is False
        assert body["auth_invalidate_tokens_on_deactivate"] is False
        assert body["auth_invalidate_tokens_on_logout"] is False
        assert body["auth_rate_limit_change_password"] is False
        assert body["auth_rate_limit_login_lockout_enabled"] is False
        assert body["auth_password_reset_mode"] == "temp_password"
        assert body["auth_password_history_depth"] == 0
        assert body["auth_require_admin_quorum"] is False

    def test_auth_hardening_surfaces_when_enabled(self):
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
            ADMIN_UI_ENABLED=True,
        )
        _with_auth_defaults(
            app_settings,
            AUTH_TOKEN_VERSIONING_ENABLED=True,
            AUTH_RATE_LIMIT_CHANGE_PASSWORD=True,
            AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE=10,
            AUTH_PASSWORD_RESET_MODE="reset_token",
            AUTH_PASSWORD_RESET_BASE_URL="http://localhost:3000",
            AUTH_PASSWORD_HISTORY_DEPTH=5,
            AUTH_REQUIRE_ADMIN_QUORUM=True,
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
        assert body["auth_token_versioning_enabled"] is True
        assert body["auth_rate_limit_change_password"] is True
        assert body["auth_change_password_per_user_per_minute"] == 10
        assert body["auth_password_reset_mode"] == "reset_token"
        assert body["auth_password_reset_base_url"] == "http://localhost:3000"
        assert body["auth_password_history_depth"] == 5
        assert body["auth_require_admin_quorum"] is True

    def test_admin_ui_toggle_surfaces_in_response(self):
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
            ADMIN_UI_ENABLED=False,
        )
        app = _build_app(app_settings)
        with patch(
            "src.api.endpoints.settings.get_or_create_settings",
            new=AsyncMock(return_value=_settings_obj()),
        ):
            client = TestClient(app)
            resp = client.get("/api/settings/")
        assert resp.status_code == 200
        assert resp.json()["admin_ui_enabled"] is False
