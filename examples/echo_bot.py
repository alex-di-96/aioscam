"""
Echo Bot — basic bot skeleton

DEMONSTRATES
────────────
  • Bot, Dispatcher, Router              (aioscam)
  • Command filter                       (aioscam.Command)
  • F.text magic filter                  (magic_filter.F)
  • SenderAction (typing indicator)      (aioscam.enums.SenderAction)
  • TextFormat formatting utilities      (aioscam.utils.formatting)
  • event.answer() shortcut
  • Handler registration order matters:
    specific filters BEFORE the catch-all handler

COMMANDS
────────
  /start   — welcome message with formatting examples
  /help    — list of commands
  /fmt     — TextFormat showcase (bold, italic, code, mention, link)
  <text>   — echo (any message)
  "привет" — special greeting reply

VISUAL IN MAX MESSENGER
───────────────────────
  /start → bot replies with a styled welcome message
  /fmt   → bot shows bold/italic/code/link/mention rendering
  "привет world" → bot replies "👋 Привет! Как дела?"
  any text → bot shows ✍️ typing indicator then echoes the message

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python echo_bot.py
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command, F
from aioscam.enums import SenderAction
from aioscam.utils.formatting import Bold, Italic, Code, Pre, Link, Mention

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """Welcome message — shows that Markdown formatting works."""
    await event.answer(
        f"{Bold('AioScam Echo Bot')}\n\n"
        "Отправь мне любое сообщение — я повторю его!\n\n"
        f"Попробуй: {Code('/fmt')} чтобы увидеть примеры форматирования."
    )


@router.message_created(Command("help"))
async def cmd_help(event):
    """Help text with available commands."""
    await event.answer(
        f"{Bold('Команды')}\n\n"
        "/start — приветствие\n"
        "/help  — эта справка\n"
        "/fmt   — демо форматирования\n\n"
        "Или просто напиши что-нибудь — я повторю!"
    )


@router.message_created(Command("fmt"))
async def cmd_fmt(event):
    """
    TextFormat showcase.

    TextFormat is a utility class in aioscam.utils.formatting that generates
    Markdown strings. These are rendered by Max Messenger when the message is
    sent with format=ParseMode.MARKDOWN (the default).
    """
    lines = [
        f"{Bold('Жирный')} — Bold(text)",
        f"{Italic('Курсив')} — Italic(text)",
        f"{Code('inline код')} — Code(text)",
        f"{Link('Ссылка', 'https://max.ru')} — Link(text, url)",
        f"{Mention('Упоминание', 12345)} — Mention(name, user_id)",
        "",
        "Блок кода:",
        Pre("result = await bot.get_me()", language="python"),
    ]
    await event.answer("\n".join(lines))


# NOTE: specific filters MUST come BEFORE the catch-all handler.
# If echo_message() were placed here first, it would match every message
# and the "привет" handler below would never be reached.

@router.message_created(F.text.func(lambda t: "привет" in t.lower()))
async def handle_hello(event):
    """Catch messages that contain 'привет' (any case)."""
    await event.answer("👋 Привет! Как дела?")


@router.message_created()
async def echo_message(event):
    """
    Catch-all handler — echoes any text message.

    SenderAction.TYPING shows a '✍️ typing...' indicator in the chat
    before the bot replies. Max API ignores the request gracefully if
    the chat_id is not reachable.
    """
    if not event.message or not event.message.has_text:
        return

    # Show typing indicator
    await event.bot.send_action(event.chat_id, SenderAction.TYPING)

    await event.answer(f"🔁 {event.text}")


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    # Token is read from MAX_BOT_TOKEN environment variable automatically.
    bot = Bot()
    logger.info("Echo bot started. Send /start in Max Messenger.")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
