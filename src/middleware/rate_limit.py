"""Rate limiting middleware using Redis"""
import logging
import time
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


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

        # Skip rate limiting for health check
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host

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
