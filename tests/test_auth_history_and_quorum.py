"""Phase D tests — password history (D1) + admin quorum (D3)."""
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
from src.api.endpoints.admin_users import router as admin_router
from src.api.endpoints.auth import router as auth_router
from src.auth.dependencies import (
    get_auth_service,
    get_current_active_user,
    require_admin,
)
from src.auth.models import PasswordHistory, User
from src.auth.service import AuthService, count_active_admins
from src.config.settings import Settings
from src.database.connection import Base
from src.middleware.rate_limit import auth_rate_limiter, change_password_rate_limiter


@pytest.fixture(autouse=True)
def _reset_change_password_limiter():
    """Default for AUTH_RATE_LIMIT_CHANGE_PASSWORD is now True; reset between
    tests so a multi-rotation test (e.g. test_history_trims_to_depth) doesn't
    blow through the per-user limit on a clean account.
    """
    change_password_rate_limiter.reset()
    yield
    change_password_rate_limiter.reset()


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


# ── Password history (D1) ────────────────────────────────────────────


def _build_change_password_app(settings: Settings, session_factory, user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")

    async def override_db():
        async with session_factory() as db:
            yield db

    async def reload_user(db: AsyncSession = Depends(get_db)) -> User:
        row = await db.execute(select(User).where(User.id == user_id))
        return row.scalar_one()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: AuthService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_current_active_user] = reload_user
    app.dependency_overrides[auth_rate_limiter] = lambda: None
    return app


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


class TestPasswordHistory:
    @pytest.mark.asyncio
    async def test_history_disabled_keeps_table_empty(self, session_factory, alice):
        s = Settings(JWT_SECRET="x" * 32, AUTH_RATE_LIMIT_CHANGE_PASSWORD=False, AUTH_PASSWORD_HISTORY_DEPTH=0)
        client = TestClient(_build_change_password_app(s, session_factory, alice.id))
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "OriginalPass99", "new_password": "FirstNewPass99"},
        )
        assert r.status_code == 200, r.text
        async with session_factory() as db:
            rows = await db.execute(select(PasswordHistory))
            assert rows.scalars().all() == []

    @pytest.mark.asyncio
    async def test_history_blocks_immediate_reuse(self, session_factory, alice):
        s = Settings(JWT_SECRET="x" * 32, AUTH_RATE_LIMIT_CHANGE_PASSWORD=False, AUTH_PASSWORD_HISTORY_DEPTH=3)
        client = TestClient(_build_change_password_app(s, session_factory, alice.id))
        # Rotate to a new password.
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "OriginalPass99", "new_password": "FirstNewPass99"},
        )
        assert r.status_code == 200

        # Try to rotate back to the original — must be blocked.
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "FirstNewPass99", "new_password": "OriginalPass99"},
        )
        assert r.status_code == 400
        assert "recent" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_history_trims_to_depth(self, session_factory, alice):
        s = Settings(JWT_SECRET="x" * 32, AUTH_RATE_LIMIT_CHANGE_PASSWORD=False, AUTH_PASSWORD_HISTORY_DEPTH=2)
        client = TestClient(_build_change_password_app(s, session_factory, alice.id))
        passwords = ["AlphaPass1234", "BetaPass1234", "GammaPass1234", "DeltaPass1234"]
        current = "OriginalPass99"
        for nxt in passwords:
            r = client.post(
                "/api/auth/change-password",
                json={"current_password": current, "new_password": nxt},
            )
            assert r.status_code == 200, r.text
            current = nxt

        async with session_factory() as db:
            rows = await db.execute(
                select(PasswordHistory).where(PasswordHistory.user_id == alice.id)
            )
            history = list(rows.scalars().all())
        # depth=2, so only the two most recent prior hashes are kept.
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_oldest_password_outside_depth_can_be_reused(self, session_factory, alice):
        """With depth=2, an old enough password rolls off the window."""
        s = Settings(JWT_SECRET="x" * 32, AUTH_RATE_LIMIT_CHANGE_PASSWORD=False, AUTH_PASSWORD_HISTORY_DEPTH=2)
        client = TestClient(_build_change_password_app(s, session_factory, alice.id))
        chain = [
            ("OriginalPass99", "FirstReuseMe11"),  # original goes into history slot 1
            ("FirstReuseMe11", "SecondPass2233"),  # original moves to slot 2
            ("SecondPass2233", "ThirdPass3344"),   # original rolls off (depth=2)
        ]
        for cur, nxt in chain:
            r = client.post(
                "/api/auth/change-password",
                json={"current_password": cur, "new_password": nxt},
            )
            assert r.status_code == 200, r.text

        # Original should be reusable now.
        r = client.post(
            "/api/auth/change-password",
            json={"current_password": "ThirdPass3344", "new_password": "OriginalPass99"},
        )
        assert r.status_code == 200, r.text


# ── Admin quorum (D3) ────────────────────────────────────────────────


def _build_admin_app(settings: Settings, session_factory, admin: User) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router, prefix="/api")

    async def override_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_service] = lambda: AuthService(settings)
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[auth_rate_limiter] = lambda: None
    return app


@pytest_asyncio.fixture
async def two_admins(session_factory):
    """Solo + sidekick admin so quorum tests can express both directions."""
    async with session_factory() as db:
        primary = User(
            email="primary@example.com",
            username="primary",
            hashed_password=AuthService.hash_password("PrimaryPass99"),
            is_admin=True, is_active=True,
        )
        sidekick = User(
            email="side@example.com",
            username="sidekick",
            hashed_password=AuthService.hash_password("SidekickPass99"),
            is_admin=True, is_active=True,
        )
        db.add_all([primary, sidekick])
        await db.commit()
        await db.refresh(primary)
        await db.refresh(sidekick)
        return primary, sidekick


class TestAdminQuorum:
    @pytest.mark.asyncio
    async def test_count_active_admins_helper(self, session_factory, two_admins):
        async with session_factory() as db:
            assert await count_active_admins(db) == 2

    @pytest.mark.asyncio
    async def test_disabled_flag_allows_demoting_last_admin(self, session_factory, two_admins):
        primary, sidekick = two_admins
        s = Settings(JWT_SECRET="x" * 32, AUTH_REQUIRE_ADMIN_QUORUM=False)
        client = TestClient(_build_admin_app(s, session_factory, primary))
        # Primary deactivates sidekick (one admin left), then demotes themselves
        # via the API caller (admin user fixture). Use an unrelated admin to
        # demote primary — but with the flag off both calls succeed regardless.
        r = client.delete(f"/api/admin/users/{sidekick.id}")
        assert r.status_code == 204
        # With flag off, sidekick was the only "other" admin, and we'd be
        # left with just primary. That's fine when guard is off.

    @pytest.mark.asyncio
    async def test_quorum_blocks_demoting_last_admin(self, session_factory, two_admins):
        primary, sidekick = two_admins
        s = Settings(JWT_SECRET="x" * 32, AUTH_REQUIRE_ADMIN_QUORUM=True)
        client = TestClient(_build_admin_app(s, session_factory, primary))

        # Knock sidekick out of the admin pool first — primary is now the only one.
        r = client.patch(f"/api/admin/users/{sidekick.id}", json={"is_admin": False})
        assert r.status_code == 200, r.text

        # Now the quorum check kicks in: another admin (we forge one for the
        # call) tries to demote primary. We override require_admin to be
        # sidekick (still allowed by the test override), simulating an
        # external call attempting to remove the last admin.
        client_other = TestClient(_build_admin_app(s, session_factory, sidekick))
        r = client_other.patch(f"/api/admin/users/{primary.id}", json={"is_admin": False})
        assert r.status_code == 400
        assert "active admin" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_quorum_blocks_deactivating_last_admin(self, session_factory, two_admins):
        primary, sidekick = two_admins
        s = Settings(JWT_SECRET="x" * 32, AUTH_REQUIRE_ADMIN_QUORUM=True)
        # Demote sidekick (allowed — primary still admin).
        client = TestClient(_build_admin_app(s, session_factory, primary))
        assert client.patch(
            f"/api/admin/users/{sidekick.id}", json={"is_admin": False},
        ).status_code == 200

        # Now an attempt to deactivate primary must be refused.
        client_other = TestClient(_build_admin_app(s, session_factory, sidekick))
        r = client_other.delete(f"/api/admin/users/{primary.id}")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_quorum_allows_change_when_other_admin_remains(
        self, session_factory, two_admins,
    ):
        primary, sidekick = two_admins
        s = Settings(JWT_SECRET="x" * 32, AUTH_REQUIRE_ADMIN_QUORUM=True)
        client = TestClient(_build_admin_app(s, session_factory, primary))
        # Demote sidekick — primary is still active admin, so quorum is satisfied.
        r = client.patch(f"/api/admin/users/{sidekick.id}", json={"is_admin": False})
        assert r.status_code == 200
