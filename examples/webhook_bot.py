"""
Webhook example

This example demonstrates how to run bot in webhook mode with aiohttp.
"""

import asyncio
import logging
import os
from aiohttp import web
from aioscam import Bot, Dispatcher, Router, Command
from aioscam.webhook import AiohttpWebhookHandler

# Setup logging
logging.basicConfig(level=logging.INFO)

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://your-domain.com{WEBHOOK_PATH}")

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Handle /start command"""
    await event.answer("👋 Бот работает в режиме Webhook!")


@router.message_created(Command("info"))
async def cmd_info(event):
    """Show bot info"""
    await event.answer(
        "📊 Информация:\n"
        f"🌐 Режим: Webhook\n"
        f"🔗 URL: {WEBHOOK_URL}\n"
        f"🖥️ Хост: {HOST}:{PORT}"
    )


@router.message_created()
async def echo(event):
    """Echo messages"""
    if event.message.has_text:
        await event.answer(f"🔁 {event.text}")


# Include router into dispatcher
dp.include_router(router)


async def main():
    """Main function"""
    # Create bot
    bot = Bot()
    
    # Create aiohttp application
    app = web.Application()
    
    # Setup webhook handler
    webhook_handler = AiohttpWebhookHandler(bot, dp, path=WEBHOOK_PATH)
    app.router.add_post(WEBHOOK_PATH, webhook_handler.handle)
    
    # Subscribe to webhook
    logging.info("Subscribing to webhook...")
    await bot.subscribe_webhook(WEBHOOK_URL)
    
    # Setup and run server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    
    logging.info(f"Starting webhook server on {HOST}:{PORT}")
    
    try:
        await site.start()
        # Keep running
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Bot stopped")
    finally:
        await bot.unsubscribe_webhook()
        await runner.cleanup()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
