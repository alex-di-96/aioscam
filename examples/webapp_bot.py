"""
WebApp Bot — Max mini-app integration example

DEMONSTRATES
────────────
  • OpenAppButton with dynamic web_app + contact_id from get_me()
  • aiohttp HTTP server alongside polling (asyncio tasks)
  • /api/auth — initData HMAC validation via validate_init_data()
  • /api/contact — contact hash validation via validate_contact()
  • cors_middleware — CORS for cross-origin frontend hosting
  • WebAppMiddleware — per-request initData auth on API routes
  • Static file serving for the mini-app frontend

REGISTRATION (required before the mini-app opens)
──────────────────────────────────────────────────
  1. Go to https://business.max.ru/self
  2. Chats → Go → Select your bot → Advanced Settings → Configure
  3. Enter the HTTPS URL where index.html is served (e.g. Vercel)
  4. Save — the OpenAppButton will now work in chats

CALLING THE APP
───────────────
  • OpenAppButton in a message (sent by /webapp command below)
  • Deep link: https://max.ru/<botName>?startapp=<payload>

SECURITY
────────
  • BOT_TOKEN never reaches the frontend (only used server-side)
  • initData validated with HMAC-SHA256 on every /api/* request
  • Contact hash validated separately with user_id from initData
  • CORS restricted to WEBAPP_ORIGIN in production

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  export WEBAPP_URL=https://your-app.vercel.app      # where index.html is hosted
  export WEBAPP_ORIGIN=https://your-app.vercel.app   # for CORS (same as above)
  export API_PORT=8080                                # optional, default 8080
  python examples/webapp_bot.py
"""

import asyncio
import logging
import os
from pathlib import Path

from aiohttp import web

from aioscam import Bot, BotCommand, Command, Dispatcher, Router
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.webapp import WebAppDataError, validate_contact, validate_init_data
from aioscam.webapp.aiohttp import WebAppMiddleware, cors_middleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-app.vercel.app")
WEBAPP_ORIGIN = os.environ.get("WEBAPP_ORIGIN", "*")
API_PORT = int(os.environ.get("API_PORT", "8080"))

STATIC_DIR = Path(__file__).parent / "webapp"

# ── Bot setup ─────────────────────────────────────────────────────────────────

bot = Bot()
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "👋 Привет! Нажми кнопку ниже чтобы открыть мини-приложение.",
    )


@router.message_created(Command("webapp"))
async def cmd_webapp(event):
    """Send a message with OpenAppButton that opens the mini-app."""
    me = await event.bot.get_me()

    kb = KeyboardBuilder(inline=True)
    kb.open_app(
        text="Открыть приложение",
        web_app=me.username,       # bot username
        contact_id=me.id,          # bot user_id
        payload="demo",            # start_param accessible in window.WebApp.initDataUnsafe.start_param
    )

    await event.answer(
        "🚀 Нажми кнопку чтобы открыть мини-приложение:",
        inline_keyboard=kb.build(),
    )


# ── API handlers ──────────────────────────────────────────────────────────────

async def handle_auth(request: web.Request) -> web.Response:
    """
    POST /api/auth
    Validates initData and returns the user object.
    WebAppMiddleware has already validated initData — it's in request["webapp_init_data"].
    """
    init_data = request["webapp_init_data"]
    user = init_data.user

    return web.json_response({
        "ok": True,
        "user": {
            "id": user.id if user else None,
            "first_name": user.first_name if user else None,
            "username": user.username if user else None,
            "language_code": user.language_code if user else None,
        },
        "start_param": init_data.start_param,
        "platform": request.headers.get("X-Max-Platform"),
    })


async def handle_contact(request: web.Request) -> web.Response:
    """
    POST /api/contact
    Body: { phone, authDate, hash }   (from window.WebApp.requestContact())
    Header: Authorization: MaxWebApp <initData>

    Validates initData (done by middleware) and contact hash separately.
    """
    init_data = request["webapp_init_data"]

    if not init_data.user:
        return web.json_response({"ok": False, "error": "No user in initData"}, status=400)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON body"}, status=400)

    phone = body.get("phone", "")
    auth_date = body.get("authDate", "")
    contact_hash = body.get("hash", "")

    if not all([phone, auth_date, contact_hash]):
        return web.json_response(
            {"ok": False, "error": "Missing phone, authDate, or hash"},
            status=400,
        )

    try:
        contact = validate_contact(
            phone=phone,
            auth_date=auth_date,
            contact_hash=contact_hash,
            user_id=init_data.user.id,
            bot_token=BOT_TOKEN,
        )
    except WebAppDataError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=401)

    return web.json_response({"ok": True, "phone": contact.phone})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "aioscam-webapp"})


# ── aiohttp app factory ───────────────────────────────────────────────────────

def build_web_app() -> web.Application:
    """Build the aiohttp Application with middleware stack and routes."""

    # Middleware order: CORS → WebApp auth (skips /static and OPTIONS automatically)
    app = web.Application(middlewares=[
        cors_middleware(allow_origins=[WEBAPP_ORIGIN]),
        WebAppMiddleware(bot_token=BOT_TOKEN, max_age=3600),
    ])

    # API routes (protected by WebAppMiddleware)
    app.router.add_post("/api/auth", handle_auth)
    app.router.add_post("/api/contact", handle_contact)

    # Health check — no auth needed (WebAppMiddleware skips non-/api paths)
    app.router.add_get("/health", handle_health)

    # Static files — mini-app frontend (WebAppMiddleware skips /static)
    if STATIC_DIR.is_dir():
        app.router.add_static("/", path=str(STATIC_DIR), name="static", show_index=True)
        logger.info(f"Serving static files from {STATIC_DIR}")

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("MAX_BOT_TOKEN environment variable is not set")

    me = await bot.get_me()
    logger.info(f"Bot: @{me.username} (id={me.id})")
    logger.info(f"WebApp URL: {WEBAPP_URL}")
    logger.info(f"API server: http://0.0.0.0:{API_PORT}")

    await bot.set_my_commands([
        BotCommand(name="start",  description="Приветствие"),
        BotCommand(name="webapp", description="Открыть мини-приложение"),
    ])

    dp.include_router(router)

    # Start aiohttp server
    web_app = build_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()

    logger.info("WebApp API server started. Bot polling...")
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await runner.cleanup()
        await bot.close()
        logger.info("Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
