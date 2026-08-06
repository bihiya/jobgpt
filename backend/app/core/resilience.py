"""Retry + circuit breaker for outbound calls (portals, HTTP, etc.)."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(AppException):
    def __init__(self, name: str) -> None:
        super().__init__(
            message=f"Circuit open for {name}",
            code="CIRCUIT_OPEN",
            status_code=503,
        )


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = 0.0

    def _can_pass(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.opened_at >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # half-open allows probe

    def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            logger.warning("circuit_opened", name=self.name)

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        if not self._can_pass():
            raise CircuitOpenError(self.name)
        try:
            result = await fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 8.0,
) -> T:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=min_wait, max=max_wait),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    ):
        with attempt:
            return await fn()
    raise RuntimeError("unreachable")
