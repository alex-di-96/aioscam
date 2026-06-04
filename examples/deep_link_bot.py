"""
Deep Link Bot — personal invite links via Max deep link API

DEMONSTRATES
────────────
  • create_deep_link(username, payload)       — https://max.ru/<bot>?start=<payload>
  • create_group_deep_link(username, gid, p)  — add bot to a group with payload
  • parse_deep_link(url)                      — extract bot_username, payload, group_id
  • StartCommand() filter                     — catches ?start= payload on bot_started
  • bot_started event                         — fired once when user opens the bot

COMMANDS
────────
  /start  — show invite link button (or handle deep link payload if present)
  /link   — generate your personal referral link
  /group  — show how a group deep link looks

VISUAL IN MAX MESSENGER
───────────────────────
  User opens bot normally:
    /start → "Нажми кнопку → получи персональную ссылку"

  User clicks "📤 Пригласить друга":
    → bot sends a link: https://max.ru/<bot>?start=ref_<user_id>

  Friend opens that link (bot_started with payload "ref_<id>"):
    → "Вас пригласил пользователь ID: <id>"

  Repeated deep link click (arrives as /start <payload> message):
    → same welcome handled by StartCommand filter

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python deep_link_bot.py

HOW DEEP LINKS WORK IN MAX
──────────────────────────
  First visit:  Max fires bot_started event with event.payload = "<payload>"
  Return visit: Max sends a message "/start <payload>"; handled via StartCommand()
  Group link:   https://max.ru/<bot>?add_to_group=<gid>&start=<payload>
                User is prompted to add the bot to group <gid>.
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, StartCommand, Command
from aioscam.enums import ParseMode
from aioscam.utils.deep_linking import create_deep_link, create_group_deep_link, parse_deep_link
from aioscam.utils.keyboard import KeyboardBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.bot_started()
async def on_bot_started(event):
    """
    Fired ONCE when a user opens the bot for the first time (or after a long pause).

    event.payload contains the ?start= query parameter from the deep link URL,
    or None if the user opened the bot directly.
    """
    if event.payload:
        await _handle_deep_link_payload(event, event.payload)
    else:
        # Regular /start without deep link
        kb = _invite_keyboard()
        await event.bot.send_message(
            chat_id=event.chat_id or event.user_id,
            text="👋 Привет! Я демо-бот диплинков.\n\nНажми кнопку — получи свою персональную ссылку.",
            keyboard=kb.to_dict(),
        )


@router.message_created(StartCommand())
async def on_start_with_deeplink(event):
    """
    Handles repeated deep link visits.

    After the first visit (bot_started), subsequent deep link clicks arrive as
    a plain message "/start <payload>". StartCommand() catches this pattern and
    exposes the payload via event.payload or the `start_payload` kwarg.
    """
    payload = event.payload or ""
    if payload:
        await _handle_deep_link_payload(event, payload)
    else:
        await cmd_start(event)


@router.message_created(Command("start"))
async def cmd_start(event):
    """Plain /start without a deep link payload."""
    kb = _invite_keyboard()
    await event.answer(
        "👋 Привет!\n\n"
        "Нажми кнопку чтобы получить свою ссылку-приглашение.\n"
        "Когда друг перейдёт по ней — бот узнает, кто его пригласил.",
        keyboard=kb.to_dict(),
    )


@router.message_created(Command("link"))
async def cmd_link(event):
    """
    Generate the user's personal referral link.

    create_deep_link() URL-encodes the payload automatically,
    so any characters (spaces, unicode, special symbols) are safe.
    """
    bot_info = await event.bot.get_me()
    bot_username = bot_info.get("username", "your_bot")
    user_id = event.user_id or 0

    # Payload format is up to you — here we use "ref_<user_id>"
    link = create_deep_link(bot_username, f"ref_{user_id}")

    # Also show how to parse it back
    parsed = parse_deep_link(link)

    await event.answer(
        f"🔗 **Твоя ссылка:**\n`{link}`\n\n"
        f"Поделись ей — я узнаю, кто её передал.\n\n"
        f"parse_deep_link() вернёт:\n"
        f"• bot_username: `{parsed['bot_username']}`\n"
        f"• payload: `{parsed['payload']}`"
    )


@router.message_created(Command("group"))
async def cmd_group(event):
    """
    Demonstrate create_group_deep_link().

    This link type prompts the user to add the bot to a specific group.
    The optional payload is delivered to the bot_added event.
    """
    bot_info = await event.bot.get_me()
    bot_username = bot_info.get("username", "your_bot")
    example_group_id = 123456789

    # Without payload
    link_plain = create_group_deep_link(bot_username, example_group_id)
    # With payload (URL-encoded automatically)
    link_with_payload = create_group_deep_link(bot_username, example_group_id, "invite_from_admin")

    await event.answer(
        "**Ссылки для добавления бота в группу:**\n\n"
        f"Без payload:\n`{link_plain}`\n\n"
        f"С payload:\n`{link_with_payload}`\n\n"
        f"Когда пользователь открывает такую ссылку,\n"
        f"Max предлагает добавить бота в группу #{example_group_id}."
    )


# ── Callback ──────────────────────────────────────────────────────────────────

@router.callback_query()
async def handle_callback(event):
    """Handle 'get_invite_link' button click — generate and send personal link."""
    if event.callback_data != "get_invite_link":
        await event.bot.send_callback(callback_id=event.callback_id)
        return

    bot_info = await event.bot.get_me()
    bot_username = bot_info.get("username", "your_bot")
    user_id = event.user_id or 0

    link = create_deep_link(bot_username, f"ref_{user_id}")

    await event.bot.send_callback(callback_id=event.callback_id)
    await event.answer(
        f"📬 **Твоя персональная ссылка:**\n\n"
        f"`{link}`\n\n"
        f"Поделись с друзьями!\n"
        f"Я узнаю, что их пригласил ты (ID: {user_id})."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _handle_deep_link_payload(event, payload: str) -> None:
    """Parse and respond to a deep link payload."""
    referrer_id = None
    if payload.startswith("ref_"):
        referrer_id = payload[4:]

    if referrer_id:
        text = (
            f"🎉 Добро пожаловать!\n\n"
            f"Вас пригласил пользователь с ID: **{referrer_id}**\n\n"
            f"_payload: `{payload}`_"
        )
    else:
        text = (
            f"🔗 Вы перешли по диплинку!\n\n"
            f"payload: `{payload}`\n\n"
            f"Это может быть промокод, реферальная ссылка и т.д."
        )

    chat_id = event.chat_id or event.user_id
    await event.bot.send_message(chat_id=chat_id, text=text)


def _invite_keyboard() -> KeyboardBuilder:
    kb = KeyboardBuilder(inline=True)
    kb.callback("📤 Пригласить друга", "get_invite_link")
    return kb


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot(parse_mode=ParseMode.MARKDOWN)
    me = await bot.get_me()
    bot_username = me.get("username", "your_bot")
    logger.info("Deep link bot started: @%s", bot_username)
    logger.info("Example deep link: https://max.ru/%s?start=ref_12345", bot_username)
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
