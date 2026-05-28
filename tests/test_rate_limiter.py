"""
Tests for RateLimiter
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioscam.limiter import RateLimiter, RateLimitConfig
from aioscam.exceptions import RetryAfter


# ============================================================
# RateLimitConfig tests
# ============================================================

class TestRateLimitConfig:
    def test_default_config(self):
        cfg = RateLimitConfig()
        assert cfg.rate == 10.0
        assert cfg.burst == 20
        assert cfg.max_retries == 3
        assert cfg.backoff_base == 1.0
        assert cfg.backoff_max == 60.0
        assert cfg.retry_429 is True

    def test_strict_config(self):
        cfg = RateLimitConfig.strict()
        assert cfg.rate == 5.0
        assert cfg.burst == 10
        assert cfg.max_retries == 5

    def test_relaxed_config(self):
        cfg = RateLimitConfig.relaxed()
        assert cfg.rate == 30.0
        assert cfg.burst == 50
        assert cfg.max_retries == 1


# ============================================================
# RateLimiter token bucket tests
# ============================================================

class TestRateLimiterTokenBucket:
    @pytest.mark.asyncio
    async def test_acquire_with_tokens_available(self):
        """Should acquire token immediately when bucket is full"""
        limiter = RateLimiter(RateLimitConfig(rate=10, burst=10))
        await limiter.start()
        try:
            start = time.monotonic()
            await limiter.acquire()
            elapsed = time.monotonic() - start
            assert elapsed < 0.1  # Should be nearly instant
        finally:
            await limiter.stop()

    @pytest.mark.asyncio
    async def test_acquire_waits_when_no_tokens(self):
        """Should wait for token refill when bucket is empty"""
        # 2 tokens, burst=2, rate=100/sec
        limiter = RateLimiter(RateLimitConfig(rate=100, burst=2))
        await limiter.start()
        try:
            # Consume both tokens
            await limiter.acquire()
            await limiter.acquire()

            # Third should wait for refill
            start = time.monotonic()
            await limiter.acquire()
            elapsed = time.monotonic() - start
            # At 100/sec, should get a token in ~0.01s
            assert elapsed < 0.5
        finally:
            await limiter.stop()

    @pytest.mark.asyncio
    async def test_burst_limit(self):
        """Should not allow more than burst tokens at once"""
        limiter = RateLimiter(RateLimitConfig(rate=1, burst=3))
        await limiter.start()
        try:
            # Should consume 3 tokens quickly
            start = time.monotonic()
            await limiter.acquire()
            await limiter.acquire()
            await limiter.acquire()
            burst_time = time.monotonic() - start

            # 4th should wait (bucket empty)
            await limiter.acquire()
            total_time = time.monotonic() - start

            # First 3 should be fast, 4th forces wait
            assert burst_time < 0.5
            assert total_time > burst_time
        finally:
            await limiter.stop()


# ============================================================
# RateLimiter 429 retry tests
# ============================================================

class TestRateLimiter429Retry:
    @pytest.mark.asyncio
    async def test_retry_on_429(self):
        """Should retry on 429 response"""
        limiter = RateLimiter(RateLimitConfig(
            rate=100, burst=100, max_retries=3, backoff_base=0.01
        ))
        await limiter.start()
        try:
            call_count = 0

            async def failing_then_success():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise RetryAfter("Rate limited", retry_after=0.01)
                return "success"

            result = await limiter.execute(failing_then_success)
            assert result == "success"
            assert call_count == 3
        finally:
            await limiter.stop()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Should raise RetryAfter after max retries"""
        limiter = RateLimiter(RateLimitConfig(
            rate=100, burst=100, max_retries=2, backoff_base=0.01
        ))
        await limiter.start()
        try:
            call_count = 0

            async def always_fail():
                nonlocal call_count
                call_count += 1
                raise RetryAfter("Rate limited", retry_after=0.01)

            with pytest.raises(RetryAfter):
                await limiter.execute(always_fail)

            # Should have tried 1 initial + 2 retries = 3 times
            assert call_count == 3
        finally:
            await limiter.stop()

    @pytest.mark.asyncio
    async def test_retry_429_disabled(self):
        """Should not retry when retry_429 is False"""
        limiter = RateLimiter(RateLimitConfig(
            rate=100, burst=100, retry_429=False
        ))
        await limiter.start()
        try:
            async def always_fail():
                raise RetryAfter("Rate limited", retry_after=0.01)

            with pytest.raises(RetryAfter):
                await limiter.execute(always_fail)
        finally:
            await limiter.stop()

    @pytest.mark.asyncio
    async def test_uses_retry_after_from_response(self):
        """Should use retry_after value from API response"""
        limiter = RateLimiter(RateLimitConfig(
            rate=100, burst=100, max_retries=1, backoff_base=10.0
        ))
        await limiter.start()
        try:
            call_count = 0
            timestamps = []

            async def failing_then_success():
                nonlocal call_count
                call_count += 1
                timestamps.append(time.monotonic())
                if call_count == 1:
                    raise RetryAfter("Rate limited", retry_after=0.05)
                return "success"

            result = await limiter.execute(failing_then_success)
            assert result == "success"

            # Should have waited at least 0.05s (retry_after)
            delay = timestamps[1] - timestamps[0]
            assert delay >= 0.04  # small tolerance
        finally:
            await limiter.stop()


# ============================================================
# RateLimiter lifecycle tests
# ============================================================

class TestRateLimiterLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Should start and stop cleanly"""
        limiter = RateLimiter()
        await limiter.start()
        assert limiter._running is True
        await limiter.stop()
        assert limiter._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self):
        """Should handle double start gracefully"""
        limiter = RateLimiter()
        await limiter.start()
        await limiter.start()  # Should not raise
        await limiter.stop()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Should work as context manager via start/stop"""
        limiter = RateLimiter(RateLimitConfig(rate=100, burst=100))
        await limiter.start()
        try:
            await limiter.acquire()
        finally:
            await limiter.stop()


# ============================================================
# Integration: AioScamClient with rate limiter
# ============================================================

class TestClientRateLimiterIntegration:
    @pytest.mark.asyncio
    async def test_client_has_rate_limiter(self):
        """Client should have a rate limiter instance"""
        from aioscam.client import AioScamClient
        client = AioScamClient(token="test")
        assert hasattr(client, "rate_limiter")
        assert isinstance(client.rate_limiter, RateLimiter)
        await client.close()

    @pytest.mark.asyncio
    async def test_client_custom_rate_limit(self):
        """Client should accept custom rate limit config"""
        from aioscam.client import AioScamClient
        cfg = RateLimitConfig(rate=5, burst=10)
        client = AioScamClient(token="test", rate_limit=cfg)
        assert client.rate_limiter.config.rate == 5
        assert client.rate_limiter.config.burst == 10
        await client.close()

    @pytest.mark.asyncio
    async def test_bot_rate_limit_config(self):
        """Bot should pass rate_limit to client"""
        from aioscam.bot import Bot
        cfg = RateLimitConfig.strict()
        bot = Bot(token="test", rate_limit=cfg)
        assert bot._client.rate_limiter.config.rate == 5.0
        await bot.close()
