import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.failure_threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.timeout = settings.CIRCUIT_BREAKER_TIMEOUT
        self.recovery_timeout = settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT

    async def connect(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Circuit breaker Redis connected")
        except Exception as e:
            logger.error(f"Failed to connect circuit breaker Redis: {e}")
            self.redis_client = None

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()

    def _get_state_key(self, service_name: str) -> str:
        return f"circuit:{service_name}:state"

    def _get_failure_key(self, service_name: str) -> str:
        return f"circuit:{service_name}:failures"

    def _get_last_failure_key(self, service_name: str) -> str:
        return f"circuit:{service_name}:last_failure"

    async def get_state(self, service_name: str) -> CircuitState:
        if not self.redis_client:
            return CircuitState.CLOSED

        try:
            state = await self.redis_client.get(self._get_state_key(service_name))
            if state:
                return CircuitState(state)

            last_failure_time = await self.redis_client.get(self._get_last_failure_key(service_name))
            if last_failure_time:
                last_failure = float(last_failure_time)
                if time.time() - last_failure > self.recovery_timeout:
                    await self._set_state(service_name, CircuitState.HALF_OPEN)
                    return CircuitState.HALF_OPEN

            return CircuitState.CLOSED
        except Exception as e:
            logger.error(f"Error getting circuit state for {service_name}: {e}")
            return CircuitState.CLOSED

    async def _set_state(self, service_name: str, state: CircuitState):
        if not self.redis_client:
            return

        try:
            await self.redis_client.set(
                self._get_state_key(service_name),
                state.value,
                ex=self.timeout
            )
        except Exception as e:
            logger.error(f"Error setting circuit state for {service_name}: {e}")

    async def is_available(self, service_name: str) -> bool:
        state = await self.get_state(service_name)
        return state != CircuitState.OPEN

    async def record_success(self, service_name: str):
        if not self.redis_client:
            return

        try:
            await self.redis_client.delete(self._get_failure_key(service_name))
            await self.redis_client.delete(self._get_last_failure_key(service_name))
            await self._set_state(service_name, CircuitState.CLOSED)
            logger.info(f"Circuit breaker for {service_name} reset to CLOSED")
        except Exception as e:
            logger.error(f"Error recording success for {service_name}: {e}")

    async def record_failure(self, service_name: str):
        if not self.redis_client:
            return

        try:
            failure_key = self._get_failure_key(service_name)
            failures = await self.redis_client.incr(failure_key)
            await self.redis_client.expire(failure_key, self.timeout)

            await self.redis_client.set(
                self._get_last_failure_key(service_name),
                time.time(),
                ex=self.timeout
            )

            if failures >= self.failure_threshold:
                await self._set_state(service_name, CircuitState.OPEN)
                logger.warning(f"Circuit breaker OPENED for {service_name} after {failures} failures")
            else:
                logger.info(f"Circuit breaker recorded failure {failures}/{self.failure_threshold} for {service_name}")

        except Exception as e:
            logger.error(f"Error recording failure for {service_name}: {e}")

    async def get_failure_count(self, service_name: str) -> int:
        if not self.redis_client:
            return 0

        try:
            count = await self.redis_client.get(self._get_failure_key(service_name))
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting failure count for {service_name}: {e}")
            return 0


circuit_breaker = CircuitBreaker()
