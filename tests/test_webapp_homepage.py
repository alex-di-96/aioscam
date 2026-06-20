"""Tests for aioscam.webapp.aiohttp.HomePage"""

from unittest.mock import AsyncMock

import pytest

from aioscam.webapp.aiohttp import HomePage


def make_bot(**me_overrides):
    me = {"username": "demo_bot", "name": "Demo Bot", "description": "Demo description"}
    me.update(me_overrides)
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=me)
    return bot


class TestHomePageRender:
    @pytest.mark.asyncio
    async def test_uses_bot_info_by_default(self):
        home = HomePage(make_bot())
        html = await home.render()

        assert "Demo Bot" in html
        assert "Demo description" in html
        assert "https://max.ru/demo_bot" in html

    @pytest.mark.asyncio
    async def test_explicit_overrides_skip_bot_lookup(self):
        bot = make_bot()
        home = HomePage(bot, title="Custom", description="Custom desc", username="custom_bot")
        html = await home.render()

        bot.get_me.assert_not_called()
        assert "Custom" in html
        assert "Custom desc" in html
        assert "https://max.ru/custom_bot" in html

    @pytest.mark.asyncio
    async def test_no_bot_no_overrides_falls_back(self):
        home = HomePage()
        html = await home.render()

        assert "Max Bot" in html
        assert 'href="#"' in html

    @pytest.mark.asyncio
    async def test_get_me_failure_falls_back_gracefully(self):
        bot = AsyncMock()
        bot.get_me = AsyncMock(side_effect=RuntimeError("network down"))
        home = HomePage(bot)

        html = await home.render()

        assert "Max Bot" in html

    @pytest.mark.asyncio
    async def test_render_caches_bot_lookup(self):
        bot = make_bot()
        home = HomePage(bot)

        await home.render()
        await home.render()

        bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_open_in_max_false_hides_fallback(self):
        home = HomePage(make_bot(), show_open_in_max=False)
        html = await home.render()

        assert '<div id="open-in-max-fallback">' not in html
        assert "Open in Max" not in html

    @pytest.mark.asyncio
    async def test_escapes_html_in_title_and_description(self):
        home = HomePage(make_bot(name="<script>alert(1)</script>", description="<b>x</b>"))
        html = await home.render()

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    @pytest.mark.asyncio
    async def test_extra_head_and_body_injected_verbatim(self):
        home = HomePage(
            make_bot(),
            extra_head='<link rel="stylesheet" href="/static/app.css">',
            extra_body='<div id="app"></div>',
        )
        html = await home.render()

        assert '<link rel="stylesheet" href="/static/app.css">' in html
        assert '<div id="app"></div>' in html

    @pytest.mark.asyncio
    async def test_includes_bridge_script(self):
        home = HomePage(make_bot())
        html = await home.render()

        assert "https://st.max.ru/js/max-web-app.js" in html


class TestHomePageHandler:
    @pytest.mark.asyncio
    async def test_handler_returns_html_response(self):
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        app = web.Application()
        home = HomePage(make_bot())
        app.router.add_get("/", home.handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/")
            assert resp.status == 200
            assert resp.content_type == "text/html"
            body = await resp.text()
            assert "Demo Bot" in body

    @pytest.mark.asyncio
    async def test_handler_does_not_reveal_api_routes(self):
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        app = web.Application()
        home = HomePage(make_bot())
        app.router.add_get("/", home.handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/")
            body = await resp.text()
            assert "/api/" not in body
