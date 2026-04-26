"""Phase C tests — one-shot password reset tokens.

Covers:
- Reset endpoint shape varies with AUTH_PASSWORD_RESET_MODE.
- Redeem endpoint accepts a valid token, rejects unknown / expired / reused
  tokens, and rotates the password / bumps password_version.
- Redeem endpoint 404s when the feature is off.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.api.endpoints.admin_users import router as admin_router
from src.api.endpoints.auth import router as auth_router
from src.auth.dependencies import get_auth_service, require_admin
from src.auth.models import PasswordResetToken, User
from src.auth.service import AuthService
from src.config.settings import Settings
from src.database.connection import Base
from src.middleware.rate_limit import auth_rate_limiter


def _make_settings(*, mode: str = "reset_token", base_url: str = "http://localhost:3000") -> Settings:
    return Settings(
        JWT_SECRET="x" * 32,
        JWT_ALGORITHM="HS256",
        JWT_EXPIRATION_MINUTES=60,
        AUTH_PASSWORD_RESET_MODE=mode,
        AUTH_PASSWORD_RESET_BASE_URL=base_url,
        AUTH_PASSWORD_RESET_TOKEN_TTL_MINUTES=15,
    )


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_user(session_factory):
    async with session_factory() as db:
        u = User(
            email="admin@example.com",
            username="admin",
            hashed_password=AuthService.hash_password("AdminP@ssw0rd1"),
            is_admin=True,
            is_active=True,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return u


@pytest_asyncio.fixture
async def alice(session_factory):
    async with session_factory() as db:
        u = User(
            email="alice@example.com",
            username="alice",
            hashed_password=AuthService.hash_password("OriginalPass99"),
            is_active=True,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)
        return u


def _build_app(settings: Settings, session_factory, admin: User) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")

    async def override_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_service] = lambda: AuthService(settings)
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[auth_rate_limiter] = lambda: None
    return app


# ── Reset endpoint shape ─────────────────────────────────────────────


class TestResetEndpointShape:
    @pytest.mark.asyncio
    async def test_reset_token_mode_returns_token_not_password(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="reset_token")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        r = client.post(f"/api/admin/users/{alice.id}/reset-password")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "reset_token"
        assert body["temporary_password"] is None
        assert body["reset_token"]
        assert body["redemption_url"].startswith("http://localhost:3000/reset?token=")
        assert body["expires_at"]

        # Token row exists, hashed (not equal to plaintext).
        async with session_factory() as db:
            rows = await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == alice.id))
            record = rows.scalar_one()
        assert record.token_hash != body["reset_token"]
        assert record.used_at is None

    @pytest.mark.asyncio
    async def test_both_mode_returns_password_and_token(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="both")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        r = client.post(f"/api/admin/users/{alice.id}/reset-password")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "both"
        assert body["temporary_password"]
        assert body["reset_token"]

    @pytest.mark.asyncio
    async def test_temp_password_mode_unchanged(self, session_factory, admin_user, alice):
        s = _make_settings(mode="temp_password")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        r = client.post(f"/api/admin/users/{alice.id}/reset-password")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "temp_password"
        assert body["temporary_password"]
        assert body["reset_token"] is None
        assert body["redemption_url"] is None


# ── Redeem endpoint ──────────────────────────────────────────────────


class TestRedeemEndpoint:
    @pytest.mark.asyncio
    async def test_redeem_succeeds_and_rotates_password(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="reset_token")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        before_pv = alice.password_version

        # Issue the reset.
        issue = client.post(f"/api/admin/users/{alice.id}/reset-password").json()
        token = issue["reset_token"]

        redeem = client.post(
            "/api/auth/redeem-reset",
            json={"token": token, "new_password": "BrandNewStrong99"},
        )
        assert redeem.status_code == 200, redeem.text
        body = redeem.json()
        assert "access_token" in body
        assert body["user"]["must_change_password"] is False

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == alice.id))
            updated = row.scalar_one()
            tokens = await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == alice.id))
            record = tokens.scalar_one()
        assert AuthService.verify_password("BrandNewStrong99", updated.hashed_password)
        # bump from issuance + bump from redemption.
        assert updated.password_version >= before_pv + 2
        assert record.used_at is not None

    @pytest.mark.asyncio
    async def test_redeem_unknown_token_rejected(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="reset_token")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        r = client.post(
            "/api/auth/redeem-reset",
            json={"token": "completely-bogus-token", "new_password": "NewStrongPass99"},
        )
        assert r.status_code == 401
        assert "invalid" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_redeem_reused_token_rejected(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="reset_token")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        token = client.post(f"/api/admin/users/{alice.id}/reset-password").json()["reset_token"]

        first = client.post(
            "/api/auth/redeem-reset",
            json={"token": token, "new_password": "FirstStrong99x"},
        )
        assert first.status_code == 200
        # Reuse → 401, password not rotated again.
        again = client.post(
            "/api/auth/redeem-reset",
            json={"token": token, "new_password": "SecondStrong99y"},
        )
        assert again.status_code == 401

    @pytest.mark.asyncio
    async def test_redeem_expired_token_rejected(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="reset_token")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        token = client.post(f"/api/admin/users/{alice.id}/reset-password").json()["reset_token"]

        # Expire the row by hand.
        async with session_factory() as db:
            row = await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == alice.id))
            record = row.scalar_one()
            record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()

        r = client.post(
            "/api/auth/redeem-reset",
            json={"token": token, "new_password": "FreshStrong99zz"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_redeem_404_when_feature_off(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="temp_password")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        r = client.post(
            "/api/auth/redeem-reset",
            json={"token": "anything-but-long-enough-to-pass-schema-validation", "new_password": "FreshStrong99zz"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_redeem_rejects_inactive_user(
        self, session_factory, admin_user, alice,
    ):
        s = _make_settings(mode="reset_token")
        app = _build_app(s, session_factory, admin_user)
        client = TestClient(app)
        token = client.post(f"/api/admin/users/{alice.id}/reset-password").json()["reset_token"]

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == alice.id))
            row.scalar_one().is_active = False
            await db.commit()

        r = client.post(
            "/api/auth/redeem-reset",
            json={"token": token, "new_password": "FreshStrong99zz"},
        )
        assert r.status_code == 401
