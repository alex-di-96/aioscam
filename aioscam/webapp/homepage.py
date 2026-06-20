"""
Generic landing page for a bot's WebApp HTTP server.

Serves the same self-contained HTML to everyone hitting the server's root:
a plain visitor (or a port scanner) without JavaScript sees the bot's name,
description, and an "Open in Max" link — nothing that hints at ``/api/*``
existing underneath. Opened from inside the Max client, the same page loads
the Bridge SDK and can act as the Mini App's start screen.

Usage::

    from aioscam.webapp.aiohttp import HomePage

    home = HomePage(bot)
    app.router.add_get("/", home.handler)

Bring your own Mini App markup/scripts on top of the default shell::

    home = HomePage(
        bot,
        title="My Bot",
        description="What this bot does.",
        extra_head='<link rel="stylesheet" href="/static/app.css">',
        extra_body='<div id="app"></div><script src="/static/app.js"></script>',
    )
"""

import logging
from html import escape
from typing import Any, Optional, Tuple

from aiohttp import web

from aioscam.utils.deep_linking import create_deep_link

logger = logging.getLogger(__name__)

_BRIDGE_SCRIPT_URL = "https://st.max.ru/js/max-web-app.js"

_FALLBACK_BLOCK = """<div id="open-in-max-fallback">
  <a class="open-in-max" href="{deep_link}">Open in Max</a>
</div>"""

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="{bridge_url}"></script>
{extra_head}
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 48px auto;
          padding: 0 16px; text-align: center; color: #1a1a1a; }}
  .open-in-max {{ display: inline-block; margin-top: 24px; padding: 12px 24px;
                  background: #0078ff; color: #fff; text-decoration: none;
                  border-radius: 10px; font-weight: 600; }}
  .description {{ color: #555; line-height: 1.5; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="description">{description}</p>
{fallback}
{extra_body}
<script>
  (function () {{
    var fallback = document.getElementById("open-in-max-fallback");
    if (fallback && typeof window.WebApp !== "undefined" && window.WebApp) {{
      fallback.style.display = "none";
    }}
  }})();
</script>
</body>
</html>
"""


class HomePage:
    """
    Generic, reusable landing page for a bot's WebApp HTTP server.

    Bot name/description/username are read once from :meth:`Bot.get_me`
    (cached by the ``Bot`` instance itself) unless overridden here. The
    rendered HTML is cached after the first request.
    """

    def __init__(
        self,
        bot: Optional[Any] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        username: Optional[str] = None,
        deep_link_payload: str = "",
        lang: str = "ru",
        show_open_in_max: bool = True,
        extra_head: str = "",
        extra_body: str = "",
    ) -> None:
        self._bot = bot
        self._title = title
        self._description = description
        self._username = username
        self._deep_link_payload = deep_link_payload
        self._lang = lang
        self._show_open_in_max = show_open_in_max
        self._extra_head = extra_head
        self._extra_body = extra_body
        self._cached_html: Optional[str] = None

    async def _resolve_bot_info(self) -> Tuple[str, str, str]:
        title, description, username = self._title, self._description, self._username

        if (title is None or description is None or username is None) and self._bot is not None:
            try:
                me = await self._bot.get_me()
            except Exception as exc:
                logger.warning(f"HomePage: get_me() failed, using fallback text: {exc}")
                me = {}

            if title is None:
                title = me.get("name") or me.get("first_name") or "Max Bot"
            if description is None:
                description = me.get("description", "")
            if username is None:
                username = me.get("username", "")

        return title or "Max Bot", description or "", username or ""

    async def render(self) -> str:
        """Render (and cache) the page HTML. Construct a new HomePage to re-render."""
        if self._cached_html is not None:
            return self._cached_html

        title, description, username = await self._resolve_bot_info()
        deep_link = create_deep_link(username, self._deep_link_payload) if username else "#"

        fallback = (
            _FALLBACK_BLOCK.format(deep_link=escape(deep_link))
            if self._show_open_in_max
            else ""
        )

        self._cached_html = _PAGE_TEMPLATE.format(
            lang=escape(self._lang),
            title=escape(title),
            description=escape(description),
            bridge_url=_BRIDGE_SCRIPT_URL,
            extra_head=self._extra_head,
            fallback=fallback,
            extra_body=self._extra_body,
        )
        return self._cached_html

    async def handler(self, request: web.Request) -> web.Response:
        html = await self.render()
        return web.Response(text=html, content_type="text/html")
