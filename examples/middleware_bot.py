"""
Middleware Bot — two patterns for writing middleware

DEMONSTRATES
────────────
  • @router.middleware() decorator   — function-style, quick to write
  • BaseMiddleware class             — reusable, testable, injectable
  • router.add_middleware(instance)  — register a class-based middleware
  • StateGuardMiddleware             — built-in guard for FSM flows
  • Middleware execution order       — outer→inner on enter, inner→outer on exit

COMMANDS
────────
  /start  — trigger all middleware (logging + timing)
  /slow   — 2-second sleep to see timing middleware in action
  /error  — raise an intentional exception to see error middleware

VISUAL IN MAX MESSENGER
───────────────────────
  /start → bot replies "👋 Привет! Я бот с middleware."
           console shows: [LOG] Received → [TIMING] 0.002s
  /slow  → 2-second pause, then "⏳ Готово!" (timing shows ~2.001s)
  /error → error middleware catches exception, bot replies with error details

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python middleware_bot.py

HOW MIDDLEWARE WORKS
────────────────────
  Each middleware wraps the next handler:

    async def my_middleware(event, handler):
        # runs BEFORE the handler
        result = await handler(event)
        # runs AFTER the handler
        return result

  Middleware is executed in registration order (first registered = outermost).
  Multiple middleware form a chain: MW1 → MW2 → MW3 → handler.
"""

import asyncio
import logging
import time

from aioscam import Bot, Dispatcher, Router, Command, BotCommand
from aioscam.middleware.base import BaseMiddleware
from aioscam.middleware.manager import StateGuardMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Pattern 1: decorator style ────────────────────────────────────────────────
#
# @router.middleware() turns a plain async function into middleware.
# Best for simple, one-off middleware that doesn't need configuration.

@router.middleware()
async def logging_middleware(event, handler):
    """Log every event before and after it is handled."""
    event_type = type(event.event).__name__ if hasattr(event, "event") else type(event).__name__
    logger.info("[LOG] Received event: %s", event_type)
    result = await handler(event)
    logger.info("[LOG] Event handled: %s", event_type)
    return result


@router.middleware()
async def timing_middleware(event, handler):
    """Measure how long each handler takes to execute."""
    start = time.perf_counter()
    result = await handler(event)
    elapsed = time.perf_counter() - start
    logger.info("[TIMING] Handler executed in %.3fs", elapsed)
    return result


# ── Pattern 2: class-based (BaseMiddleware) ───────────────────────────────────
#
# Subclass BaseMiddleware for middleware that:
#   - needs constructor arguments (config, dependencies)
#   - should be testable in isolation
#   - is shared across multiple routers

class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Catch unhandled exceptions in any handler and reply with a user-friendly
    error message instead of silently failing.

    Class-based middleware receives its configuration via __init__.
    """

    def __init__(self, notify_user: bool = True):
        self.notify_user = notify_user

    async def __call__(self, event, handler):
        try:
            return await handler(event)
        except Exception as exc:
            logger.exception("[ERROR] Unhandled exception in handler: %s", exc)
            if self.notify_user:
                try:
                    await event.answer(
                        f"❌ Внутренняя ошибка бота\n\n"
                        f"Тип: `{type(exc).__name__}`\n"
                        f"Сообщение: `{exc}`"
                    )
                except Exception:
                    pass  # if we can't reply, just log it


# Register the class-based middleware via add_middleware()
router.add_middleware(ErrorHandlerMiddleware(notify_user=True))

# ── Pattern 3: StateGuardMiddleware (built-in) ────────────────────────────────
#
# Guards FSM-active users from typing unrelated commands.
# Register AFTER other middleware so it runs closest to the handler.
#
# Uncomment to enable:
#
# router.add_middleware(StateGuardMiddleware(hints={
#     "MyState:waiting_name": "ваше имя",
# }))

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """Simple reply to demonstrate middleware chain execution."""
    await event.answer("👋 Привет! Я бот с middleware.")


@router.message_created(Command("slow"))
async def cmd_slow(event):
    """Sleep 2 seconds — visible in timing_middleware output."""
    await asyncio.sleep(2)
    await event.answer("⏳ Готово! Это заняло 2 секунды.")


@router.message_created(Command("error"))
async def cmd_error(event):
    """Raise an exception — ErrorHandlerMiddleware catches it and replies."""
    raise RuntimeError("Это намеренная тестовая ошибка!")


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start", description="Приветствие (все middleware в действии)"),
        BotCommand(name="slow",  description="Медленный хэндлер — видно в timing middleware"),
        BotCommand(name="error", description="Намеренная ошибка — ErrorHandlerMiddleware поймает"),
    ])
    logger.info("Middleware bot started | /start /slow /error")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
