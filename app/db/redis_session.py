import redis.asyncio as redis
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.core.config import settings

redis_pool = None

def setup_redis_pool():
    """Initializes the Redis connection pool."""
    global redis_pool
    if redis_pool is None:
        print(f"--- Initializing Redis connection pool for URL: {settings.REDIS_URL} ---")
        
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True 
        )
    return redis_pool

def get_redis_pool():
    """Returns the existing Redis connection pool."""
    if redis_pool is None:
        return setup_redis_pool()
    return redis_pool

async def close_redis_pool():
    """Closes the Redis connection pool."""
    global redis_pool
    if redis_pool:
        print("--- Closing Redis connection pool ---")
        await redis_pool.disconnect()
        redis_pool = None

async def get_redis_client() -> redis.Redis:
    """Dependency/getter for obtaining a Redis client from the pool."""
    pool = get_redis_pool()
    return redis.Redis(connection_pool=pool)

@asynccontextmanager
async def redis_context() -> AsyncGenerator[redis.Redis, None]:
    client: redis.Redis | None = None
    try:
        client = await get_redis_client()
        yield client
    finally:
        pass