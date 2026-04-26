"""Tests for the self-service password change endpoint (Phase 24.7 follow-up).

Covers the post-reset forced-change flow: admin reset flips
``must_change_password``, the user logs in, hits ``/api/auth/change-password``,
and the flag is cleared.
"""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.dependencies import get_db
from src.api.endpoints.auth import router as auth_router
from src.auth.audit import AuditLog
from src.auth.dependencies import get_auth_service, get_current_active_user
from src.auth.models import User
from src.auth.service import AuthService
from src.config.settings import Settings
from src.database.connection import Base
from src.middleware.rate_limit import auth_rate_limiter


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def reset_user(session_factory):
    """A user whose password was just reset by an operator."""
    auth_service = AuthService(Settings(JWT_SECRET="test", JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60))
    async with session_factory() as db:
        user = User(
            email="alice@example.com",
            username="alice",
            hashed_password=auth_service.hash_password("TempPass12345"),
            is_active=True,
            must_change_password=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest.fixture
def app_factory(session_factory):
    auth_service = AuthService(Settings(JWT_SECRET="test", JWT_ALGORITHM="HS256", JWT_EXPIRATION_MINUTES=60))

    def build(current_user: User) -> FastAPI:
        app = FastAPI()
        app.include_router(auth_router, prefix="/api")

        async def override_db():
            async with session_factory() as db:
                yield db

        # Reload the seeded user inside the request session so the User
        # instance stays attached when the endpoint mutates it. Without this
        # the fixture-created user is detached and refresh() fails.
        from fastapi import Depends as _Depends

        async def reload_user(db: AsyncSession = _Depends(get_db)) -> User:
            row = await db.execute(select(User).where(User.id == current_user.id))
            return row.scalar_one()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_auth_service] = lambda: auth_service
        app.dependency_overrides[get_current_active_user] = reload_user
        # Skip rate limiting in unit tests.
        app.dependency_overrides[auth_rate_limiter] = lambda: None
        return app

    return build


async def _last_audit_action(session_factory) -> str | None:
    async with session_factory() as db:
        rows = await db.execute(select(AuditLog.action).order_by(AuditLog.id.desc()))
        return rows.scalars().first()


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_clears_must_change_flag_on_success(self, app_factory, reset_user, session_factory):
        client = TestClient(app_factory(reset_user))
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "TempPass12345", "new_password": "NewStrongPass99"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["must_change_password"] is False

        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == reset_user.id))
            updated = row.scalar_one()
        assert updated.must_change_password is False
        assert AuthService.verify_password("NewStrongPass99", updated.hashed_password)

        assert await _last_audit_action(session_factory) == "password_change"

    @pytest.mark.asyncio
    async def test_rejects_wrong_current_password(self, app_factory, reset_user, session_factory):
        client = TestClient(app_factory(reset_user))
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "WrongPass1234", "new_password": "NewStrongPass99"},
        )
        assert resp.status_code == 401

        # Flag must remain set so the forced-change UI keeps blocking the user.
        async with session_factory() as db:
            row = await db.execute(select(User).where(User.id == reset_user.id))
            updated = row.scalar_one()
        assert updated.must_change_password is True

        assert await _last_audit_action(session_factory) == "password_change_failed"

    @pytest.mark.asyncio
    async def test_rejects_reusing_same_password(self, app_factory, reset_user):
        client = TestClient(app_factory(reset_user))
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "TempPass12345", "new_password": "TempPass12345"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_weak_new_password(self, app_factory, reset_user):
        client = TestClient(app_factory(reset_user))
        # Pydantic complexity validation kicks in before the endpoint logic.
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "TempPass12345", "new_password": "alllowercase1"},
        )
        assert resp.status_code == 422
