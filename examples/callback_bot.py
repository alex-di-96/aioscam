"""
Callback Bot — detailed send_callback() API patterns

DEMONSTRATES
────────────
  • bot.send_callback()           — acknowledge callback with text reply
  • bot.send_callback(notification=) — show a popup notification
  • bot.send_callback() no args   — dismiss spinner silently
  • event.answer()                — sends a regular chat message (NOT callback ack)

COMMANDS
────────
  /start  — inline keyboard with 3 callback buttons
  /help   — explain the difference between send_callback and event.answer

VISUAL IN MAX MESSENGER
───────────────────────
  /start → message with 3 inline buttons
  "ℹ️ Ответ текстом"       → spinner dismisses, bot replies with text
  "🔔 Ответ + уведомление" → spinner dismisses + popup notification appears
  "⏹️ Только закрыть"      → spinner dismisses silently (no message)

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python callback_bot.py

IMPORTANT
─────────
  Max API endpoint: POST https://botapi.max.ru/answers
  Auth: Authorization header (not access_token query param — deprecated)
  Body: {"message": {"text": "..."}, "notification": "..."}

  bot.send_callback() wraps this endpoint correctly.
  Calling event.answer() instead sends a NEW chat message and leaves
  the button in the loading/spinner state.
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command, BotCommand
from aioscam.utils.keyboard import KeyboardBuilder

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()


# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """Show inline keyboard to demonstrate all three send_callback patterns."""
    logger.info("cmd_start: user=%s", getattr(event.from_user, "user_id", "?"))
    builder = KeyboardBuilder(inline=True)
    builder.callback("ℹ️ Ответ текстом", "cb:message")
    builder.callback("🔔 Ответ + уведомление", "cb:notify")
    builder.row()
    builder.callback("⏹️ Только закрыть", "cb:close")

    await event.answer(
        "🔘 **Callback Demo**\n\n"
        "Нажмите кнопку — бот ответит через `bot.send_callback()`.\n\n"
        "• `message=` — текстовый ответ в чате\n"
        "• `notification=` — всплывающий попап\n"
        "• без аргументов — просто закрыть спиннер",
        keyboard=builder.build().to_dict(),
    )


@router.callback_query()
async def handle_callback(event):
    """
    Handle button clicks.

    send_callback(callback_id, message=, notification=) covers three patterns:
      1. message only     — reply text appears in the chat
      2. notification     — short popup toast shown to the user
      3. neither          — spinner dismissed silently
    """
    callback_data = event.callback_data or ""
    callback_id = event.callback_id
    logger.info("callback: data=%r  id=%s", callback_data, callback_id)

    if callback_data == "cb:message":
        await event.bot.send_callback(
            callback_id=callback_id,
            message="ℹ️ Это текстовый ответ на callback.",
        )

    elif callback_data == "cb:notify":
        await event.bot.send_callback(
            callback_id=callback_id,
            message="🔔 Сообщение в чате.",
            notification="Это всплывающий попап!",
        )

    elif callback_data == "cb:close":
        # No message or notification — spinner dismissed silently.
        await event.bot.send_callback(callback_id=callback_id)

    else:
        await event.bot.send_callback(
            callback_id=callback_id,
            message=f"🔘 Получен callback: {callback_data}",
        )


@router.message_created(Command("help"))
async def cmd_help(event):
    """Explain the API difference between send_callback and event.answer."""
    await event.answer(
        "📖 **Callback API**\n\n"
        "**bot.send_callback()** — подтверждает нажатие кнопки:\n"
        "```python\n"
        "await bot.send_callback(\n"
        "    callback_id=event.callback_id,\n"
        "    message='Текст ответа',      # опционально\n"
        "    notification='Попап',         # опционально\n"
        ")\n"
        "```\n\n"
        "**event.answer()** — отправляет обычное сообщение в чат.\n"
        "Используй его для /команд, но НЕ для ответа на callback.\n\n"
        "URL: `botapi.max.ru/answers`\n"
        "Auth: `Authorization` header"
    )


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start", description="Показать кнопки с callback"),
        BotCommand(name="help",  description="Объяснение send_callback vs answer"),
    ])
    logger.info("Callback bot started | /start /help")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
