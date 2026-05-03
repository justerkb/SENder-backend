"""API throttling and rate limiting middleware using SlowAPI + Redis.

Rules:
  - 60 requests per minute per IP  (all endpoints)
  - 500 requests per hour per IP   (all endpoints)
  - 50 *write* requests per hour per IP  (POST/PUT/PATCH/DELETE only)
  - GET (read) requests are NOT subject to the write limit

The limits are stored in Redis so they are shared across workers.
"""

import logging
import time as _time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import get_settings

logger = logging.getLogger("packagego.ratelimit")


# ---------------------------------------------------------------------------
# SlowAPI Limiter – created lazily
# ---------------------------------------------------------------------------

_limiter = None


def get_limiter() -> Limiter:
    global _limiter
    if _limiter is None:
        settings = get_settings()
        _limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=settings.redis_url,
            default_limits=[
                f"{settings.rate_limit_per_minute}/minute",
                f"{settings.rate_limit_per_hour}/hour",
            ],
        )
    return _limiter


# Expose as module-level for main.py
limiter = property(lambda self: get_limiter())


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Return 429 with Retry-After header on rate limit exceeded."""
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


# ---------------------------------------------------------------------------
# Write-method rate limiter (custom middleware)
# ---------------------------------------------------------------------------

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class WriteRateLimitMiddleware(BaseHTTPMiddleware):
    """Separate per-IP rate limit for write (mutating) HTTP methods.

    Uses a simple Redis-based sliding-window counter.  The key pattern is:
        ``write_rl:<ip>:<hour_bucket>``
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method not in _WRITE_METHODS:
            return await call_next(request)

        settings = get_settings()
        ip = get_remote_address(request)
        hour_bucket = int(_time.time()) // 3600  # changes every hour
        key = f"write_rl:{ip}:{hour_bucket}"

        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, 3600)
            await r.aclose()

            if current > settings.rate_limit_write_per_hour:
                logger.warning("Write rate limit exceeded for IP %s", ip)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            f"Write rate limit exceeded: "
                            f"{settings.rate_limit_write_per_hour}/hour for write requests"
                        ),
                        "retry_after_seconds": 3600 - (int(_time.time()) % 3600),
                    },
                    headers={
                        "Retry-After": str(3600 - (int(_time.time()) % 3600))
                    },
                )
        except Exception as exc:
            logger.debug("Write rate-limit check failed (allowing): %s", exc)

        return await call_next(request)
