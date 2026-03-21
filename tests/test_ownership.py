"""Tests for Phase 21: Resource ownership and access control"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.dependencies import get_optional_user, get_current_user, require_admin
from src.auth.service import AuthService
from src.api.endpoints.chat import _check_session_ownership
from src.database.models import ChatSession, DatabaseConnection
from src.config.settings import Settings


# ── Ownership check helper ─────────────────────────────────────────

class TestSessionOwnershipCheck:
    def test_no_user_unowned_session(self):
        """Unauthenticated users can access unowned (legacy/guest) sessions."""
        session = MagicMock(spec=ChatSession)
        session.owner_id = None
        _check_session_ownership(session, None)  # Should not raise

    def test_no_user_owned_session_raises_403(self):
        """Unauthenticated users cannot access owned sessions."""
        session = MagicMock(spec=ChatSession)
        session.owner_id = 42
        with pytest.raises(HTTPException) as exc_info:
            _check_session_ownership(session, None)
        assert exc_info.value.status_code == 403

    def test_owner_matches(self):
        """Owner accessing own session — allowed."""
        session = MagicMock(spec=ChatSession)
        session.owner_id = 42
        user = MagicMock(spec=User)
        user.id = 42
        _check_session_ownership(session, user)  # Should not raise

    def test_owner_mismatch_raises_403(self):
        """Different user accessing owned session — blocked."""
        session = MagicMock(spec=ChatSession)
        session.owner_id = 42
        user = MagicMock(spec=User)
        user.id = 99
        with pytest.raises(HTTPException) as exc_info:
            _check_session_ownership(session, user)
        assert exc_info.value.status_code == 403

    def test_unowned_session_accessible(self):
        """Session with no owner — accessible to all."""
        session = MagicMock(spec=ChatSession)
        session.owner_id = None
        user = MagicMock(spec=User)
        user.id = 99
        _check_session_ownership(session, user)  # Should not raise


# ── get_optional_user dependency ──────────────────────────────────

class TestOptionalUser:
    @pytest.mark.asyncio
    async def test_no_token_require_auth_false(self):
        """Without token and REQUIRE_AUTH=False, returns None."""
        settings = Settings(REQUIRE_AUTH=False, JWT_SECRET="test")

        with patch("src.auth.dependencies.get_settings", return_value=settings):
            result = await get_optional_user(
                token=None,
                db=AsyncMock(spec=AsyncSession),
                settings=settings,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_token_require_auth_true(self):
        """Without token and REQUIRE_AUTH=True, raises 401."""
        settings = Settings(REQUIRE_AUTH=True, JWT_SECRET="test")

        with pytest.raises(HTTPException) as exc_info:
            await get_optional_user(
                token=None,
                db=AsyncMock(spec=AsyncSession),
                settings=settings,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_require_auth_false(self):
        """Invalid token with REQUIRE_AUTH=False returns None."""
        settings = Settings(REQUIRE_AUTH=False, JWT_SECRET="test")

        result = await get_optional_user(
            token="invalid.jwt.token",
            db=AsyncMock(spec=AsyncSession),
            settings=settings,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_require_auth_true(self):
        """Invalid token with REQUIRE_AUTH=True raises 401."""
        settings = Settings(REQUIRE_AUTH=True, JWT_SECRET="test")

        with pytest.raises(HTTPException) as exc_info:
            await get_optional_user(
                token="invalid.jwt.token",
                db=AsyncMock(spec=AsyncSession),
                settings=settings,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """Valid token returns the user."""
        settings = Settings(REQUIRE_AUTH=False, JWT_SECRET="test-secret-123")

        from src.auth.service import AuthService
        service = AuthService(settings)
        token, _ = service.create_access_token(user_id=5, username="alice")

        user = User(id=5, email="a@b.com", username="alice",
                     hashed_password="x", is_active=True)
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        result = await get_optional_user(token=token, db=db, settings=settings)
        assert result is not None
        assert result.id == 5

    @pytest.mark.asyncio
    async def test_valid_token_inactive_user_returns_none(self):
        """Valid token for inactive user returns None."""
        settings = Settings(REQUIRE_AUTH=False, JWT_SECRET="test-secret-123")

        from src.auth.service import AuthService
        service = AuthService(settings)
        token, _ = service.create_access_token(user_id=5, username="alice")

        user = User(id=5, email="a@b.com", username="alice",
                     hashed_password="x", is_active=False)
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        result = await get_optional_user(token=token, db=db, settings=settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_inactive_user_require_auth_true_raises_401(self):
        """Inactive user with REQUIRE_AUTH=True raises 401, not None."""
        settings = Settings(REQUIRE_AUTH=True, JWT_SECRET="test-secret-123")

        from src.auth.service import AuthService
        service = AuthService(settings)
        token, _ = service.create_access_token(user_id=5, username="alice")

        user = User(id=5, email="a@b.com", username="alice",
                     hashed_password="x", is_active=False)
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_optional_user(token=token, db=db, settings=settings)
        assert exc_info.value.status_code == 401
        assert "deactivated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_user_require_auth_true_raises_401(self):
        """Deleted user with REQUIRE_AUTH=True raises 401, not None."""
        settings = Settings(REQUIRE_AUTH=True, JWT_SECRET="test-secret-123")

        from src.auth.service import AuthService
        service = AuthService(settings)
        token, _ = service.create_access_token(user_id=999, username="ghost")

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_optional_user(token=token, db=db, settings=settings)
        assert exc_info.value.status_code == 401
        assert "not found" in exc_info.value.detail


# ── get_current_user dependency ───────────────────────────────────

class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                token=None,
                db=AsyncMock(spec=AsyncSession),
                auth_service=MagicMock(),
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        service = MagicMock()
        service.decode_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                token="bad.token",
                db=AsyncMock(spec=AsyncSession),
                auth_service=service,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self):
        service = MagicMock()
        service.decode_token.return_value = {"sub": "999"}
        service.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                token="valid.token",
                db=AsyncMock(spec=AsyncSession),
                auth_service=service,
            )
        assert exc_info.value.status_code == 401


# ── require_admin dependency ──────────────────────────────────────

class TestRequireAdmin:
    @pytest.mark.asyncio
    async def test_admin_user_passes(self):
        user = MagicMock(spec=User)
        user.is_admin = True
        result = await require_admin(user=user)
        assert result == user

    @pytest.mark.asyncio
    async def test_non_admin_raises_403(self):
        user = MagicMock(spec=User)
        user.is_admin = False
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=user)
        assert exc_info.value.status_code == 403


# ── int(user_id) ValueError paths ────────────────────────────────

class TestMalformedSubClaim:
    @pytest.mark.asyncio
    async def test_get_current_user_non_integer_sub_raises_401(self):
        """Malformed sub claim (non-integer) returns 401, not 500."""
        service = MagicMock()
        service.decode_token.return_value = {"sub": "not_a_number"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                token="valid.token",
                db=AsyncMock(spec=AsyncSession),
                auth_service=service,
            )
        assert exc_info.value.status_code == 401
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_optional_user_non_integer_sub_require_auth_true(self):
        """Malformed sub with REQUIRE_AUTH=True raises 401."""
        settings = Settings(REQUIRE_AUTH=True, JWT_SECRET="test-secret-123")
        service = AuthService(settings)
        # Craft a token with non-integer sub
        from jose import jwt as jose_jwt
        token = jose_jwt.encode(
            {"sub": "abc", "exp": 9999999999},
            "test-secret-123", algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_optional_user(
                token=token,
                db=AsyncMock(spec=AsyncSession),
                settings=settings,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_optional_user_non_integer_sub_require_auth_false(self):
        """Malformed sub with REQUIRE_AUTH=False returns None."""
        settings = Settings(REQUIRE_AUTH=False, JWT_SECRET="test-secret-123")
        from jose import jwt as jose_jwt
        token = jose_jwt.encode(
            {"sub": "abc", "exp": 9999999999},
            "test-secret-123", algorithm="HS256",
        )

        result = await get_optional_user(
            token=token,
            db=AsyncMock(spec=AsyncSession),
            settings=settings,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub_raises_401(self):
        """Token with no sub claim returns 401."""
        service = MagicMock()
        service.decode_token.return_value = {"username": "test"}  # no "sub"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                token="valid.token",
                db=AsyncMock(spec=AsyncSession),
                auth_service=service,
            )
        assert exc_info.value.status_code == 401


# ── Connection ownership in list ──────────────────────────────────

class TestConnectionOwnership:
    def test_connection_model_has_owner_id(self):
        """DatabaseConnection model has owner_id column."""
        conn = DatabaseConnection(name="test", database_type="sqlite")
        assert hasattr(conn, 'owner_id')

    def test_chat_session_model_has_owner_id(self):
        """ChatSession model has owner_id column."""
        session = ChatSession(name="test")
        assert hasattr(session, 'owner_id')


# ── activate_connection ownership enforcement ─────────────────────

class TestActivateConnectionOwnership:
    @pytest.mark.asyncio
    async def test_activate_other_users_connection_raises_403(self):
        """User cannot activate a connection owned by another user."""
        from src.api.endpoints.connections import activate_connection

        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.owner_id = 42
        conn.is_deleted = False

        user = MagicMock(spec=User)
        user.id = 99

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await activate_connection(
                connection_id=1, db=db, current_user=user,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_activate_own_connection_succeeds(self):
        """User can activate their own connection."""
        from src.api.endpoints.connections import activate_connection
        from datetime import datetime, timezone

        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.name = "my-db"
        conn.database_type = "postgresql"
        conn.host = "localhost"
        conn.port = 5432
        conn.database_name = "testdb"
        conn.owner_id = 42
        conn.is_deleted = False
        conn.is_active = True
        conn.last_tested_at = None
        conn.created_at = datetime.now(timezone.utc)

        user = MagicMock(spec=User)
        user.id = 42

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = mock_result

        result = await activate_connection(
            connection_id=1, db=db, current_user=user,
        )
        assert result.id == 1
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_unowned_connection_succeeds(self):
        """User can activate an unowned connection."""
        from src.api.endpoints.connections import activate_connection
        from datetime import datetime, timezone

        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.name = "shared-db"
        conn.database_type = "sqlite"
        conn.host = None
        conn.port = None
        conn.database_name = "test.db"
        conn.owner_id = None
        conn.is_deleted = False
        conn.is_active = True
        conn.last_tested_at = None
        conn.created_at = datetime.now(timezone.utc)

        user = MagicMock(spec=User)
        user.id = 99

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = mock_result

        result = await activate_connection(
            connection_id=1, db=db, current_user=user,
        )
        assert result.id == 1


# ── delete_connection ownership enforcement ───────────────────────

class TestDeleteConnectionOwnership:
    @pytest.mark.asyncio
    async def test_delete_other_users_connection_raises_403(self):
        """User cannot delete a connection owned by another user."""
        from src.api.endpoints.connections import delete_connection

        conn = MagicMock(spec=DatabaseConnection)
        conn.id = 1
        conn.name = "other-db"
        conn.owner_id = 42
        conn.is_deleted = False

        user = MagicMock(spec=User)
        user.id = 99

        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = mock_result

        request = MagicMock()
        request.client.host = "127.0.0.1"

        with pytest.raises(HTTPException) as exc_info:
            await delete_connection(
                request=request, connection_id=1,
                db=db, current_user=user,
            )
        assert exc_info.value.status_code == 403
