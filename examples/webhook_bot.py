"""
Webhook Bot — production-ready webhook server with aiohttp

DEMONSTRATES
────────────
  • AiohttpWebhookHandler           — aiohttp-based webhook receiver
  • secret_token validation         — X-Max-Secret-Token header check
  • bot.subscribe_webhook(url)      — register webhook with Max API
  • bot.unsubscribe_webhook(url)    — deregister on shutdown
  • signal-based graceful shutdown  — SIGINT / SIGTERM (works with systemd)

COMMANDS
────────
  /start  — confirm webhook mode is active
  /info   — show webhook URL and server host/port

VISUAL IN MAX MESSENGER
───────────────────────
  /start → "👋 Бот работает в режиме Webhook!"
  /info  → shows configured WEBHOOK_URL, HOST:PORT, and whether secret is set

SETUP
─────
  # Set environment variables (required: WEBHOOK_URL must be publicly reachable)
  export MAX_BOT_TOKEN=your_token_here
  export WEBHOOK_URL=https://your-domain.com/webhook
  export WEBHOOK_SECRET=your_secret   # optional but recommended
  export HOST=0.0.0.0                 # default
  export PORT=8080                    # default

  python webhook_bot.py

POLLING vs WEBHOOK
──────────────────
  Polling  — bot calls Max API every N seconds to fetch updates.
             Simple to run locally, no public URL needed.
             Use dp.start_polling(bot) — see echo_bot.py.

  Webhook  — Max API pushes updates to your HTTPS URL.
             Requires a public server and a valid TLS certificate.
             Lower latency, preferred for production.

SECRET TOKEN
────────────
  When WEBHOOK_SECRET is set, AiohttpWebhookHandler rejects any request that
  does not include the matching X-Max-Secret-Token header.
  This prevents unauthorized parties from injecting fake updates.
"""

import asyncio
import logging
import os
import signal

from aiohttp import web

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.webhook import AiohttpWebhookHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration (all from environment) ─────────────────────────────────────

HOST           = os.getenv("HOST", "0.0.0.0")
PORT           = int(os.getenv("PORT", "8080"))
WEBHOOK_PATH   = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", f"https://your-domain.com{WEBHOOK_PATH}")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("👋 Бот работает в режиме Webhook!")


@router.message_created(Command("info"))
async def cmd_info(event):
    await event.answer(
        f"📊 **Webhook Info**\n\n"
        f"🔗 URL:     `{WEBHOOK_URL}`\n"
        f"🖥️ Server: `{HOST}:{PORT}`\n"
        f"🔒 Secret:  {'✅ да' if WEBHOOK_SECRET else '❌ нет'}"
    )


@router.message_created()
async def echo(event):
    if event.message and event.message.has_text:
        await event.answer(f"🔁 {event.text}")


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()

    # AiohttpWebhookHandler validates X-Max-Secret-Token when secret_token is set.
    # Any request without the correct token returns HTTP 401.
    webhook_handler = AiohttpWebhookHandler(
        bot, dp,
        path=WEBHOOK_PATH,
        secret_token=WEBHOOK_SECRET or None,
    )

    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, webhook_handler.handle)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)

    logger.info("Subscribing to webhook: %s", WEBHOOK_URL)
    await bot.subscribe_webhook(WEBHOOK_URL)

    # Graceful shutdown on SIGINT (Ctrl+C) and SIGTERM (systemd stop)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _on_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except (NotImplementedError, RuntimeError):
            pass  # Windows does not support add_signal_handler

    try:
        await site.start()
        logger.info("Webhook server listening on http://%s:%s%s", HOST, PORT, WEBHOOK_PATH)
        await stop_event.wait()
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, RuntimeError):
                pass
        logger.info("Unsubscribing webhook...")
        await bot.unsubscribe_webhook(url=WEBHOOK_URL)
        await runner.cleanup()
        await bot.close()
        logger.info("Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
