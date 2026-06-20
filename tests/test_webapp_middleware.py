"""Tests for aioscam.webapp.aiohttp.WebAppMiddleware / webapp_auth_middleware"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from aioscam.webapp.aiohttp import WebAppFailGuard, WebAppMiddleware, webapp_auth_middleware

BOT_TOKEN = "test_bot_token_123"


def _make_init_data(params: dict, bot_token: str = BOT_TOKEN, corrupt_hash: bool = False) -> str:
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if corrupt_hash:
        computed_hash = "00" * 32
    return urlencode({**params, "hash": computed_hash})


def _valid_init_data() -> str:
    return _make_init_data({"auth_date": str(int(time.time())), "query_id": "q1"})


async def _ok_handler(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "had_init_data": "webapp_init_data" in request})


class TestWebAppMiddlewareStatusCodes:
    @pytest.mark.asyncio
    async def test_missing_init_data_returns_404(self):
        app = web.Application(middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN)])
        app.router.add_get("/api/me", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/me")
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_invalid_init_data_returns_401(self):
        app = web.Application(middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN)])
        app.router.add_get("/api/me", _ok_handler)

        bad = _make_init_data({"auth_date": str(int(time.time())), "query_id": "q1"}, corrupt_hash=True)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/me", headers={"Authorization": f"MaxWebApp {bad}"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_valid_init_data_passes_through(self):
        app = web.Application(middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN)])
        app.router.add_get("/api/me", _ok_handler)

        good = _valid_init_data()

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/me", headers={"Authorization": f"MaxWebApp {good}"})
            assert resp.status == 200
            body = await resp.json()
            assert body == {"ok": True, "had_init_data": True}

    @pytest.mark.asyncio
    async def test_non_api_path_skips_auth(self):
        app = web.Application(middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN)])
        app.router.add_get("/", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/")
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_options_skips_auth(self):
        app = web.Application(middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN)])

        async def options_handler(request):
            return web.Response(status=204)

        app.router.add_route("OPTIONS", "/api/me", options_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.options("/api/me")
            assert resp.status == 204


class TestWebAppMiddlewareCustomPrefix:
    @pytest.mark.asyncio
    async def test_custom_prefix_protects_matching_path(self):
        app = web.Application(
            middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN, api_prefix="/secret-abc")]
        )
        app.router.add_get("/secret-abc/me", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/secret-abc/me")
            assert resp.status == 404  # protected, but no initData sent

    @pytest.mark.asyncio
    async def test_default_prefix_path_unprotected_when_custom_prefix_set(self):
        app = web.Application(
            middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN, api_prefix="/secret-abc")]
        )
        app.router.add_get("/api/me", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/me")
            assert resp.status == 200  # not behind the configured prefix anymore


class TestWebAppMiddlewareFailGuard:
    @pytest.mark.asyncio
    async def test_bans_after_repeated_failures(self):
        guard = WebAppFailGuard(max_failures=3, window=60.0, ban_seconds=300.0)
        app = web.Application(
            middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN, fail_guard=guard)]
        )
        app.router.add_get("/api/me", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            for _ in range(3):
                resp = await client.get("/api/me")
                assert resp.status == 404

            # Guard should now be banning this address outright — even a
            # request that would otherwise be a 401 (bad signature) gets 404.
            bad = _make_init_data(
                {"auth_date": str(int(time.time())), "query_id": "q1"}, corrupt_hash=True
            )
            resp = await client.get("/api/me", headers={"Authorization": f"MaxWebApp {bad}"})
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_valid_init_data_does_not_count_as_failure(self):
        guard = WebAppFailGuard(max_failures=2, window=60.0, ban_seconds=300.0)
        app = web.Application(
            middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN, fail_guard=guard)]
        )
        app.router.add_get("/api/me", _ok_handler)

        good = _valid_init_data()

        async with TestClient(TestServer(app)) as client:
            for _ in range(5):
                resp = await client.get("/api/me", headers={"Authorization": f"MaxWebApp {good}"})
                assert resp.status == 200


class TestWebappAuthMiddlewareStatusCodes:
    @pytest.mark.asyncio
    async def test_missing_init_data_returns_404(self):
        app = web.Application(middlewares=[webapp_auth_middleware])
        app["bot_token"] = BOT_TOKEN
        app.router.add_get("/profile", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/profile")
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_invalid_init_data_returns_401(self):
        app = web.Application(middlewares=[webapp_auth_middleware])
        app["bot_token"] = BOT_TOKEN
        app.router.add_get("/profile", _ok_handler)

        bad = _make_init_data({"auth_date": str(int(time.time())), "query_id": "q1"}, corrupt_hash=True)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/profile", headers={"Authorization": f"MaxWebApp {bad}"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_static_path_skips_auth(self):
        app = web.Application(middlewares=[webapp_auth_middleware])
        app["bot_token"] = BOT_TOKEN
        app.router.add_get("/static/app.js", _ok_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/static/app.js")
            assert resp.status == 200
