"""Phase B tests — change-password rate limit + login lockout.

The limiter is in-process and keyed by user.id; the lockout tracker is
in-process and keyed by lowercase username. Both reset between tests via
the shared module-level singletons' ``reset()`` helpers.
"""
import asyncio

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.api.endpoints.auth import router as auth_router
from src.auth.dependencies import get_auth_service, get_current_active_user
from src.auth.models import User
from src.auth.service import AuthService
from src.config.settings import Settings
from src.database.connection import Base
from src.middleware.rate_limit import (
    auth_rate_limiter,
    change_password_rate_limiter,
    login_attempt_tracker,
)


@pytest.fixture(autouse=True)
def _reset_limiters():
    change_password_rate_limiter.reset()
    login_attempt_tracker.reset()
    yield
    change_password_rate_limiter.reset()
    login_attempt_tracker.reset()


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def stored_user(session_factory):
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


def _build_login_app(settings: Settings, session_factory) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")

    async def override_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: AuthService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    # Bypass the global per-IP auth rate limiter so the test can hammer login.
    app.dependency_overrides[auth_rate_limiter] = lambda: None
    return app


def _build_change_password_app(settings: Settings, session_factory, current_user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")

    async def override_db():
        async with session_factory() as db:
            yield db

    from fastapi import Depends as _Depends

    async def reload_user(db: AsyncSession = _Depends(get_db)) -> User:
        row = await db.execute(select(User).where(User.id == current_user.id))
        return row.scalar_one()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: AuthService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_current_active_user] = reload_user
    app.dependency_overrides[auth_rate_limiter] = lambda: None
    return app


# ── Change-password rate limit ──────────────────────────────────────


class TestChangePasswordRateLimit:
    @pytest.mark.asyncio
    async def test_disabled_flag_is_unlimited(self, stored_user, session_factory):
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_CHANGE_PASSWORD=False,
            AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE=2,
        )
        app = _build_change_password_app(s, session_factory, stored_user)
        client = TestClient(app)
        # 6 attempts with the wrong current password — all should 401, none 429.
        for _ in range(6):
            r = client.post(
                "/api/auth/change-password",
                json={"current_password": "wrong", "new_password": "FreshPass99x"},
            )
            assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_enforced_when_enabled(self, stored_user, session_factory):
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_CHANGE_PASSWORD=True,
            AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE=3,
        )
        app = _build_change_password_app(s, session_factory, stored_user)
        client = TestClient(app)
        # First 3 fail with 401 (wrong password) — they still count as attempts.
        for _ in range(3):
            r = client.post(
                "/api/auth/change-password",
                json={"current_password": "wrong", "new_password": "FreshPass99x"},
            )
            assert r.status_code == 401
        # 4th is rate-limited regardless of whether the password is right.
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "OriginalPass99", "new_password": "FreshPass99x"},
        )
        assert r.status_code == 429
        assert "Retry-After" in r.headers


# ── Login lockout ───────────────────────────────────────────────────


class TestLoginLockout:
    @pytest.mark.asyncio
    async def test_disabled_flag_no_lockout(self, stored_user, session_factory):
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=False,
            AUTH_LOGIN_LOCKOUT_THRESHOLD=3,
            AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS=900,
        )
        app = _build_login_app(s, session_factory)
        client = TestClient(app)
        for _ in range(5):
            r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
            assert r.status_code == 401  # never 429

    @pytest.mark.asyncio
    async def test_locks_after_threshold(self, stored_user, session_factory):
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=True,
            AUTH_LOGIN_LOCKOUT_THRESHOLD=3,
            AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS=900,
        )
        app = _build_login_app(s, session_factory)
        client = TestClient(app)
        for _ in range(3):
            r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
            assert r.status_code == 401
        # 4th attempt — even with the correct password — gets locked out.
        r = client.post("/api/auth/login", json={"username": "alice", "password": "OriginalPass99"})
        assert r.status_code == 429
        assert int(r.headers["Retry-After"]) > 0

    @pytest.mark.asyncio
    async def test_case_insensitive_lockout_key(self, stored_user, session_factory):
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=True,
            AUTH_LOGIN_LOCKOUT_THRESHOLD=3,
            AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS=900,
        )
        app = _build_login_app(s, session_factory)
        client = TestClient(app)
        # Three failures spread across casings — they all key to the same bucket.
        for name in ("alice", "ALICE", "Alice"):
            r = client.post("/api/auth/login", json={"username": name, "password": "wrong"})
            assert r.status_code == 401
        r = client.post("/api/auth/login", json={"username": "alice", "password": "OriginalPass99"})
        assert r.status_code == 429

    @pytest.mark.asyncio
    async def test_success_clears_counter(self, stored_user, session_factory):
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=True,
            AUTH_LOGIN_LOCKOUT_THRESHOLD=3,
            AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS=900,
        )
        app = _build_login_app(s, session_factory)
        client = TestClient(app)
        # 2 failures, then a success — counter resets, so 2 more failures don't lock.
        for _ in range(2):
            assert client.post(
                "/api/auth/login", json={"username": "alice", "password": "wrong"}
            ).status_code == 401
        ok = client.post(
            "/api/auth/login", json={"username": "alice", "password": "OriginalPass99"}
        )
        assert ok.status_code == 200
        for _ in range(2):
            assert client.post(
                "/api/auth/login", json={"username": "alice", "password": "wrong"}
            ).status_code == 401
        # Still under the new window — the 3rd failure since reset will lock.

    @pytest.mark.asyncio
    async def test_unknown_username_still_counts(self, session_factory):
        """Failures on unknown usernames must count too; otherwise an attacker
        could enumerate users by watching for lockout vs. plain 401."""
        s = Settings(
            JWT_SECRET="x" * 32, JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60,
            AUTH_RATE_LIMIT_LOGIN_LOCKOUT_ENABLED=True,
            AUTH_LOGIN_LOCKOUT_THRESHOLD=2,
            AUTH_LOGIN_LOCKOUT_WINDOW_SECONDS=900,
        )
        app = _build_login_app(s, session_factory)
        client = TestClient(app)
        for _ in range(2):
            assert client.post(
                "/api/auth/login", json={"username": "ghost", "password": "x"}
            ).status_code == 401
        r = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
        assert r.status_code == 429


# ── Tracker unit tests ──────────────────────────────────────────────


class TestLoginAttemptTracker:
    @pytest.mark.asyncio
    async def test_locks_and_unlocks_after_window(self, monkeypatch):
        from src.middleware.rate_limit import LoginAttemptTracker
        import src.middleware.rate_limit as rl

        tracker = LoginAttemptTracker()
        clock = {"t": 1000.0}
        monkeypatch.setattr(rl.time, "time", lambda: clock["t"])

        for _ in range(3):
            await tracker.record_failure("bob", window_s=60)
        locked, retry = await tracker.is_locked("bob", threshold=3, window_s=60)
        assert locked is True
        assert retry > 0

        # Advance past the window — the counter rolls off and lock clears.
        clock["t"] += 61
        locked, retry = await tracker.is_locked("bob", threshold=3, window_s=60)
        assert locked is False
        assert retry == 0
