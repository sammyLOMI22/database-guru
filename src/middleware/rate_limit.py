"""Rate limiting middleware and dependencies"""
import logging
import time
from typing import Callable, Dict, Optional
from fastapi import Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import Settings

logger = logging.getLogger(__name__)

_settings = Settings()


def _extract_rate_limit_key(request: Request) -> Optional[str]:
    """Derive a rate-limit key from a *validated* Bearer token.

    Only uses the token hash as bucket key after verifying the JWT
    signature.  Invalid or expired tokens fall back to IP-based
    bucketing so that attackers cannot bypass rate limits by rotating
    random Bearer values.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if not token:
        return None
    # Validate JWT and extract stable user identity
    try:
        payload = jwt.decode(
            token,
            _settings.JWT_SECRET,
            algorithms=[_settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None
    # Key by the stable user ID from the token, not the token itself
    sub = payload.get("sub")
    if not sub:
        return None
    return f"user:{sub}"


# ============================================================================
# Endpoint-Specific Rate Limiter (for expensive LLM operations)
# ============================================================================

class EndpointRateLimiter:
    """
    Stricter rate limiter for computationally expensive endpoints.

    Use as a FastAPI dependency to add per-endpoint rate limits that are
    stricter than the global middleware limit.

    Example:
        llm_limiter = EndpointRateLimiter(calls=10, period=60)

        @router.post("/ask")
        async def ask(request: Request, _: None = Depends(llm_limiter)):
            ...
    """

    def __init__(self, calls: int = 10, period: int = 60):
        """
        Initialize endpoint rate limiter.

        Args:
            calls: Maximum calls allowed per period
            period: Time window in seconds
        """
        self.calls = calls
        self.period = period
        self._clients: Dict[str, Dict] = {}

    def _cleanup_old_entries(self, now: float) -> None:
        """Remove expired client entries to prevent memory growth."""
        expired = [
            client_id for client_id, data in self._clients.items()
            if not data["calls"] or max(data["calls"]) < now - self.period * 2
        ]
        for client_id in expired:
            del self._clients[client_id]

    async def __call__(self, request: Request) -> None:
        """Check rate limit for the request."""
        client_ip = _extract_rate_limit_key(request) or (request.client.host if request.client else "unknown")
        now = time.time()

        # Periodic cleanup (every 100 requests approximately)
        if len(self._clients) > 100:
            self._cleanup_old_entries(now)

        # Initialize client record
        if client_ip not in self._clients:
            self._clients[client_ip] = {"calls": [], "blocked_until": 0}

        client_data = self._clients[client_ip]

        # Check if blocked
        if client_data["blocked_until"] > now:
            retry_after = int(client_data["blocked_until"] - now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for this endpoint. "
                       f"Maximum {self.calls} requests per {self.period} seconds. "
                       f"Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # Clean old calls
        client_data["calls"] = [
            t for t in client_data["calls"] if t > now - self.period
        ]

        # Check limit
        if len(client_data["calls"]) >= self.calls:
            oldest = min(client_data["calls"])
            client_data["blocked_until"] = oldest + self.period
            retry_after = int(client_data["blocked_until"] - now)

            logger.warning(
                f"Endpoint rate limit exceeded for {client_ip}: "
                f"{self.calls}/{self.period}s"
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for this endpoint. "
                       f"Maximum {self.calls} requests per {self.period} seconds. "
                       f"Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # Record this call
        client_data["calls"].append(now)


# Pre-configured limiters for different endpoint types
llm_rate_limiter = EndpointRateLimiter(calls=20, period=60)  # 20 LLM calls/min


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware using in-memory storage

    For production, this should use Redis for distributed rate limiting
    """

    def __init__(self, app, calls: int = 100, period: int = 60):
        """
        Initialize rate limiter

        Args:
            app: FastAPI application
            calls: Number of calls allowed
            period: Time period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}  # In production, use Redis

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""

        # Skip rate limiting for health/monitoring endpoints
        exempt_paths = [
            "/health", "/", "/docs", "/openapi.json",
            # Pool monitoring endpoints (internal health checks, polled frequently)
            "/api/pools/stats", "/api/pools/health",
            # Model listing (needed on every page load)
            "/api/models/", "/api/models/details",
            # Settings (loaded on app init)
            "/api/settings/",
        ]
        if request.url.path in exempt_paths or request.url.path.rstrip('/') in exempt_paths:
            return await call_next(request)

        # Get client identifier (prefer user ID from JWT, fall back to IP)
        client_ip = _extract_rate_limit_key(request) or request.client.host

        # Get current time
        now = time.time()

        # Initialize client record if not exists
        if client_ip not in self.clients:
            self.clients[client_ip] = {"calls": [], "blocked_until": 0}

        client_data = self.clients[client_ip]

        # Check if client is blocked
        if client_data["blocked_until"] > now:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Please try again later.",
                    "retry_after": int(client_data["blocked_until"] - now),
                },
            )

        # Clean up old calls outside the time window
        client_data["calls"] = [
            call_time for call_time in client_data["calls"]
            if call_time > now - self.period
        ]

        # Check if rate limit exceeded
        if len(client_data["calls"]) >= self.calls:
            # Block client for the remaining period
            oldest_call = min(client_data["calls"])
            client_data["blocked_until"] = oldest_call + self.period

            logger.warning(f"Rate limit exceeded for {client_ip}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.calls} requests per {self.period} seconds allowed",
                    "retry_after": self.period,
                },
            )

        # Add current call
        client_data["calls"].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.calls - len(client_data["calls"])
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))

        return response


class RedisRateLimiter:
    """
    Redis-based rate limiter (for production use)

    This would be used in production for distributed rate limiting
    """

    def __init__(self, redis_client, calls: int = 100, period: int = 60):
        """
        Initialize Redis rate limiter

        Args:
            redis_client: Redis client instance
            calls: Number of calls allowed
            period: Time period in seconds
        """
        self.redis = redis_client
        self.calls = calls
        self.period = period

    async def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed

        Args:
            client_id: Client identifier

        Returns:
            (is_allowed, remaining_calls)
        """
        key = f"ratelimit:{client_id}"
        now = time.time()

        # Use Redis sorted set to track requests
        # Remove old requests
        await self.redis.redis.zremrangebyscore(key, 0, now - self.period)

        # Count requests in current window
        count = await self.redis.redis.zcard(key)

        if count >= self.calls:
            return False, 0

        # Add current request
        await self.redis.redis.zadd(key, {str(now): now})
        await self.redis.redis.expire(key, self.period)

        remaining = self.calls - count - 1
        return True, remaining
