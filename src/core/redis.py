import redis.asyncio as redis

from src.core.config import config

redis_client = redis.from_url(  # type: ignore[no-untyped-call]
    config.REDIS_URL,
    decode_responses=True,
    encoding="utf-8",
)
