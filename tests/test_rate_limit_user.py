"""Tests for Phase 21: Per-user rate limiting"""
import pytest
from unittest.mock import MagicMock, patch
from jose import jwt as jose_jwt
from src.middleware.rate_limit import (
    _extract_rate_limit_key,
    EndpointRateLimiter,
    RateLimitMiddleware,
)
from fastapi import Request, HTTPException

TEST_SECRET = "test-jwt-secret"
TEST_ALGORITHM = "HS256"


def _make_token(claims: dict, secret: str = TEST_SECRET) -> str:
    return jose_jwt.encode(claims, secret, algorithm=TEST_ALGORITHM)


def _make_request(auth_header: str = None, client_host: str = "127.0.0.1"):
    """Build a mock Request object."""
    request = MagicMock(spec=Request)
    headers = {}
    if auth_header:
        headers["authorization"] = auth_header
    request.headers = headers
    request.client = MagicMock()
    request.client.host = client_host
    return request


@pytest.fixture(autouse=True)
def _patch_settings():
    """Patch module-level _settings so JWT validation uses our test secret."""
    with patch("src.middleware.rate_limit._settings") as mock_settings:
        mock_settings.JWT_SECRET = TEST_SECRET
        mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
        yield mock_settings


class TestExtractRateLimitKey:
    def test_no_auth_header(self):
        request = _make_request()
        assert _extract_rate_limit_key(request) is None

    def test_non_bearer_header(self):
        request = _make_request(auth_header="Basic abc123")
        assert _extract_rate_limit_key(request) is None

    def test_valid_jwt_returns_token_hash(self):
        token = _make_token({"sub": "42", "username": "alice"})
        request = _make_request(auth_header=f"Bearer {token}")
        result = _extract_rate_limit_key(request)
        assert result is not None
        assert result.startswith("tok:")
        assert len(result) == 20  # "tok:" + 16 hex chars

    def test_invalid_jwt_returns_none(self):
        """Invalid tokens must fall back to IP (return None)."""
        request = _make_request(auth_header="Bearer not.a.valid.jwt")
        result = _extract_rate_limit_key(request)
        assert result is None

    def test_wrong_secret_returns_none(self):
        """Token signed with wrong secret is rejected."""
        token = _make_token({"sub": "42"}, secret="wrong-secret")
        request = _make_request(auth_header=f"Bearer {token}")
        assert _extract_rate_limit_key(request) is None

    def test_same_token_same_key(self):
        token = _make_token({"sub": "42"})
        req1 = _make_request(auth_header=f"Bearer {token}")
        req2 = _make_request(auth_header=f"Bearer {token}")
        assert _extract_rate_limit_key(req1) == _extract_rate_limit_key(req2)

    def test_different_valid_tokens_different_keys(self):
        """Two valid tokens with different claims get different buckets."""
        token_a = _make_token({"sub": "1"})
        token_b = _make_token({"sub": "2"})
        req_a = _make_request(auth_header=f"Bearer {token_a}")
        req_b = _make_request(auth_header=f"Bearer {token_b}")
        assert _extract_rate_limit_key(req_a) != _extract_rate_limit_key(req_b)

    def test_forged_token_falls_back_to_ip(self):
        """Forged token (different secret, same sub) returns None, not a unique bucket."""
        token_forged = _make_token({"sub": "42"}, secret="forged-secret")
        req = _make_request(auth_header=f"Bearer {token_forged}")
        assert _extract_rate_limit_key(req) is None


class TestEndpointRateLimiterUserBased:
    @pytest.mark.asyncio
    async def test_rate_limit_by_user_id(self):
        """Authenticated users are rate-limited by token hash, not IP."""
        limiter = EndpointRateLimiter(calls=2, period=60)
        token = _make_token({"sub": "42"})
        request = _make_request(auth_header=f"Bearer {token}", client_host="192.168.1.1")

        await limiter(request)
        await limiter(request)

        with pytest.raises(HTTPException) as exc_info:
            await limiter(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_different_users_independent_limits(self):
        """Different users have independent rate limits."""
        limiter = EndpointRateLimiter(calls=1, period=60)

        token_a = _make_token({"sub": "1"})
        token_b = _make_token({"sub": "2"})

        req_a = _make_request(auth_header=f"Bearer {token_a}")
        req_b = _make_request(auth_header=f"Bearer {token_b}")

        await limiter(req_a)  # User 1: OK
        await limiter(req_b)  # User 2: OK (independent)

        with pytest.raises(HTTPException):
            await limiter(req_a)  # User 1: blocked

    @pytest.mark.asyncio
    async def test_unauthenticated_falls_back_to_ip(self):
        """Without JWT, falls back to IP-based limiting."""
        limiter = EndpointRateLimiter(calls=1, period=60)

        req = _make_request(client_host="10.0.0.1")
        await limiter(req)

        with pytest.raises(HTTPException):
            await limiter(req)

    @pytest.mark.asyncio
    async def test_invalid_token_falls_back_to_ip(self):
        """Invalid JWT falls back to IP-based limiting, not a per-token bucket."""
        limiter = EndpointRateLimiter(calls=1, period=60)

        # Two requests with different invalid tokens from same IP
        req1 = _make_request(auth_header="Bearer fake1", client_host="10.0.0.5")
        req2 = _make_request(auth_header="Bearer fake2", client_host="10.0.0.5")

        await limiter(req1)

        # Second request with different fake token should still be blocked (same IP bucket)
        with pytest.raises(HTTPException):
            await limiter(req2)
