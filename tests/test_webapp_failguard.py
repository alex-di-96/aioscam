"""Tests for aioscam.webapp.aiohttp.WebAppFailGuard"""

from unittest.mock import patch

from aioscam.webapp.aiohttp import WebAppFailGuard


class TestWebAppFailGuard:
    def test_not_banned_by_default(self):
        guard = WebAppFailGuard()
        assert guard.is_banned("1.2.3.4") is False

    def test_bans_after_threshold(self):
        guard = WebAppFailGuard(max_failures=3, window=60.0, ban_seconds=300.0)
        for _ in range(2):
            guard.record_failure("1.2.3.4")
        assert guard.is_banned("1.2.3.4") is False

        guard.record_failure("1.2.3.4")
        assert guard.is_banned("1.2.3.4") is True

    def test_other_addresses_unaffected(self):
        guard = WebAppFailGuard(max_failures=2, window=60.0, ban_seconds=300.0)
        guard.record_failure("1.2.3.4")
        guard.record_failure("1.2.3.4")
        assert guard.is_banned("1.2.3.4") is True
        assert guard.is_banned("5.6.7.8") is False

    def test_failures_outside_window_expire(self):
        guard = WebAppFailGuard(max_failures=2, window=10.0, ban_seconds=300.0)
        with patch("time.monotonic", return_value=1000.0):
            guard.record_failure("1.2.3.4")
        with patch("time.monotonic", return_value=1020.0):
            # 20s later, outside the 10s window — first failure should be pruned
            guard.record_failure("1.2.3.4")
            assert guard.is_banned("1.2.3.4") is False

    def test_ban_expires_after_ban_seconds(self):
        guard = WebAppFailGuard(max_failures=1, window=60.0, ban_seconds=100.0)
        with patch("time.monotonic", return_value=1000.0):
            guard.record_failure("1.2.3.4")
            assert guard.is_banned("1.2.3.4") is True

        with patch("time.monotonic", return_value=1050.0):
            assert guard.is_banned("1.2.3.4") is True  # still within ban window

        with patch("time.monotonic", return_value=1101.0):
            assert guard.is_banned("1.2.3.4") is False  # ban expired

    def test_failure_count_resets_after_ban(self):
        guard = WebAppFailGuard(max_failures=2, window=60.0, ban_seconds=0.0)
        guard.record_failure("1.2.3.4")
        guard.record_failure("1.2.3.4")
        assert guard.is_banned("1.2.3.4") is False  # ban_seconds=0 expires immediately

        # A single new failure should not immediately re-ban (counter was cleared)
        guard.record_failure("1.2.3.4")
        assert guard.is_banned("1.2.3.4") is False
