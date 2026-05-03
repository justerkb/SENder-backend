"""Redis-based token blocklist for logout / token revocation."""

import redis.asyncio as redis

from config import get_settings

settings = get_settings()

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url, decode_responses=True
        )
    return _redis_client


async def add_to_blocklist(jti: str, expires_in_seconds: int) -> None:
    """Block a token by storing its JTI in Redis with an expiry."""
    r = await get_redis()
    await r.setex(f"blocklist:{jti}", expires_in_seconds, "blocked")


async def is_blocked(jti: str) -> bool:
    """Check if a token JTI is in the blocklist."""
    r = await get_redis()
    return await r.exists(f"blocklist:{jti}") > 0


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
