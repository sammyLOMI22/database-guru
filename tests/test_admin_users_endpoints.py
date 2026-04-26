"""Tests for /api/admin/users endpoints (Phase 24)."""
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.api.endpoints.admin_users import router, _generate_temp_password
from src.auth.audit import AuditLog
from src.auth.dependencies import get_auth_service, require_admin
from src.auth.models import User
from src.auth.service import AuthService
from src.config.settings import Settings
from src.database.connection import Base


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def seed_users(session_factory):
    """Insert one admin and a couple of regular users."""
    auth_service = AuthService(Settings(JWT_SECRET="test", JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60))
    async with session_factory() as db:
        admin = User(
            email="admin@example.com",
            username="admin",
            hashed_password=auth_service.hash_password("AdminP@ssw0rd1"),
            is_admin=True,
            is_active=True,
        )
        alice = User(
            email="alice@example.com",
            username="alice",
            hashed_password=auth_service.hash_password("AlicePass1234"),
            is_active=True,
        )
        bob = User(
            email="bob@example.com",
            username="bob",
            hashed_password=auth_service.hash_password("BobPass1234"),
            is_active=False,  # already inactive
        )
        db.add_all([admin, alice, bob])
        await db.commit()
        await db.refresh(admin)
        await db.refresh(alice)
        await db.refresh(bob)
        return {"admin": admin, "alice": alice, "bob": bob}


@pytest.fixture
def app_factory(session_factory):
    """Build a FastAPI app wired to the in-memory session and a configurable user."""

    auth_service = AuthService(
        Settings(JWT_SECRET="test", JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60)
    )

    def make_app(
        *,
        current_user: User | None,
        override_admin: bool = True,
        settings: Settings | None = None,
    ) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/api")

        async def override_db():
            async with session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_auth_service] = lambda: auth_service
        # Tests can pass custom settings to flip Phase A flags.
        app.dependency_overrides[get_settings] = lambda: settings or Settings(
            JWT_SECRET="test", JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
        )

        if override_admin:
            if current_user is None:
                async def deny():
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
                app.dependency_overrides[require_admin] = deny
            else:
                app.dependency_overrides[require_admin] = lambda: current_user
        return app

    return make_app


async def _all_audit_actions(session_factory) -> list[str]:
    from sqlalchemy import select
    async with session_factory() as db:
        rows = await db.execute(select(AuditLog.action))
        return list(rows.scalars().all())


# ── Helper tests ─────────────────────────────────────────────────────


class TestGenerateTempPassword:
    def test_meets_complexity(self):
        for _ in range(20):
            pw = _generate_temp_password()
            assert len(pw) == 16
            assert any(c.isupper() for c in pw)
            assert any(c.islower() for c in pw)
            assert any(c.isdigit() for c in pw)


# ── List endpoint ────────────────────────────────────────────────────


class TestListUsers:
    @pytest.mark.asyncio
    async def test_lists_all_with_total(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.get("/api/admin/users")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert {u["username"] for u in body["items"]} == {"admin", "alice", "bob"}

    @pytest.mark.asyncio
    async def test_search_filter(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.get("/api/admin/users", params={"search": "ali"})
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_active_filter(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.get("/api/admin/users", params={"is_active": "false"})
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["username"] == "bob"

    @pytest.mark.asyncio
    async def test_pagination(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.get("/api/admin/users", params={"limit": 2, "offset": 0})
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2

    @pytest.mark.asyncio
    async def test_non_admin_403(self, app_factory):
        app = app_factory(current_user=None)
        client = TestClient(app)
        resp = client.get("/api/admin/users")
        assert resp.status_code == 403


# ── Update endpoint ──────────────────────────────────────────────────


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_promote_to_admin_writes_audit(self, app_factory, seed_users, session_factory):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.patch(
            f"/api/admin/users/{seed_users['alice'].id}",
            json={"is_admin": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True
        actions = await _all_audit_actions(session_factory)
        assert "admin_update_user" in actions

    @pytest.mark.asyncio
    async def test_admin_cannot_demote_self(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.patch(
            f"/api/admin/users/{seed_users['admin'].id}",
            json={"is_admin": False},
        )
        assert resp.status_code == 400
        assert "demote" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_self_via_patch(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.patch(
            f"/api/admin/users/{seed_users['admin'].id}",
            json={"is_active": False},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_404_for_unknown_user(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.patch("/api/admin/users/9999", json={"is_active": False})
        assert resp.status_code == 404


# ── Phase A: token-versioning bumps ─────────────────────────────────


class TestDeactivateInvalidationFlag:
    @pytest.mark.asyncio
    async def test_deactivate_does_not_bump_when_flag_off(self, app_factory, seed_users, session_factory):
        from sqlalchemy import select

        before = seed_users["alice"].password_version
        app = app_factory(current_user=seed_users["admin"])  # default settings -> flag off
        client = TestClient(app)
        r = client.delete(f"/api/admin/users/{seed_users['alice'].id}")
        assert r.status_code == 204

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == seed_users["alice"].id))
            alice = row.scalar_one()
        assert alice.is_active is False
        assert alice.password_version == before  # untouched

    @pytest.mark.asyncio
    async def test_deactivate_bumps_when_flag_on(self, app_factory, seed_users, session_factory):
        from sqlalchemy import select

        before = seed_users["alice"].password_version
        s = Settings(
            JWT_SECRET="test", JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_INVALIDATE_TOKENS_ON_DEACTIVATE=True,
        )
        app = app_factory(current_user=seed_users["admin"], settings=s)
        client = TestClient(app)
        r = client.delete(f"/api/admin/users/{seed_users['alice'].id}")
        assert r.status_code == 204

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == seed_users["alice"].id))
            alice = row.scalar_one()
        assert alice.is_active is False
        assert alice.password_version == before + 1


# ── Reset password ───────────────────────────────────────────────────


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_returns_temp_password_and_updates_hash(self, app_factory, seed_users, session_factory):
        from sqlalchemy import select

        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.post(f"/api/admin/users/{seed_users['alice'].id}/reset-password")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == seed_users["alice"].id
        temp = body["temporary_password"]
        assert len(temp) == 16
        # Operator-driven reset must flag the account so the next login is
        # forced through the change-password flow.
        assert body["must_change_password"] is True

        # Hash actually rotated and verifies against the temp password.
        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == seed_users["alice"].id))
            alice = row.scalar_one()
        assert AuthService.verify_password(temp, alice.hashed_password)
        assert alice.must_change_password is True
        # Phase A: admin reset bumps password_version so any token the user
        # may already hold is invalidated on next request.
        assert alice.password_version > 1

        actions = await _all_audit_actions(session_factory)
        assert "admin_reset_password" in actions


# ── Create user ──────────────────────────────────────────────────────


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_admin_can_create_user(self, app_factory, seed_users, session_factory):
        from sqlalchemy import select

        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "carol@example.com",
                "username": "carol",
                "password": "CarolPass1234",
                "is_admin": True,
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["username"] == "carol"
        assert body["is_admin"] is True

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.username == "carol"))
            assert row.scalar_one() is not None

    @pytest.mark.asyncio
    async def test_duplicate_username_409(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "alice2@example.com",
                "username": "alice",
                "password": "AlicePass1234",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_weak_password_422(self, app_factory, seed_users):
        """Passwords missing uppercase/lowercase/digit are 422, not 409."""
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        # Length OK (12), but all-lowercase + no digit fails complexity.
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "weak@example.com",
                "username": "weak",
                "password": "alllowercase",
            },
        )
        assert resp.status_code == 422, resp.text
        # Confirm the error came from the password validator, not duplicate-email.
        assert any("password" in str(e.get("loc", [])).lower() for e in resp.json()["detail"])


# ── Deactivate ───────────────────────────────────────────────────────


class TestDeactivate:
    @pytest.mark.asyncio
    async def test_deactivate_sets_is_active_false(self, app_factory, seed_users, session_factory):
        from sqlalchemy import select

        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.delete(f"/api/admin/users/{seed_users['alice'].id}")
        assert resp.status_code == 204

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == seed_users["alice"].id))
            alice = row.scalar_one()
        assert alice.is_active is False

        actions = await _all_audit_actions(session_factory)
        assert "admin_deactivate_user" in actions

    @pytest.mark.asyncio
    async def test_deactivate_idempotent(self, app_factory, seed_users, session_factory):
        # bob is already inactive — should still 204 with no extra audit entry.
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        before = await _all_audit_actions(session_factory)
        resp = client.delete(f"/api/admin/users/{seed_users['bob'].id}")
        assert resp.status_code == 204
        after = await _all_audit_actions(session_factory)
        assert after.count("admin_deactivate_user") == before.count("admin_deactivate_user")

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_self(self, app_factory, seed_users):
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.delete(f"/api/admin/users/{seed_users['admin'].id}")
        assert resp.status_code == 400


# ── Self-reset-password guard (H1) ───────────────────────────────────


class TestResetPasswordSelfGuard:
    @pytest.mark.asyncio
    async def test_admin_cannot_reset_own_password(self, app_factory, seed_users, session_factory):
        """An admin must use the self-service /api/auth flow, not this endpoint."""
        app = app_factory(current_user=seed_users["admin"])
        client = TestClient(app)
        resp = client.post(f"/api/admin/users/{seed_users['admin'].id}/reset-password")
        assert resp.status_code == 400
        assert "own password" in resp.json()["detail"].lower()

        # Also confirms no audit entry was written for the rejected attempt.
        actions = await _all_audit_actions(session_factory)
        assert "admin_reset_password" not in actions


# ── Non-admin 403 probes for every mutating endpoint (H3) ────────────


class TestNonAdminForbidden:
    """Each endpoint must return 403 for callers without `require_admin`.

    Catches accidental drops of the dependency on a single route — the kind
    of regression that wouldn't surface from positive-path tests.
    """

    @pytest.mark.asyncio
    async def test_create_403(self, app_factory):
        app = app_factory(current_user=None)
        client = TestClient(app)
        resp = client.post(
            "/api/admin/users",
            json={
                "email": "x@example.com",
                "username": "x",
                "password": "StrongPass1234",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_403(self, app_factory, seed_users):
        app = app_factory(current_user=None)
        client = TestClient(app)
        resp = client.patch(
            f"/api/admin/users/{seed_users['alice'].id}",
            json={"is_admin": True},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_reset_password_403(self, app_factory, seed_users):
        app = app_factory(current_user=None)
        client = TestClient(app)
        resp = client.post(f"/api/admin/users/{seed_users['alice'].id}/reset-password")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_deactivate_403(self, app_factory, seed_users):
        app = app_factory(current_user=None)
        client = TestClient(app)
        resp = client.delete(f"/api/admin/users/{seed_users['alice'].id}")
        assert resp.status_code == 403
