"""
Tests for AioScamClient error handling: HTTP 401/403/404/429 and
RateLimiter token exhaustion / 429 retry.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aioscam.client.client import AioScamClient
from aioscam.client.response import Response
from aioscam.exceptions import (
    UnauthorizedError, ForbiddenError, NotFoundError,
    RetryAfter, ApiError, NetworkError, TimeoutError as AioScamTimeoutError,
)
from aioscam.limiter import RateLimiter, RateLimitConfig


# ─── _handle_error ──────────────────────────────────────────────────────────

class TestHandleError:
    def _client(self):
        return AioScamClient(token="t")

    def _resp(self, status, error=None, result=None):
        return Response(
            ok=False,
            result=result or {},
            status_code=status,
            error=error or f"HTTP {status}",
        )

    def test_401_raises_unauthorized(self):
        client = self._client()
        with pytest.raises(UnauthorizedError):
            client._handle_error(self._resp(401))

    def test_403_raises_forbidden(self):
        client = self._client()
        with pytest.raises(ForbiddenError):
            client._handle_error(self._resp(403))

    def test_404_raises_not_found(self):
        client = self._client()
        with pytest.raises(NotFoundError):
            client._handle_error(self._resp(404))

    def test_429_raises_retry_after(self):
        client = self._client()
        with pytest.raises(RetryAfter):
            client._handle_error(self._resp(429, result={"retry_after": 5}))

    def test_429_retry_after_value(self):
        client = self._client()
        try:
            client._handle_error(self._resp(429, result={"retry_after": 10}))
        except RetryAfter as e:
            assert e.retry_after == 10

    def test_500_raises_api_error(self):
        client = self._client()
        with pytest.raises(ApiError):
            client._handle_error(self._resp(500))

    def test_400_raises_api_error(self):
        client = self._client()
        with pytest.raises(ApiError):
            client._handle_error(self._resp(400))


# ─── Response model ──────────────────────────────────────────────────────────

class TestResponseModel:
    def test_ok_true_for_200(self):
        r = Response(ok=True, status_code=200)
        assert r.ok is True

    def test_description_from_result(self):
        r = Response(ok=False, status_code=400, error="err", result={"description": "bad input"})
        assert r.description == "bad input"

    def test_code_from_result(self):
        r = Response(ok=False, status_code=400, error="err", result={"code": 42})
        assert r.code == 42

    def test_description_none_when_ok(self):
        r = Response(ok=True, status_code=200, result={"description": "ok"})
        assert r.description is None

    def test_code_none_when_ok(self):
        r = Response(ok=True, status_code=200, result={"code": 0})
        assert r.code is None


# ─── RateLimiter ─────────────────────────────────────────────────────────────

class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_execute_calls_func(self):
        limiter = RateLimiter(RateLimitConfig(rate=100, burst=100))
        await limiter.start()
        func = AsyncMock(return_value="result")
        result = await limiter.execute(func)
        assert result == "result"
        func.assert_called_once()
        await limiter.stop()

    @pytest.mark.asyncio
    async def test_execute_passes_args(self):
        limiter = RateLimiter(RateLimitConfig(rate=100, burst=100))
        await limiter.start()
        func = AsyncMock(return_value=42)
        result = await limiter.execute(func, "a", "b", key="val")
        func.assert_called_once_with("a", "b", key="val")
        await limiter.stop()

    @pytest.mark.asyncio
    async def test_429_retried_then_success(self):
        limiter = RateLimiter(RateLimitConfig(
            rate=100, burst=100, retry_429=True, max_retries=2, backoff_base=0.01
        ))
        await limiter.start()

        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RetryAfter("rate limit", retry_after=0)
            return "ok"

        result = await limiter.execute(flaky)
        assert result == "ok"
        assert call_count == 2
        await limiter.stop()

    @pytest.mark.asyncio
    async def test_429_max_retries_exceeded_raises(self):
        limiter = RateLimiter(RateLimitConfig(
            rate=100, burst=100, retry_429=True, max_retries=2, backoff_base=0.01
        ))
        await limiter.start()

        async def always_429():
            raise RetryAfter("rate limit", retry_after=0)

        with pytest.raises(RetryAfter):
            await limiter.execute(always_429)
        await limiter.stop()

    @pytest.mark.asyncio
    async def test_acquire_decrements_tokens(self):
        config = RateLimitConfig(rate=100, burst=5)
        limiter = RateLimiter(config)
        initial = limiter.available_tokens
        assert initial == 5.0
        await limiter.acquire()
        assert limiter.available_tokens < initial

    @pytest.mark.asyncio
    async def test_stop_cancels_background_task(self):
        limiter = RateLimiter()
        await limiter.start()
        assert limiter._task is not None
        await limiter.stop()
        assert limiter._task is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        limiter = RateLimiter()
        await limiter.start()
        task1 = limiter._task
        await limiter.start()  # second start should be no-op
        task2 = limiter._task
        assert task1 is task2
        await limiter.stop()


# ─── AioScamClient.make_temp_path ────────────────────────────────────────────

class TestMakeTempPath:
    def test_returns_string(self):
        path = AioScamClient.make_temp_path(".jpg")
        assert isinstance(path, str)

    def test_extension_included(self):
        path = AioScamClient.make_temp_path(".png")
        assert path.endswith(".png")

    def test_no_extension(self):
        path = AioScamClient.make_temp_path()
        assert "aioscam_" in path

    def test_paths_unique(self):
        import time
        p1 = AioScamClient.make_temp_path(".jpg")
        time.sleep(0.001)
        p2 = AioScamClient.make_temp_path(".jpg")
        assert p1 != p2

    def test_custom_directory(self):
        path = AioScamClient.make_temp_path(".bin", directory="/var/tmp")
        assert path.startswith("/var/tmp/")
