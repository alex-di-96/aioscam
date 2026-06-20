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

    mw = WebAppMiddleware(bot_token=BOT_TOKEN)
    app = web.Application(middlewares=[mw])

    @routes.get("/profile")
    async def profile(request: web.Request) -> web.Response:
        init_data: WebAppInitData = request["webapp_init_data"]
        return web.json_response({"user_id": init_data.user.id})

InitData lookup order (first match wins):
    1. ``Authorization: MaxWebApp <initData>`` header
    2. ``X-Webapp-Init-Data: <initData>`` header
    3. ``?initData=<initData>`` query parameter (for EventSource / SSE)
    4. JSON body field ``initData`` or ``init_data``

CORS:
    Add :func:`cors_middleware` when the mini-app frontend is hosted
    on a different domain from the bot API server::

        app = web.Application(middlewares=[
            cors_middleware(allow_origins=["https://my-app.vercel.app"]),
            WebAppMiddleware(bot_token=BOT_TOKEN),
        ])

Landing page:
    Use :class:`HomePage` to serve the bot's HTTP root with a generic,
    framework-provided page instead of a hand-written ``index.html`` or a
    raw ``/api/*`` response — it works without JS (plain "Open in Max"
    link) and doesn't expose any sign of the API surface to a plain
    visitor or scanner::

        app.router.add_get("/", HomePage(bot).handler)

Hiding /api/* from scanners:
    ``WebAppMiddleware`` already returns 404 (not 401) when a request has
    no initData attempt at all, so blind probing of ``/api/*`` paths looks
    identical to a route that doesn't exist. For stronger masking, move the
    API off the well-known ``/api`` prefix and add a :class:`WebAppFailGuard`
    to 404 out repeat offenders::

        guard = WebAppFailGuard(max_failures=20, window=60, ban_seconds=300)
        app = web.Application(middlewares=[
            WebAppMiddleware(bot_token=BOT_TOKEN, api_prefix="/a8f3e1", fail_guard=guard),
        ])
"""

import logging
from typing import Iterable, Optional

from aiohttp import web

from aioscam.webapp.failguard import WebAppFailGuard
from aioscam.webapp.homepage import HomePage
from aioscam.webapp.init_data import WebAppDataError, WebAppInitData, validate_init_data

__all__ = [
    "cors_middleware",
    "get_init_data",
    "WebAppMiddleware",
    "webapp_auth_middleware",
    "HomePage",
    "WebAppFailGuard",
]

logger = logging.getLogger(__name__)

_CORS_HEADERS = (
    "Content-Type",
    "Authorization",
    "X-Webapp-Init-Data",
)


def cors_middleware(
    allow_origins: Iterable[str] = ("*",),
    allow_methods: str = "GET, POST, OPTIONS",
    max_age: int = 600,
):
    """
    CORS middleware for aiohttp WebApp servers.

    Required when the mini-app frontend is served from a different
    domain than the bot API (e.g., frontend on Vercel, API on your VPS).

    Args:
        allow_origins: Allowed origins. Defaults to ``["*"]`` (open).
                       In production, restrict to your mini-app domain.
        allow_methods: Comma-separated allowed HTTP methods.
        max_age: Preflight cache duration in seconds.

    Usage::

        cors = cors_middleware(allow_origins=["https://my-app.vercel.app"])
        app = web.Application(middlewares=[cors, WebAppMiddleware(BOT_TOKEN)])
    """
    origins = list(allow_origins)

    @web.middleware
    async def _middleware(request: web.Request, handler):
        origin = request.headers.get("Origin", "")

        if origins == ["*"]:
            allow_origin = "*"
        elif origin in origins:
            allow_origin = origin
        else:
            allow_origin = ""

        # Handle preflight
        if request.method == "OPTIONS":
            return web.Response(
                status=204,
                headers={
                    "Access-Control-Allow-Origin": allow_origin,
                    "Access-Control-Allow-Methods": allow_methods,
                    "Access-Control-Allow-Headers": ", ".join(_CORS_HEADERS),
                    "Access-Control-Max-Age": str(max_age),
                },
            )

        response = await handler(request)

        if allow_origin:
            response.headers["Access-Control-Allow-Origin"] = allow_origin
            response.headers["Access-Control-Allow-Headers"] = ", ".join(_CORS_HEADERS)

        return response

    return _middleware


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
        WebAppDataError: If initData is missing (bare ``WebAppDataError``,
            no subclass — callers can use this to tell "nothing was sent"
            apart from "something was sent but invalid")
        WebAppSignatureError, WebAppExpiredError, WebAppMissingFieldError,
        WebAppParseError: If initData was present but failed validation
            (all subclasses of ``WebAppDataError``)
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
    """Extract raw initData string from headers or query (for EventSource)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("MaxWebApp "):
        return auth[len("MaxWebApp "):]

    header = request.headers.get("X-Webapp-Init-Data", "")
    if header:
        return header

    # EventSource cannot set headers — allow query param for SSE endpoints
    query_val = request.rel_url.query.get("initData", "")
    if query_val:
        return query_val

    return None


def WebAppMiddleware(
    bot_token: str,
    max_age: int = 86400,
    api_prefix: str = "/api",
    fail_guard: Optional[WebAppFailGuard] = None,
):
    """
    Configurable aiohttp middleware factory for Max WebApp auth.

    Validates initData on ``{api_prefix}/*`` requests and attaches
    :class:`WebAppInitData` to ``request["webapp_init_data"]``. Skips
    OPTIONS and any path that does not start with ``api_prefix``.

    Response codes are deliberately split so blind scanning can't tell
    "no route here" from "route exists, auth rejected":
        - 404 — no initData was sent at all (looks like a 404 for any path)
        - 401 — initData was sent but failed validation (bad signature,
          expired, malformed)

    Args:
        bot_token: Bot token used to verify the initData signature.
        max_age: Maximum allowed initData age in seconds. Pass 0 to skip.
        api_prefix: Path prefix to protect. Defaults to ``/api``; set it to
            an unguessable value (e.g. ``secrets.token_hex(8)``) to keep the
            API surface off wordlist-based scanners. Your frontend's fetch
            calls must then target the same prefix.
        fail_guard: Optional :class:`WebAppFailGuard` — when given, addresses
            that repeatedly fail auth get a flat 404 (no validation attempt)
            until their ban expires.

    Usage::

        app = web.Application(middlewares=[
            WebAppMiddleware(bot_token=BOT_TOKEN, max_age=3600),
        ])
    """

    @web.middleware
    async def _middleware(request: web.Request, handler):
        if request.method == "OPTIONS" or not request.path.startswith(api_prefix):
            return await handler(request)

        if fail_guard is not None and fail_guard.is_banned(request.remote or ""):
            return web.json_response({"ok": False, "error": "Not Found"}, status=404)

        try:
            init_data = await get_init_data(request, bot_token, max_age)
        except WebAppDataError as exc:
            if fail_guard is not None:
                fail_guard.record_failure(request.remote or "")
            if type(exc) is WebAppDataError:
                return web.json_response({"ok": False, "error": "Not Found"}, status=404)
            return web.json_response({"ok": False, "error": str(exc)}, status=401)

        request["webapp_init_data"] = init_data
        return await handler(request)

    return _middleware


@web.middleware
async def webapp_auth_middleware(request: web.Request, handler):
    """
    Bare aiohttp middleware that validates initData on every request.

    Reads bot token from ``app["bot_token"]``. Prefer :class:`WebAppMiddleware`
    for new code (accepts token directly in constructor).
    """
    bot_token: Optional[str] = request.app.get("bot_token")
    if not bot_token:
        logger.error("webapp_auth_middleware: app['bot_token'] is not set")
        return web.json_response({"ok": False, "error": "Server misconfiguration"}, status=500)

    if request.method == "OPTIONS" or request.path.startswith("/static"):
        return await handler(request)

    try:
        init_data = await get_init_data(request, bot_token)
    except WebAppDataError as exc:
        if type(exc) is WebAppDataError:
            return web.json_response({"ok": False, "error": "Not Found"}, status=404)
        return web.json_response({"ok": False, "error": str(exc)}, status=401)

    request["webapp_init_data"] = init_data
    return await handler(request)
