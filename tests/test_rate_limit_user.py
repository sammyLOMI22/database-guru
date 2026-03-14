"""Tests for Phase 21: Per-user rate limiting"""
import pytest
from unittest.mock import MagicMock, patch
from src.middleware.rate_limit import (
    _extract_rate_limit_key,
    EndpointRateLimiter,
    RateLimitMiddleware,
)
from fastapi import Request


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


class TestExtractRateLimitKey:
    def test_no_auth_header(self):
        request = _make_request()
        assert _extract_rate_limit_key(request) is None

    def test_non_bearer_header(self):
        request = _make_request(auth_header="Basic abc123")
        assert _extract_rate_limit_key(request) is None

    def test_valid_jwt_returns_token_hash(self):
        from jose import jwt
        token = jwt.encode({"sub": "42", "username": "alice"}, "secret", algorithm="HS256")
        request = _make_request(auth_header=f"Bearer {token}")
        result = _extract_rate_limit_key(request)
        assert result is not None
        assert result.startswith("tok:")
        assert len(result) == 20  # "tok:" + 16 hex chars

    def test_invalid_jwt_still_returns_key(self):
        """Even malformed tokens get their own bucket (not None)."""
        request = _make_request(auth_header="Bearer not.a.valid.jwt")
        result = _extract_rate_limit_key(request)
        assert result is not None
        assert result.startswith("tok:")

    def test_same_token_same_key(self):
        from jose import jwt
        token = jwt.encode({"sub": "42"}, "secret", algorithm="HS256")
        req1 = _make_request(auth_header=f"Bearer {token}")
        req2 = _make_request(auth_header=f"Bearer {token}")
        assert _extract_rate_limit_key(req1) == _extract_rate_limit_key(req2)

    def test_different_tokens_different_keys(self):
        """Forged token with same sub gets a different bucket."""
        from jose import jwt
        token_real = jwt.encode({"sub": "42"}, "real-secret", algorithm="HS256")
        token_forged = jwt.encode({"sub": "42"}, "forged-secret", algorithm="HS256")
        req_real = _make_request(auth_header=f"Bearer {token_real}")
        req_forged = _make_request(auth_header=f"Bearer {token_forged}")
        assert _extract_rate_limit_key(req_real) != _extract_rate_limit_key(req_forged)


class TestEndpointRateLimiterUserBased:
    @pytest.mark.asyncio
    async def test_rate_limit_by_user_id(self):
        """Authenticated users are rate-limited by user ID, not IP."""
        limiter = EndpointRateLimiter(calls=2, period=60)
        from jose import jwt
        token = jwt.encode({"sub": "42"}, "secret", algorithm="HS256")

        request = _make_request(auth_header=f"Bearer {token}", client_host="192.168.1.1")

        # First 2 calls should pass
        await limiter(request)
        await limiter(request)

        # 3rd should fail
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await limiter(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_different_users_independent_limits(self):
        """Different users have independent rate limits."""
        limiter = EndpointRateLimiter(calls=1, period=60)
        from jose import jwt

        token_a = jwt.encode({"sub": "1"}, "secret", algorithm="HS256")
        token_b = jwt.encode({"sub": "2"}, "secret", algorithm="HS256")

        req_a = _make_request(auth_header=f"Bearer {token_a}")
        req_b = _make_request(auth_header=f"Bearer {token_b}")

        await limiter(req_a)  # User 1: OK
        await limiter(req_b)  # User 2: OK (independent)

        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await limiter(req_a)  # User 1: blocked

    @pytest.mark.asyncio
    async def test_unauthenticated_falls_back_to_ip(self):
        """Without JWT, falls back to IP-based limiting."""
        limiter = EndpointRateLimiter(calls=1, period=60)

        req = _make_request(client_host="10.0.0.1")
        await limiter(req)

        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await limiter(req)
