"""
WebApp Bot — Max mini-app полный пример с двусторонней связью

АРХИТЕКТУРА
───────────
  Bot  ←──polling──→  Max API
   │                      ↑
   │  SSE push            │ OpenAppButton
   ▼                      │
  WebApp ──POST /api/*──► aiohttp server

ЭНДПОИНТЫ
──────────
  GET  /               — общая landing-страница (HomePage), без auth, без JS не ломается
  GET  /health          — статус сервера (без auth)
  GET  /app, /app/*     — Mini App фронтенд (HTML/JS) — это URL для Max bot dashboard,
                           НЕ bare WEBAPP_URL
  GET  /api/me          — профиль пользователя из initData
  POST /api/auth        — валидация initData, возвращает user
  POST /api/contact     — запрос и валидация контакта
  POST /api/send        — WebApp отправляет сообщение через бота
  GET  /api/events      — SSE поток: bot→WebApp push-уведомления

КОМАНДЫ БОТА
────────────
  /start               — приветствие
  /webapp              — открыть мини-приложение
  /echo <текст>        — бот отвечает + толкает событие в WebApp
  /status              — показывает активные SSE-подключения

ДВУСТОРОННЯЯ СВЯЗЬ
──────────────────
  WebApp → Bot:  POST /api/send → бот получает и обрабатывает
  Bot → WebApp:  SSE /api/events — real-time события от бота

БЕЗОПАСНОСТЬ
────────────
  • BOT_TOKEN никогда не покидает сервер
  • initData валидируется HMAC-SHA256 на каждом /api/* запросе
  • Контакт валидируется отдельным HMAC с user_id из initData
  • CORS ограничен WEBAPP_ORIGIN
  • Лимит тела запроса: 64 KB
  • Отсутствующий initData → 404 (как несуществующий роут), неверный → 401 —
    слепой перебор путей не отличает существующий /api/* от 404
  • WebAppFailGuard: после повторных неудачных попыток с одного адреса —
    плоский 404 без проверки подписи на ban_seconds

ЗАПУСК
──────
  export MAX_BOT_TOKEN=your_token_here
  export WEBAPP_URL=https://your-app.example.com
  export WEBAPP_ORIGIN=https://your-app.example.com
  export API_PORT=8080
  python examples/webapp_bot.py

  В Max bot dashboard в качестве Mini App URL указать WEBAPP_URL + /app
  (например https://your-app.example.com/app), а не сам WEBAPP_URL —
  bare WEBAPP_URL отдаёт только общую HomePage.
"""

import asyncio
import logging
import os
from pathlib import Path

from aiohttp import web

from aioscam import Bot, BotCommand, Command, Dispatcher, Router
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.utils.capabilities import BotCapabilities
from aioscam.webapp import (
    EventStreamManager,
    FeatureUnavailableError,
    WebAppDataError,
    WebAppExpiredError,
    WebAppSignatureError,
    validate_contact,
)
from aioscam.webapp.aiohttp import HomePage, WebAppFailGuard, WebAppMiddleware, cors_middleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

BOT_TOKEN   = os.environ.get("MAX_BOT_TOKEN", "")
WEBAPP_URL  = os.environ.get("WEBAPP_URL",    "https://your-app.example.com")
WEBAPP_ORIGIN = os.environ.get("WEBAPP_ORIGIN", "*")
API_PORT    = int(os.environ.get("API_PORT",   "8080"))
MAX_BODY    = 64 * 1024  # 64 KB
WEBAPP_PATH = "/app"  # register WEBAPP_URL + WEBAPP_PATH as the Mini App URL in the Max bot dashboard

STATIC_DIR = Path(__file__).parent / "webapp"

# ── SSE manager (singleton) ────────────────────────────────────────────────────

sse = EventStreamManager()
fail_guard = WebAppFailGuard(max_failures=20, window=60.0, ban_seconds=300.0)

# ── Bot setup ──────────────────────────────────────────────────────────────────

bot = Bot()
dp  = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "👋 Привет! Я демо-бот AioScam WebApp.\n\n"
        "Команды:\n"
        "/webapp — открыть мини-приложение\n"
        "/echo <текст> — эхо + push в WebApp\n"
        "/status — активные WebApp-сессии"
    )


@router.message_created(Command("webapp"))
async def cmd_webapp(event):
    me = await event.bot.get_me()
    kb = KeyboardBuilder(inline=True)
    kb.open_app(
        text="Открыть мини-приложение",
        web_app=me["username"],
        contact_id=me["user_id"],
        payload="demo",
    )
    await event.answer(
        "🚀 Нажми кнопку чтобы открыть мини-приложение:",
        inline_keyboard=kb.build(),
    )


@router.message_created(Command("echo"))
async def cmd_echo(event):
    """Отвечает в чат И толкает событие в открытый WebApp пользователя."""
    text = event.message.body.text.replace("/echo", "", 1).strip()
    if not text:
        await event.answer("Использование: /echo <текст>")
        return

    sender = event.message.sender
    user_id = sender["user_id"]

    # Ответ в чат
    await event.answer(f"🔁 {text}")

    # Push в WebApp (если открыт)
    n = await sse.publish(
        user_id=user_id,
        event="bot_message",
        data={
            "text": text,
            "from": "bot",
            "command": "echo",
        },
    )
    if n:
        await event.answer(f"📡 Отправлено в {n} WebApp-сессию(й)")


@router.message_created(Command("status"))
async def cmd_status(event):
    users = sse.active_users()
    total = sse.connection_count()
    if not users:
        await event.answer("📭 Нет активных WebApp-сессий")
    else:
        lines = [f"📡 Активных WebApp-сессий: {total}"]
        for uid in users:
            n = sse.connection_count(uid)
            lines.append(f"  • user_id={uid}: {n} вкладка(ок)")
        await event.answer("\n".join(lines))


@router.message_created()
async def on_any_message(event):
    """Все обычные сообщения — пушим в WebApp как уведомление."""
    body = event.message.body
    text = getattr(body, "text", "") or ""
    if not text or text.startswith("/"):
        return

    sender = event.message.sender
    user_id = sender["user_id"]

    n = await sse.publish(
        user_id=user_id,
        event="chat_message",
        data={
            "text": text,
            "from": "user",
            "user_id": user_id,
        },
    )
    if n:
        logger.info(f"SSE push chat_message → user={user_id} connections={n}")


# ── API handlers ───────────────────────────────────────────────────────────────

async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({
        "ok": True,
        "service": "aioscam-webapp",
        "sse_users": sse.connection_count(),
    })


async def handle_me(request: web.Request) -> web.Response:
    """
    GET /api/me
    Возвращает профиль пользователя из initData (без обращения к API Max).
    """
    init_data = request["webapp_init_data"]
    user = init_data.user
    return web.json_response({
        "ok": True,
        "user": {
            "id":            user.id if user else None,
            "first_name":    user.first_name if user else None,
            "last_name":     user.last_name if user else None,
            "username":      user.username if user else None,
            "language_code": user.language_code if user else None,
            "photo_url":     user.photo_url if user else None,
        },
        "start_param":  init_data.start_param,
        "auth_date":    init_data.auth_date,
        "sse_active":   sse.connection_count(user.id) > 0 if user else False,
    })


async def handle_auth(request: web.Request) -> web.Response:
    """
    POST /api/auth
    Валидирует initData (middleware уже сделал это) и возвращает user.
    Используй при первом открытии WebApp для идентификации пользователя.
    """
    init_data = request["webapp_init_data"]
    user = init_data.user

    logger.info(f"Auth OK: user_id={user.id if user else 'none'} start_param={init_data.start_param!r}")

    return web.json_response({
        "ok": True,
        "user": {
            "id":            user.id if user else None,
            "first_name":    user.first_name if user else None,
            "last_name":     user.last_name if user else None,
            "username":      user.username if user else None,
            "language_code": user.language_code if user else None,
            "photo_url":     user.photo_url if user else None,
        },
        "start_param": init_data.start_param,
        "platform":    request.headers.get("X-Max-Platform"),
    })


async def handle_contact(request: web.Request) -> web.Response:
    """
    POST /api/contact
    Body: { phone, authDate, hash }  (от window.WebApp.requestContact())

    Двойная проверка:
    1. initData middleware уже проверил сессию
    2. Здесь проверяем хеш контакта (привязан к user_id из initData)
    """
    init_data = request["webapp_init_data"]

    if not init_data.user:
        return web.json_response({"ok": False, "error": "No user in initData"}, status=400)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    phone        = body.get("phone", "")
    auth_date    = body.get("authDate", "")
    contact_hash = body.get("hash", "")

    if not all([phone, auth_date, contact_hash]):
        return web.json_response(
            {"ok": False, "error": "Missing phone, authDate, or hash"}, status=400
        )

    try:
        contact = validate_contact(
            phone=phone,
            auth_date=auth_date,
            contact_hash=contact_hash,
            user_id=init_data.user.id,
            bot_token=BOT_TOKEN,
        )
    except WebAppSignatureError as exc:
        logger.warning(f"Contact signature invalid user_id={init_data.user.id}: {exc}")
        return web.json_response({"ok": False, "error": "Contact verification failed"}, status=401)
    except WebAppDataError as exc:
        logger.warning(f"Contact validation failed user_id={init_data.user.id}: {exc}")
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    logger.info(f"Contact validated: user_id={init_data.user.id} phone={contact.phone}")

    # Push в WebApp — подтверждение что контакт получен
    await sse.publish(
        user_id=init_data.user.id,
        event="contact_shared",
        data={"phone": contact.phone},
    )

    return web.json_response({"ok": True, "phone": contact.phone})


async def handle_send(request: web.Request) -> web.Response:
    """
    POST /api/send
    WebApp → Bot: отправляет сообщение через бота в чат пользователя.
    Body: { text, chat_id? }

    Это и есть WebApp→Bot канал: пользователь пишет из мини-приложения,
    бот доставляет сообщение в чат (или в указанный chat_id).
    """
    init_data = request["webapp_init_data"]
    if not init_data.user:
        return web.json_response({"ok": False, "error": "No user in initData"}, status=400)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    text = (body.get("text") or "").strip()
    if not text:
        return web.json_response({"ok": False, "error": "text is required"}, status=400)
    if len(text) > 4000:
        return web.json_response({"ok": False, "error": "text too long (max 4000)"}, status=400)

    user_id = init_data.user.id
    chat_id = body.get("chat_id", user_id)  # по умолчанию — личный диалог

    try:
        result = await bot.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=f"📱 [из мини-приложения]\n{text}",
        )
        logger.info(f"WebApp→Bot send: user_id={user_id} text={text!r:.50}")
    except Exception as exc:
        logger.error(f"Failed to send message: {exc}")
        return web.json_response({"ok": False, "error": "Failed to send message"}, status=500)

    # Пушим обратно в WebApp — подтверждение доставки
    await sse.publish(
        user_id=user_id,
        event="message_sent",
        data={"text": text, "ok": True},
    )

    return web.json_response({"ok": True, "mid": result.get("message", {}).get("body", {}).get("mid")})


async def handle_events(request: web.Request) -> web.Response:
    """
    GET /api/events
    SSE поток: Bot → WebApp push-уведомления в реальном времени.

    События:
      connected      — подключение установлено
      bot_message    — бот прислал сообщение (/echo)
      chat_message   — пользователь написал в чат
      contact_shared — контакт получен
      message_sent   — WebApp-сообщение доставлено

    Клиент (JS):
      const es = new EventSource('/api/events', {headers: {Authorization: 'MaxWebApp ...'}});
      es.addEventListener('bot_message', e => console.log(JSON.parse(e.data)));
    """
    init_data = request["webapp_init_data"]
    if not init_data.user:
        return web.json_response({"ok": False, "error": "No user in initData"}, status=400)

    user_id = init_data.user.id
    logger.info(f"SSE stream opened: user_id={user_id}")
    return await sse.stream(request, user_id=user_id)


# ── App factory ────────────────────────────────────────────────────────────────

@web.middleware
async def body_limit_middleware(request: web.Request, handler):
    """Reject requests with body > MAX_BODY bytes."""
    if request.content_length and request.content_length > MAX_BODY:
        return web.json_response(
            {"ok": False, "error": "Request body too large"}, status=413
        )
    return await handler(request)


@web.middleware
async def auth_log_middleware(request: web.Request, handler):
    """Log failed auth attempts."""
    response = await handler(request)
    if response.status == 401 and request.path.startswith("/api"):
        logger.warning(
            f"Auth failed: {request.method} {request.path} "
            f"from {request.headers.get('X-Real-IP', request.remote)}"
        )
    return response


def build_web_app() -> web.Application:
    app = web.Application(
        middlewares=[
            body_limit_middleware,
            auth_log_middleware,
            cors_middleware(allow_origins=[WEBAPP_ORIGIN]),
            WebAppMiddleware(bot_token=BOT_TOKEN, max_age=3600, fail_guard=fail_guard),
        ],
        client_max_size=MAX_BODY,
    )

    # Public — generic landing page at the bare domain root. Doesn't hint that
    # /api/* exists; works with no JS (plain "Open in Max" link).
    home = HomePage(bot, description="Демо-бот AioScam: двусторонняя связь Bot↔WebApp через SSE.")
    app.router.add_get("/", home.handler)
    app.router.add_get("/health", handle_health)

    # Protected — все проходят через WebAppMiddleware
    app.router.add_get ("/api/me",      handle_me)
    app.router.add_post("/api/auth",    handle_auth)
    app.router.add_post("/api/contact", handle_contact)
    app.router.add_post("/api/send",    handle_send)
    app.router.add_get ("/api/events",  handle_events)

    # Mini App frontend — served under WEBAPP_PATH, not the bare root, so a
    # plain visitor of WEBAPP_URL never sees the interactive demo or its asset
    # paths. Register WEBAPP_URL + WEBAPP_PATH (not bare WEBAPP_URL) as the
    # Mini App URL in the Max bot dashboard — that's the URL opened by the
    # OpenAppButton inside the Max client.
    if STATIC_DIR.is_dir():
        index_file = STATIC_DIR / "index.html"

        async def serve_index(request):
            return web.FileResponse(index_file)

        app.router.add_get(WEBAPP_PATH, serve_index)
        app.router.add_get(f"{WEBAPP_PATH}/", serve_index)
        app.router.add_static(WEBAPP_PATH, path=str(STATIC_DIR), name="static", show_index=False)
        logger.info(f"Serving Mini App frontend from {STATIC_DIR} at {WEBAPP_PATH}")

    return app


# ── Entry point ────────────────────────────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "MAX_BOT_TOKEN environment variable is not set.\n"
            "  export MAX_BOT_TOKEN=your_token_here\n"
            "or create a .env file with MAX_BOT_TOKEN=..."
        )

    # ── Register commands ──────────────────────────────────────────────────────
    await bot.set_my_commands([
        BotCommand(name="start",  description="Приветствие"),
        BotCommand(name="webapp", description="Открыть мини-приложение"),
        BotCommand(name="echo",   description="Эхо + push в WebApp"),
        BotCommand(name="status", description="Активные WebApp-сессии"),
    ])

    # ── Probe and report capabilities ─────────────────────────────────────────
    caps = await BotCapabilities.probe(
        bot=bot,
        webapp_url=WEBAPP_URL if WEBAPP_URL != "https://your-app.example.com" else None,
    )
    caps.log_report(logger)

    logger.info(f"API server: http://0.0.0.0:{API_PORT}")

    dp.include_router(router)

    web_app = build_web_app()
    runner  = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()

    logger.info("Ready.")
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
