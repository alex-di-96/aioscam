"""
Rate Limiter Example

Demonstrates centralized rate limiting to prevent API bans.
All requests pass through the limiter automatically.
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.limiter import RateLimitConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Show rate limit info"""
    await event.answer(
        "🚦 **Rate Limiter Demo**\n\n"
        "Все запросы проходят через централизованный лимитер.\n"
        "Это защищает от банов при частых вызовах API.\n\n"
        "📊 Конфигурация:\n"
        "• Скорость: 5 запросов/сек\n"
        "• Пик: 10 запросов\n"
        "• Макс повторов при 429: 5\n"
        "• Экспоненциальный backoff\n\n"
        "Попробуйте /burst чтобы отправить 10 сообщений подряд."
    )


@router.message_created(Command("burst"))
async def cmd_burst(event):
    """Send multiple messages to demonstrate rate limiting"""
    messages = [
        "📨 Сообщение 1/10",
        "📨 Сообщение 2/10",
        "📨 Сообщение 3/10",
        "📨 Сообщение 4/10",
        "📨 Сообщение 5/10",
        "📨 Сообщение 6/10",
        "📨 Сообщение 7/10",
        "📨 Сообщение 8/10",
        "📨 Сообщение 9/10",
        "📨 Сообщение 10/10 — Готово!",
    ]

    await event.answer("⏳ Отправляю 10 сообщений...")

    import time
    start = time.monotonic()

    for i, text in enumerate(messages, 1):
        await event.answer(text)
        logging.info(f"Sent message {i}/10")

    elapsed = time.monotonic() - start
    await event.answer(
        f"✅ Отправлено 10 сообщений за {elapsed:.2f}с\n\n"
        f"Без лимитера это было бы мгновенно (и привело бы к бану).\n"
        f"С лимитером: 5 запросов/сек, автоматически."
    )


@router.message_created(Command("strict"))
async def cmd_strict(event):
    """Show strict mode config"""
    cfg = RateLimitConfig.strict()
    await event.answer(
        f"🔒 **Strict Mode**\n\n"
        f"• rate: {cfg.rate} req/s\n"
        f"• burst: {cfg.burst}\n"
        f"• max_retries: {cfg.max_retries}\n"
        f"• backoff_base: {cfg.backoff_base}с\n\n"
        f"Идеально для продакшена."
    )


# Include router
dp.include_router(router)


async def main():
    """Main function"""
    # Bot with strict rate limiting (5 req/s, burst 10, 5 retries)
    bot = Bot(rate_limit=RateLimitConfig.strict())

    logging.info("Bot started with strict rate limiting")
    logging.info("Rate: 5 req/s, Burst: 10, Max retries: 5")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
