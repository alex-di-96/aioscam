"""
Webhook example — aiohttp + secret token + proper signal shutdown

Demonstrates:
- AiohttpWebhookHandler with secret token validation
- Signal-based graceful shutdown (SIGINT / SIGTERM)
- Webhook subscribe/unsubscribe lifecycle
"""

import asyncio
import logging
import os
import signal

from aiohttp import web

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.webhook import AiohttpWebhookHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration (all from env) ─────────────────────────────────────────────
HOST          = os.getenv("HOST", "0.0.0.0")
PORT          = int(os.getenv("PORT", "8080"))
WEBHOOK_PATH  = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL   = os.getenv("WEBHOOK_URL", f"https://your-domain.com{WEBHOOK_PATH}")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # optional but recommended

# ── Bot setup ────────────────────────────────────────────────────────────────
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("👋 Бот работает в режиме Webhook!")


@router.message_created(Command("info"))
async def cmd_info(event):
    await event.answer(
        f"📊 Режим: Webhook\n"
        f"🔗 URL: {WEBHOOK_URL}\n"
        f"🖥️ Хост: {HOST}:{PORT}\n"
        f"🔒 Secret: {'да' if WEBHOOK_SECRET else 'нет'}"
    )


@router.message_created()
async def echo(event):
    if event.message and event.message.has_text:
        await event.answer(f"🔁 {event.text}")


dp.include_router(router)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    bot = Bot()

    # Webhook handler — validates X-Max-Secret-Token when secret_token is set
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

    # Subscribe to webhook before starting server
    logger.info(f"Subscribing to webhook: {WEBHOOK_URL}")
    await bot.subscribe_webhook(WEBHOOK_URL)

    # Signal-based graceful shutdown (works with Ctrl+C and systemd SIGTERM)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _on_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except (NotImplementedError, RuntimeError):
            pass  # Windows

    try:
        await site.start()
        logger.info(f"Webhook server running on http://{HOST}:{PORT}{WEBHOOK_PATH}")
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
