"""
Redis Connection
"""
from typing import Optional
import redis.asyncio as redis

# Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    from app.core.config import settings
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        db=settings.REDIS_DB,
        decode_responses=True,
    )
    await redis_client.ping()


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.aclose()


def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client
