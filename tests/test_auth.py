"""Tests for Phase 21: Authentication (register, login, JWT, password hashing)"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.schemas import UserCreate, UserLogin, TokenResponse
from src.auth.service import AuthService
from src.config.settings import Settings


@pytest.fixture
def settings():
    return Settings(
        JWT_SECRET="test-secret-key-for-jwt-testing",
        JWT_ALGORITHM="HS256",
        JWT_EXPIRATION_MINUTES=60,
    )


@pytest.fixture
def auth_service(settings):
    return AuthService(settings)


# ── Password hashing ───────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_password_returns_bcrypt_hash(self):
        hashed = AuthService.hash_password("MyP@ssw0rd!")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = AuthService.hash_password("MyP@ssw0rd!")
        assert AuthService.verify_password("MyP@ssw0rd!", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = AuthService.hash_password("MyP@ssw0rd!")
        assert AuthService.verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = AuthService.hash_password("password123")
        h2 = AuthService.hash_password("password123")
        assert h1 != h2  # bcrypt salts differ


# ── JWT tokens ─────────────────────────────────────────────────────

class TestJWT:
    def test_create_access_token(self, auth_service):
        token, expires_in = auth_service.create_access_token(user_id=42, username="testuser")
        assert isinstance(token, str)
        assert len(token) > 20
        assert expires_in == 3600  # 60 minutes

    def test_decode_valid_token(self, auth_service):
        token, _ = auth_service.create_access_token(user_id=42, username="testuser")
        payload = auth_service.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["username"] == "testuser"

    def test_decode_invalid_token(self, auth_service):
        payload = auth_service.decode_token("invalid.token.here")
        assert payload is None

    def test_decode_expired_token(self):
        settings = Settings(
            JWT_SECRET="test-secret",
            JWT_ALGORITHM="HS256",
            JWT_EXPIRATION_MINUTES=0,  # Immediate expiry
        )
        service = AuthService(settings)
        from jose import jwt
        import time
        payload = {
            "sub": "1",
            "username": "test",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
            "iat": datetime.now(timezone.utc) - timedelta(seconds=20),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        result = service.decode_token(token)
        assert result is None

    def test_decode_wrong_secret(self, auth_service):
        token, _ = auth_service.create_access_token(user_id=1, username="test")
        other_service = AuthService(Settings(JWT_SECRET="different-secret"))
        payload = other_service.decode_token(token)
        assert payload is None

    def test_token_contains_iat(self, auth_service):
        token, _ = auth_service.create_access_token(user_id=1, username="test")
        payload = auth_service.decode_token(token)
        assert "iat" in payload

    def test_token_contains_exp(self, auth_service):
        token, _ = auth_service.create_access_token(user_id=1, username="test")
        payload = auth_service.decode_token(token)
        assert "exp" in payload


# ── User CRUD (with mocked DB) ────────────────────────────────────

class TestUserCRUD:
    @pytest.mark.asyncio
    async def test_register_user(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        # No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        user = await auth_service.register(db, "test@example.com", "testuser", "password123")

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password.startswith("$2b$")
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        existing = User(id=1, email="test@example.com", username="testuser", hashed_password="x")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already registered"):
            await auth_service.register(db, "test@example.com", "testuser", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        hashed = AuthService.hash_password("correct_password")
        user = User(id=1, email="t@t.com", username="testuser",
                     hashed_password=hashed, is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        result = await auth_service.authenticate(db, "testuser", "correct_password")
        assert result is not None
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        hashed = AuthService.hash_password("correct_password")
        user = User(id=1, email="t@t.com", username="testuser",
                     hashed_password=hashed, is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        result = await auth_service.authenticate(db, "testuser", "wrong")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        hashed = AuthService.hash_password("password")
        user = User(id=1, email="t@t.com", username="testuser",
                     hashed_password=hashed, is_active=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        result = await auth_service.authenticate(db, "testuser", "password")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await auth_service.authenticate(db, "nobody", "password")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, auth_service):
        db = AsyncMock(spec=AsyncSession)
        user = User(id=5, email="a@b.com", username="alice", hashed_password="x")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db.execute.return_value = mock_result

        result = await auth_service.get_user_by_id(db, 5)
        assert result.id == 5


# ── Pydantic schemas ──────────────────────────────────────────────

class TestSchemas:
    def test_user_create_valid(self):
        u = UserCreate(email="test@example.com", username="testuser", password="password123")
        assert u.email == "test@example.com"

    def test_user_create_invalid_email(self):
        with pytest.raises(Exception):
            UserCreate(email="not-an-email", username="testuser", password="password123")

    def test_user_create_short_username(self):
        with pytest.raises(Exception):
            UserCreate(email="a@b.com", username="ab", password="password123")

    def test_user_create_invalid_username_chars(self):
        with pytest.raises(Exception):
            UserCreate(email="a@b.com", username="test user!", password="password123")

    def test_user_create_short_password(self):
        with pytest.raises(Exception):
            UserCreate(email="a@b.com", username="testuser", password="short")

    def test_user_login_valid(self):
        u = UserLogin(username="testuser", password="password123")
        assert u.username == "testuser"

    def test_token_response(self):
        from src.auth.schemas import UserResponse
        user_resp = UserResponse(
            id=1, email="a@b.com", username="test",
            is_active=True, is_admin=False,
            created_at=datetime.now(timezone.utc),
        )
        t = TokenResponse(
            access_token="abc", token_type="bearer",
            expires_in=3600, user=user_resp,
        )
        assert t.access_token == "abc"
