"""
Rate Limited Bot — protect against Max API bans with token-bucket rate limiting

DEMONSTRATES
────────────
  • RateLimitConfig               — configure rate, burst, retry behaviour
  • RateLimitConfig.strict()      — preset for production (5 req/s, burst 10)
  • Bot(rate_limit=config)        — enable limiter for all API calls
  • RetryAfter handling           — auto-retry on HTTP 429 with backoff
  • Burst behaviour               — how the token bucket absorbs a spike

COMMANDS
────────
  /start   — show current rate limit configuration
  /burst   — send 10 messages in a row to demonstrate rate limiting
  /strict  — show the strict() preset values

VISUAL IN MAX MESSENGER
───────────────────────
  /burst → bot sends 10 messages sequentially; with rate=5/s and burst=10
           first 10 messages go immediately (burst allows it), then it throttles.
           Without a limiter the same burst could trigger a 429 ban.
  /strict → shows: rate=5/s, burst=10, max_retries=5, backoff_base=1.0s

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python rate_limited_bot.py

HOW THE RATE LIMITER WORKS
──────────────────────────
  Token bucket algorithm:
    - Bucket starts with `burst` tokens.
    - Each API request consumes 1 token.
    - Tokens refill at `rate` per second.
    - If the bucket is empty, the call waits for a token.

  429 retry:
    - On HTTP 429 (Too Many Requests), the limiter waits `retry_after`
      seconds (from API response) or falls back to exponential backoff.
    - After `max_retries` failed attempts it raises RetryAfter.
"""

import asyncio
import logging
import time

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.limiter import RateLimitConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """Show current rate limit settings."""
    await event.answer(
        "🚦 **Rate Limiter Demo**\n\n"
        "Все запросы к Max API проходят через лимитер.\n\n"
        "📊 Конфигурация (strict):\n"
        "• rate: 5 запросов/сек\n"
        "• burst: 10 (пиковый запас)\n"
        "• max_retries при 429: 5\n"
        "• exponential backoff\n\n"
        "/burst  — отправить 10 сообщений подряд\n"
        "/strict — показать все параметры strict() пресета"
    )


@router.message_created(Command("burst"))
async def cmd_burst(event):
    """
    Send 10 messages in rapid succession.

    With burst=10 and rate=5/s, the first 10 messages are sent immediately
    (using all burst tokens). From message 11 onward the limiter throttles
    to 5/s. This prevents the 429 ban that a plain loop would trigger.
    """
    await event.answer("⏳ Отправляю 10 сообщений...")

    start = time.monotonic()
    for i in range(1, 11):
        await event.answer(f"📨 Сообщение {i}/10")
        logger.info("Sent message %d/10", i)

    elapsed = time.monotonic() - start
    await event.answer(
        f"✅ Готово! Отправлено за {elapsed:.2f}с\n\n"
        f"Лимитер автоматически регулирует скорость,\n"
        f"защищая от банов за слишком частые запросы."
    )


@router.message_created(Command("strict"))
async def cmd_strict(event):
    """Show all values in the strict() preset."""
    cfg = RateLimitConfig.strict()
    await event.answer(
        f"🔒 **RateLimitConfig.strict()**\n\n"
        f"• rate:         {cfg.rate} req/s\n"
        f"• burst:        {cfg.burst}\n"
        f"• max_retries:  {cfg.max_retries}\n"
        f"• backoff_base: {cfg.backoff_base}s\n"
        f"• backoff_max:  {cfg.backoff_max}s\n"
        f"• retry_429:    {cfg.retry_429}\n\n"
        f"Рекомендуется для продакшена."
    )


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    # Pass rate_limit to Bot — all API calls go through the limiter automatically.
    bot = Bot(rate_limit=RateLimitConfig.strict())
    logger.info("Rate-limited bot started | /start /burst /strict")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
