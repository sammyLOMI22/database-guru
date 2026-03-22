"""Integration tests for DML API endpoints (Phase 18).

Tests cover:
- POST /dml/preview — DML script generation
- POST /dml/execute — DML execution with auth
- GET /dml/permissions/{id} — permission retrieval
- Cross-user ownership checks (User A vs User B)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.endpoints.dml import router
from src.auth.models import User
from src.database.models import ConnectionWritePermission, DatabaseConnection
from src.dml.models import ChangeType


# ── helpers ──────────────────────────────────────────────────────────


def _make_user(id: int = 1, username: str = "alice", is_admin: bool = False):
    user = MagicMock(spec=User)
    user.id = id
    user.username = username
    user.is_admin = is_admin
    return user


def _make_connection(id: int = 1, owner_id=None, database_type="postgresql"):
    conn = MagicMock(spec=DatabaseConnection)
    conn.id = id
    conn.name = "test-db"
    conn.database_type = database_type
    conn.owner_id = owner_id
    conn.is_deleted = False
    return conn


def _make_permission(**kwargs):
    defaults = dict(
        connection_id=1,
        allow_insert=True,
        allow_update=True,
        allow_delete=True,
        require_where_clause=True,
        max_rows_per_operation=100,
        allowed_tables=None,
    )
    defaults.update(kwargs)
    perm = MagicMock(spec=ConnectionWritePermission)
    for k, v in defaults.items():
        setattr(perm, k, v)
    return perm


def _build_app(db_session, current_user=None, optional_user=None, settings=None):
    """Build a FastAPI app with DML router and overridden dependencies."""
    from src.api.dependencies.common import get_db, get_settings
    from src.auth.dependencies import get_current_user, get_optional_user
    from src.config.settings import Settings

    app = FastAPI()
    app.include_router(router)

    # get_db is an async generator — override with an async generator too
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    if optional_user is not None:
        app.dependency_overrides[get_optional_user] = lambda: optional_user
    else:
        app.dependency_overrides[get_optional_user] = lambda: current_user
    app.dependency_overrides[get_settings] = lambda: settings or Settings(
        ALLOW_WRITE_OPERATIONS=True,
    )

    return app


def _mock_db(connection=_make_connection(), permission=_make_permission()):
    """Create a mock async session that returns connection and permission.

    Uses side_effect list so sequential db.execute() calls return
    the connection result first, then the permission result.
    Pass connection=None or permission=None to simulate missing records.
    """
    db = AsyncMock()

    conn_result = MagicMock()
    conn_result.scalar_one_or_none.return_value = connection

    perm_result = MagicMock()
    perm_result.scalar_one_or_none.return_value = permission

    db.execute = AsyncMock(side_effect=[conn_result, perm_result])
    return db


# ── preview endpoint ─────────────────────────────────────────────────


class TestPreviewEndpoint:
    def test_preview_returns_sql_script(self):
        conn = _make_connection()
        db = _mock_db(connection=conn)
        user = _make_user()
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "old", "new_value": "new"}],
            }],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["change_count"] == 1
        assert "UPDATE" in data["sql"]
        assert data["summary"]["UPDATE"] == 1

    def test_preview_insert(self):
        conn = _make_connection()
        db = _mock_db(connection=conn)
        user = _make_user()
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "INSERT",
                "table_name": "users",
                "primary_key": {},
                "changes": [],
                "new_row_data": {"name": "Bob", "email": "bob@test.com"},
            }],
        })

        assert response.status_code == 200
        data = response.json()
        assert "INSERT" in data["sql"]
        assert data["summary"]["INSERT"] == 1

    def test_preview_delete(self):
        conn = _make_connection()
        db = _mock_db(connection=conn)
        user = _make_user()
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "DELETE",
                "table_name": "orders",
                "primary_key": {"id": 42},
                "changes": [],
            }],
        })

        assert response.status_code == 200
        data = response.json()
        assert "DELETE" in data["sql"]
        assert data["summary"]["DELETE"] == 1

    def test_preview_404_for_missing_connection(self):
        db = _mock_db(connection=None)
        user = _make_user()
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 999,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
            }],
        })

        assert response.status_code == 404


# ── cross-user ownership ────────────────────────────────────────────


class TestCrossUserOwnership:
    def test_preview_rejects_wrong_owner(self):
        """User B cannot preview changes on User A's connection."""
        conn = _make_connection(owner_id=1)  # owned by user 1
        db = _mock_db(connection=conn)
        user_b = _make_user(id=99, username="bob")  # user 99
        app = _build_app(db, current_user=user_b)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
            }],
        })

        assert response.status_code == 403
        assert "access" in response.json()["detail"].lower()

    def test_preview_allows_owner(self):
        """Owner can preview their own connection."""
        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        owner = _make_user(id=1, username="alice")
        app = _build_app(db, current_user=owner)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
            }],
        })

        assert response.status_code == 200

    def test_preview_allows_unowned_connection(self):
        """Unowned connections are accessible to any user."""
        conn = _make_connection(owner_id=None)
        db = _mock_db(connection=conn)
        user = _make_user(id=50)
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.post("/dml/preview", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
            }],
        })

        assert response.status_code == 200

    def test_execute_rejects_wrong_owner(self):
        """User B cannot execute DML on User A's connection."""
        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        user_b = _make_user(id=99, username="bob")
        app = _build_app(db, current_user=user_b)
        client = TestClient(app)

        response = client.post("/dml/execute", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
            }],
        })

        assert response.status_code == 403


# ── execute endpoint ─────────────────────────────────────────────────


class TestExecuteEndpoint:
    def _execute_with_mock(self, client, changes, exec_result):
        """Run execute endpoint with validator and executor mocked."""
        with patch("src.api.endpoints.dml.DMLValidator") as MockValidator, \
             patch("src.api.endpoints.dml.DMLExecutor") as MockExecutor:
            mock_val = AsyncMock()
            mock_val.validate.return_value = (True, None)
            MockValidator.return_value = mock_val

            mock_exec = AsyncMock()
            mock_exec.execute.return_value = exec_result
            MockExecutor.return_value = mock_exec

            return client.post("/dml/execute", json={
                "connection_id": 1,
                "changes": changes,
            })

    def test_execute_succeeds(self):
        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        user = _make_user(id=1)
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        from src.dml.models import ExecutionResult
        response = self._execute_with_mock(client, [{
            "change_type": "UPDATE",
            "table_name": "users",
            "primary_key": {"id": 1},
            "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
        }], ExecutionResult(success=True, rows_affected=1, executed_sql="UPDATE ..."))

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rows_affected"] == 1

    def test_execute_insert(self):
        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        user = _make_user(id=1)
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        from src.dml.models import ExecutionResult
        response = self._execute_with_mock(client, [{
            "change_type": "INSERT",
            "table_name": "users",
            "primary_key": {},
            "changes": [],
            "new_row_data": {"name": "Bob", "email": "bob@test.com"},
        }], ExecutionResult(success=True, rows_affected=1, executed_sql="INSERT ..."))

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_execute_delete(self):
        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        user = _make_user(id=1)
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        from src.dml.models import ExecutionResult
        response = self._execute_with_mock(client, [{
            "change_type": "DELETE",
            "table_name": "orders",
            "primary_key": {"id": 42},
            "changes": [],
        }], ExecutionResult(success=True, rows_affected=3, executed_sql="DELETE ..."))

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rows_affected"] == 3

    def test_execute_rejects_writes_disabled(self):
        """Global ALLOW_WRITE_OPERATIONS=false blocks execution."""
        from src.config.settings import Settings

        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        user = _make_user(id=1)
        settings = Settings(ALLOW_WRITE_OPERATIONS=False)
        app = _build_app(db, current_user=user, settings=settings)
        client = TestClient(app)

        response = client.post("/dml/execute", json={
            "connection_id": 1,
            "changes": [{
                "change_type": "UPDATE",
                "table_name": "users",
                "primary_key": {"id": 1},
                "changes": [{"column": "name", "old_value": "a", "new_value": "b"}],
            }],
        })

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


# ── permissions endpoint ─────────────────────────────────────────────


class TestPermissionsEndpoint:
    def test_get_permissions_returns_disabled_when_none(self):
        conn = _make_connection()
        db = _mock_db(connection=conn, permission=None)
        user = _make_user()
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.get("/dml/permissions/1")

        assert response.status_code == 200
        data = response.json()
        assert data["write_enabled"] is False

    def test_get_permissions_returns_config(self):
        conn = _make_connection()
        perm = _make_permission(allow_insert=True, allow_delete=False)
        db = _mock_db(connection=conn, permission=perm)
        user = _make_user()
        app = _build_app(db, current_user=user)
        client = TestClient(app)

        response = client.get("/dml/permissions/1")

        assert response.status_code == 200
        data = response.json()
        assert data["write_enabled"] is True
        assert data["allow_insert"] is True
        assert data["allow_delete"] is False

    def test_get_permissions_rejects_wrong_owner(self):
        conn = _make_connection(owner_id=1)
        db = _mock_db(connection=conn)
        user_b = _make_user(id=99)
        app = _build_app(db, current_user=user_b)
        client = TestClient(app)

        response = client.get("/dml/permissions/1")

        assert response.status_code == 403
