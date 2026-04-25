"""Verify ADMIN_UI_ENABLED kill-switch removes Phase 24 admin routes."""
from unittest.mock import patch

from fastapi.testclient import TestClient


def _build_client(admin_ui_enabled: bool) -> TestClient:
    """Construct a fresh app with the chosen ADMIN_UI_ENABLED value."""
    import importlib
    from src.config import settings as settings_module

    # Reset cached Settings so the new env value is picked up.
    settings_module.Settings.model_config = settings_module.Settings.model_config  # touch
    with patch.dict("os.environ", {"ADMIN_UI_ENABLED": "true" if admin_ui_enabled else "false"}, clear=False):
        # Force a fresh import of main so the conditional include_router runs again.
        import src.main as main
        main = importlib.reload(main)
        return TestClient(main.app)


def test_admin_routes_present_by_default():
    client = _build_client(admin_ui_enabled=True)
    # Without auth, the admin routes still exist (they 401/403, not 404).
    audit = client.get("/api/audit/logs")
    users = client.get("/api/admin/users")
    assert audit.status_code in (401, 403)
    assert users.status_code in (401, 403)


def test_admin_routes_absent_when_disabled():
    client = _build_client(admin_ui_enabled=False)
    audit = client.get("/api/audit/logs")
    users = client.get("/api/admin/users")
    assert audit.status_code == 404
    assert users.status_code == 404
