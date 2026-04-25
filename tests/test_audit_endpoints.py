"""Tests for the audit log API endpoints (Phase 24 admin UI)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from src.api.endpoints.audit import router
from src.auth.audit import AuditLog
from src.auth.dependencies import get_current_active_user, require_admin


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _admin_user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.is_admin = True
    user.is_active = True
    user.username = "admin"
    return user


def _regular_user() -> MagicMock:
    user = MagicMock()
    user.id = 7
    user.is_admin = False
    user.is_active = True
    user.username = "alice"
    return user


def _sample_log(**overrides) -> AuditLog:
    defaults = dict(
        id=1,
        user_id=1,
        username="admin",
        action="login",
        resource_type="user",
        resource_id="1",
        details={"method": "password"},
        ip_address="127.0.0.1",
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return AuditLog(**defaults)


class TestAuditListEndpoint:
    def test_admin_can_list_logs(self):
        app = _make_app()
        admin = _admin_user()
        app.dependency_overrides[require_admin] = lambda: admin

        async def fake_logs(db, **kwargs):
            return [_sample_log(), _sample_log(id=2, action="logout")]

        async def fake_count(db, **kwargs):
            return 2

        with patch("src.api.endpoints.audit.get_audit_logs", new=fake_logs), \
             patch("src.api.endpoints.audit.count_audit_logs", new=fake_count):
            client = TestClient(app)
            resp = client.get("/api/audit/logs")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["limit"] == 50
        assert body["offset"] == 0
        assert len(body["items"]) == 2
        assert body["items"][0]["action"] == "login"
        assert body["items"][1]["action"] == "logout"

    def test_filters_passed_through(self):
        app = _make_app()
        app.dependency_overrides[require_admin] = lambda: _admin_user()

        captured: dict = {}

        async def fake_logs(db, **kwargs):
            captured.update(kwargs)
            return []

        async def fake_count(db, **kwargs):
            return 0

        with patch("src.api.endpoints.audit.get_audit_logs", new=fake_logs), \
             patch("src.api.endpoints.audit.count_audit_logs", new=fake_count):
            client = TestClient(app)
            resp = client.get(
                "/api/audit/logs",
                params={
                    "user_id": 7,
                    "action": "login",
                    "resource_type": "user",
                    "start_date": "2026-04-01T00:00:00+00:00",
                    "end_date": "2026-04-25T00:00:00+00:00",
                    "limit": 10,
                    "offset": 20,
                },
            )
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert captured["user_id"] == 7
        assert captured["action"] == "login"
        assert captured["resource_type"] == "user"
        assert captured["start_date"] == datetime(2026, 4, 1, tzinfo=timezone.utc)
        assert captured["end_date"] == datetime(2026, 4, 25, tzinfo=timezone.utc)
        assert captured["limit"] == 10
        assert captured["offset"] == 20

    def test_non_admin_gets_403(self):
        app = _make_app()

        def deny():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        app.dependency_overrides[require_admin] = deny
        client = TestClient(app)
        resp = client.get("/api/audit/logs")
        app.dependency_overrides.clear()

        assert resp.status_code == 403
        assert "Admin" in resp.json()["detail"]


class TestAuditFacetsEndpoint:
    def test_returns_facets(self):
        app = _make_app()
        app.dependency_overrides[require_admin] = lambda: _admin_user()

        async def fake_facets(db):
            return {"actions": ["login", "logout"], "resource_types": ["user", "connection"]}

        with patch("src.api.endpoints.audit.get_audit_facets", new=fake_facets):
            client = TestClient(app)
            resp = client.get("/api/audit/facets")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body == {
            "actions": ["login", "logout"],
            "resource_types": ["user", "connection"],
        }

    def test_facets_admin_only(self):
        app = _make_app()

        def deny():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        app.dependency_overrides[require_admin] = deny
        client = TestClient(app)
        resp = client.get("/api/audit/facets")
        app.dependency_overrides.clear()

        assert resp.status_code == 403


class TestMyAuditLogs:
    def test_pins_user_id_to_current_user(self):
        app = _make_app()
        user = _regular_user()
        app.dependency_overrides[get_current_active_user] = lambda: user

        captured: dict = {}

        async def fake_logs(db, **kwargs):
            captured.update(kwargs)
            return [_sample_log(user_id=user.id, username=user.username)]

        async def fake_count(db, **kwargs):
            return 1

        with patch("src.api.endpoints.audit.get_audit_logs", new=fake_logs), \
             patch("src.api.endpoints.audit.count_audit_logs", new=fake_count):
            client = TestClient(app)
            # Even if a malicious user tries to pass user_id, the endpoint
            # ignores it and pins to current user.
            resp = client.get("/api/audit/logs/me", params={"user_id": 999})
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        # FastAPI silently drops the unknown user_id query param (not declared);
        # the endpoint always passes the current user's id.
        assert captured["user_id"] == user.id
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["user_id"] == user.id


class TestAuditFilterHelpers:
    @pytest.mark.asyncio
    async def test_count_audit_logs_invokes_db(self):
        from src.auth.audit import count_audit_logs

        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = 5
        db.execute.return_value = result

        n = await count_audit_logs(db, action="login")
        assert n == 5
        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_audit_facets_returns_distinct(self):
        from src.auth.audit import get_audit_facets

        db = AsyncMock()
        # Two execute() calls — actions then resource_types
        actions_result = MagicMock()
        actions_scalars = MagicMock()
        actions_scalars.all.return_value = ["login", "logout"]
        actions_result.scalars.return_value = actions_scalars

        resources_result = MagicMock()
        resources_scalars = MagicMock()
        resources_scalars.all.return_value = ["user", "connection"]
        resources_result.scalars.return_value = resources_scalars

        db.execute.side_effect = [actions_result, resources_result]

        facets = await get_audit_facets(db)
        assert facets == {
            "actions": ["login", "logout"],
            "resource_types": ["user", "connection"],
        }
