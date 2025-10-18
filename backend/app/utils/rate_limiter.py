import time
from typing import Optional
import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE

    async def connect(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Rate limiter Redis connected")
        except Exception as e:
            logger.error(f"Failed to connect rate limiter Redis: {e}")
            self.redis_client = None

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()

    def _get_key(self, origin: str) -> str:
        current_minute = int(time.time() / 60)
        return f"ratelimit:{origin}:{current_minute}"

    async def is_allowed(self, origin: str, limit: Optional[int] = None) -> bool:
        if not self.redis_client:
            return True

        if limit is None:
            limit = self.rate_limit

        try:
            key = self._get_key(origin)
            current = await self.redis_client.incr(key)

            if current == 1:
                await self.redis_client.expire(key, 60)

            allowed = current <= limit

            if not allowed:
                logger.warning(f"Rate limit exceeded for {origin}: {current}/{limit}")

            return allowed

        except Exception as e:
            logger.error(f"Error checking rate limit for {origin}: {e}")
            return True

    async def get_remaining(self, origin: str, limit: Optional[int] = None) -> int:
        if not self.redis_client:
            return self.rate_limit

        if limit is None:
            limit = self.rate_limit

        try:
            key = self._get_key(origin)
            current = await self.redis_client.get(key)
            current_count = int(current) if current else 0

            return max(0, limit - current_count)

        except Exception as e:
            logger.error(f"Error getting remaining limit for {origin}: {e}")
            return limit


rate_limiter = RateLimiter()
