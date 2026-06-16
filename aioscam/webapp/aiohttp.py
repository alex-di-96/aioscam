"""
Aiohttp helpers for Max WebApp request handling.

The mini-app frontend sends ``window.WebApp.initData`` to the bot's
HTTP API. Use :func:`get_init_data` to extract and validate it from
an incoming aiohttp request, or :class:`WebAppMiddleware` to validate
automatically on all (or selected) routes.

Usage — per-handler::

    async def profile(request: web.Request) -> web.Response:
        init_data = await get_init_data(request, bot_token=BOT_TOKEN)
        return web.json_response({"user_id": init_data.user.id})

Usage — middleware (validates every request to the app)::

    app = web.Application(middlewares=[WebAppMiddleware(bot_token=BOT_TOKEN)])

    @routes.get("/profile")
    async def profile(request: web.Request) -> web.Response:
        init_data: WebAppInitData = request["webapp_init_data"]
        return web.json_response({"user_id": init_data.user.id})

InitData lookup order (first match wins):
    1. ``Authorization: MaxWebApp <initData>`` header
    2. ``X-Webapp-Init-Data: <initData>`` header
    3. JSON body field ``initData`` or ``init_data``
"""

import logging
from typing import Optional

from aiohttp import web

from aioscam.webapp.init_data import WebAppDataError, WebAppInitData, validate_init_data

logger = logging.getLogger(__name__)


async def get_init_data(
    request: web.Request,
    bot_token: str,
    max_age: int = 86400,
) -> WebAppInitData:
    """
    Extract and validate initData from an aiohttp request.

    Args:
        request: Incoming aiohttp :class:`web.Request`
        bot_token: Bot token (``MAX_BOT_TOKEN``)
        max_age: Maximum allowed data age in seconds. Pass 0 to skip.

    Returns:
        Validated :class:`WebAppInitData`

    Raises:
        WebAppDataError: If initData is missing, invalid, or expired
    """
    raw: Optional[str] = _extract_raw(request)

    if raw is None:
        try:
            body = await request.json()
            raw = body.get("initData") or body.get("init_data")
        except Exception:
            pass

    if not raw:
        raise WebAppDataError("initData not found in request headers or body")

    return validate_init_data(raw, bot_token, max_age)


def _extract_raw(request: web.Request) -> Optional[str]:
    """Extract raw initData string from headers only (no body I/O)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("MaxWebApp "):
        return auth[len("MaxWebApp "):]

    header = request.headers.get("X-Webapp-Init-Data", "")
    if header:
        return header

    return None


@web.middleware
async def webapp_auth_middleware(request: web.Request, handler):
    """
    Aiohttp middleware that validates initData on every request.

    Attaches :class:`WebAppInitData` to ``request["webapp_init_data"]``.
    Returns HTTP 401 if initData is missing or invalid.

    Attach ``bot_token`` via ``app["bot_token"]`` before adding the middleware::

        app["bot_token"] = os.environ["MAX_BOT_TOKEN"]
        app.middlewares.append(webapp_auth_middleware)
    """
    bot_token: Optional[str] = request.app.get("bot_token")
    if not bot_token:
        logger.error("webapp_auth_middleware: app['bot_token'] is not set")
        return web.json_response({"ok": False, "error": "Server misconfiguration"}, status=500)

    try:
        init_data = await get_init_data(request, bot_token)
    except WebAppDataError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=401)

    request["webapp_init_data"] = init_data
    return await handler(request)


class WebAppMiddleware:
    """
    Configurable aiohttp middleware for Max WebApp auth.

    Unlike the bare :func:`webapp_auth_middleware`, this class accepts
    ``bot_token`` directly so ``app["bot_token"]`` is not required::

        mw = WebAppMiddleware(bot_token=BOT_TOKEN, max_age=3600)
        app = web.Application(middlewares=[mw])
    """

    def __init__(self, bot_token: str, max_age: int = 86400):
        self._bot_token = bot_token
        self._max_age = max_age

    @web.middleware
    async def __call__(self, request: web.Request, handler):
        try:
            init_data = await get_init_data(request, self._bot_token, self._max_age)
        except WebAppDataError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=401)

        request["webapp_init_data"] = init_data
        return await handler(request)
