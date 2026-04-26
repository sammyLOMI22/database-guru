"""Verify ADMIN_UI_ENABLED kill-switch removes Phase 24 admin routes.

Uses the `create_app(settings)` factory directly so the flag is applied
deterministically — no env-var patching, no `importlib.reload` races with
Pydantic's BaseSettings env-read.
"""
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.main import create_app


def _client(admin_ui_enabled: bool) -> TestClient:
    """Build a fresh app with the chosen ADMIN_UI_ENABLED value."""
    settings = Settings(ADMIN_UI_ENABLED=admin_ui_enabled)
    return TestClient(create_app(settings))


def test_admin_routes_present_by_default():
    """When the kill-switch is on, audit + admin routers are mounted."""
    client = _client(admin_ui_enabled=True)

    # Without auth, the routes still exist — they 401/403, not 404.
    audit = client.get("/api/audit/logs")
    users = client.get("/api/admin/users")
    assert audit.status_code in (401, 403), (
        f"Expected 401/403 when ADMIN_UI_ENABLED=true, got {audit.status_code}"
    )
    assert users.status_code in (401, 403), (
        f"Expected 401/403 when ADMIN_UI_ENABLED=true, got {users.status_code}"
    )


def test_admin_routes_absent_when_disabled():
    """When the kill-switch is off, the routers are not mounted at all."""
    client = _client(admin_ui_enabled=False)

    audit = client.get("/api/audit/logs")
    users = client.get("/api/admin/users")
    assert audit.status_code == 404, (
        f"Expected 404 when ADMIN_UI_ENABLED=false, got {audit.status_code}"
    )
    assert users.status_code == 404, (
        f"Expected 404 when ADMIN_UI_ENABLED=false, got {users.status_code}"
    )


def test_admin_routes_absent_in_openapi_schema_when_disabled():
    """OpenAPI schema should not advertise admin paths when the flag is off."""
    client = _client(admin_ui_enabled=False)
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths", {})
    assert not any(p.startswith("/api/audit") for p in paths), (
        "Audit routes leaked into OpenAPI schema with ADMIN_UI_ENABLED=false"
    )
    assert not any(p.startswith("/api/admin/users") for p in paths), (
        "Admin user routes leaked into OpenAPI schema with ADMIN_UI_ENABLED=false"
    )
