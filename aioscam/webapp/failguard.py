"""
Per-IP failed-auth tracking for :class:`~aioscam.webapp.aiohttp.WebAppMiddleware`.

Slows down automated probing against the WebApp API surface: after
``max_failures`` failed ``initData`` validations from the same address
within ``window`` seconds, further requests from that address get a plain
404 — indistinguishable from a route that was never registered — for
``ban_seconds``, without even attempting validation.

This is a defense-in-depth speed bump against blind scanners, not a
substitute for the HMAC signature check ``WebAppMiddleware`` already does.

Usage::

    from aioscam.webapp.aiohttp import WebAppMiddleware, WebAppFailGuard

    guard = WebAppFailGuard(max_failures=20, window=60, ban_seconds=300)
    app.middlewares.append(WebAppMiddleware(bot_token=BOT_TOKEN, fail_guard=guard))
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class WebAppFailGuard:
    """In-memory sliding-window failed-auth tracker, keyed by remote address."""

    def __init__(
        self,
        max_failures: int = 20,
        window: float = 60.0,
        ban_seconds: float = 300.0,
    ) -> None:
        self.max_failures = max_failures
        self.window = window
        self.ban_seconds = ban_seconds
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._banned_until: Dict[str, float] = {}

    def is_banned(self, address: str) -> bool:
        """Check whether ``address`` is currently banned."""
        until = self._banned_until.get(address)
        if until is None:
            return False
        if until <= time.monotonic():
            del self._banned_until[address]
            return False
        return True

    def record_failure(self, address: str) -> None:
        """Record one failed-auth attempt from ``address``; ban it if over threshold."""
        now = time.monotonic()
        bucket = self._failures[address]
        bucket.append(now)

        cutoff = now - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_failures:
            self._banned_until[address] = now + self.ban_seconds
            bucket.clear()
