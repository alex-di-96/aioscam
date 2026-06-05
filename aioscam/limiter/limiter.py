"""
Rate Limiter for Max API
"""

import asyncio
import logging
import time
from typing import Callable, Awaitable, TypeVar, Any

from aioscam.limiter.config import RateLimitConfig
from aioscam.exceptions import RetryAfter

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """
    Token bucket rate limiter with 429 retry support

    All requests pass through a single async queue.
    The limiter enforces:
      - Token bucket: max `rate` requests/second, burst up to `burst`
      - 429 retry: on rate limit response, wait `retry_after` + exponential backoff
      - Max retries: give up after `max_retries` attempts

    Usage:
        limiter = RateLimiter(RateLimitConfig(rate=10, burst=20))
        await limiter.start()

        result = await limiter.execute(lambda: client.request(...))

        await limiter.stop()
    """

    def __init__(self, config: RateLimitConfig = RateLimitConfig()):
        self.config = config
        self._tokens = float(config.burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the rate limiter"""
        if self._running:
            return
        self._running = True
        logger.info(
            f"RateLimiter started: rate={self.config.rate}/s, "
            f"burst={self.config.burst}, retry_429={self.config.retry_429}"
        )

    async def stop(self) -> None:
        """Stop the rate limiter"""
        self._running = False
        logger.info("RateLimiter stopped")

    async def acquire(self) -> None:
        """
        Acquire a token from the bucket.
        Blocks until a token is available.
        """
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                # Refill tokens based on elapsed time
                self._tokens = min(
                    self.config.burst,
                    self._tokens + elapsed * self.config.rate,
                )
                self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # Calculate how long to wait for the next token to be available
                wait_time = (1.0 - self._tokens) / self.config.rate

            await asyncio.sleep(wait_time)

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a callable through the rate limiter with automatic 429 retry.

        Args:
            func: Async callable (e.g. lambda: client.request(...))
            *args, **kwargs: Passed to func

        Returns:
            Result of func

        Raises:
            RetryAfter: If max retries exceeded on 429
        """
        retries = 0
        backoff = self.config.backoff_base

        while True:
            await self.acquire()

            try:
                return await func(*args, **kwargs)
            except RetryAfter as e:
                if not self.config.retry_429 or retries >= self.config.max_retries:
                    logger.error(
                        f"RateLimiter: max retries ({self.config.max_retries}) "
                        f"exceeded on 429, giving up"
                    )
                    raise

                retries += 1
                # Use retry_after from API if available, otherwise exponential backoff
                delay = getattr(e, "retry_after", None) or backoff
                # Cap the delay
                delay = min(delay, self.config.backoff_max)

                logger.warning(
                    f"RateLimiter: 429 received, retry {retries}/{self.config.max_retries}, "
                    f"waiting {delay:.1f}s"
                )
                await asyncio.sleep(delay)

                # Exponential backoff for subsequent retries
                backoff = min(backoff * 2, self.config.backoff_max)

    @property
    def available_tokens(self) -> float:
        """Current available tokens (approximate)"""
        return self._tokens
