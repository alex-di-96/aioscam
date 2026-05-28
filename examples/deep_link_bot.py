"""
Deep Link Demo Bot

Demonstrates how to handle deep links: https://max.ru/<botName>?start=<payload>

Usage:
    1. Bot receives a deep link payload when user starts the bot via link
    2. StartCommand filter catches the payload
    3. Bot shows who invited the user

Example deep links:
    https://max.ru/my_bot?start=ref_12345
    https://max.ru/my_bot?start=promo_summer2026
"""

import asyncio
import os
from dotenv import load_dotenv

from aioscam import Bot, Dispatcher, Router, StartCommand, Command, F
from aioscam.enums import ParseMode
from aioscam.utils.deep_linking import create_deep_link
from aioscam.utils.keyboard import KeyboardBuilder

load_dotenv()

router = Router()


@router.bot_started()
async def on_bot_started(event):
    """Handle bot_started event (user opens bot dialog)"""
    user_id = event.user_id or "unknown"
    chat_id = event.chat_id or user_id

    # Check if this is a deep link (has payload)
    if event.payload:
        await handle_deep_link(event, user_id, chat_id)
    else:
        # Regular start without deep link
        await event.bot.send_message(
            chat_id=chat_id,
            text="👋 Привет! Я демо-бот диплинков.\n\n"
                 "Нажми кнопку ниже чтобы получить персональную ссылку-приглашение!",
            keyboard=_invite_keyboard().to_dict(),
        )


async def handle_deep_link(event, user_id, chat_id):
    """Process deep link payload"""
    payload = event.payload

    # Parse referrer from payload (format: ref_<user_id>)
    referrer_id = None
    if payload.startswith("ref_"):
        referrer_id = payload[4:]

    if referrer_id:
        text = (
            f"🎉 Добро пожаловать!\n\n"
            f"Вас пригласил пользователь с ID: {referrer_id}\n\n"
            f"Payload диплинка: {payload}"
        )
    else:
        text = (
            f"🔗 Вы перешли по диплинку!\n\n"
            f"Payload: {payload}\n\n"
            f"Это может быть промокод, реферальная ссылка и т.д."
        )

    await event.bot.send_message(
        chat_id=chat_id,
        text=text,
    )


@router.message_created(StartCommand())
async def on_start_with_deeplink(event, start_payload: str = None):
    """
    Handle /start <payload> sent as a message on repeat deeplink visits.
    Max API sends bot_started only once; subsequent deeplink clicks arrive here.
    """
    user_id = event.user_id or (event.from_user.id if event.from_user else "unknown")
    chat_id = event.chat_id or user_id
    payload = start_payload or event.payload or ""
    await handle_deep_link(event, user_id, chat_id)


@router.message_created(Command("start"))
async def on_start(event):
    """Handle plain /start command (no deeplink payload)"""
    user_id = event.user_id or (event.from_user.id if event.from_user else "unknown")
    chat_id = event.chat_id or user_id

    await event.bot.send_message(
        chat_id=chat_id,
        text="👋 Привет!\n\n"
             "Нажми кнопку ниже чтобы получить персональную ссылку-приглашение.\n"
             "Когда кто-то перейдёт по ней — бот узнает кто пригласил!",
        keyboard=_invite_keyboard().to_dict(),
    )


@router.message_created(Command("help"))
async def on_help(event):
    """Handle /help command"""
    chat_id = event.chat_id or event.user_id
    await event.bot.send_message(
        chat_id=chat_id,
        text="**Демо диплинков**\n\n"
             "/start — начать работу\n"
             "/help — эта справка\n\n"
             "Используй кнопку 'Пригласить друга' для создания персональной ссылки.",
        format="markdown",
    )


@router.message_callback(F.callback.data.startswith("get_invite_link"))
async def on_get_invite_link(event):
    """Generate personal invite link"""
    user_id = event.user_id or (event.from_user.id if event.from_user else 0)
    bot_info = await event.bot.get_me()
    bot_username = bot_info.get("username", "my_bot")

    # Create deep link with user's ID as payload
    invite_link = create_deep_link(bot_username, f"ref_{user_id}")

    await event.bot.send_message(
        chat_id=event.chat_id or user_id,
        text=f"📬 Твоя персональная ссылка:\n\n"
             f"`{invite_link}`\n\n"
             f"Поделись ей с друзьями!\n"
             f"Когда они перейдут — бот узнает что их пригласил ты (ID: {user_id})",
        format="markdown",
    )


def _invite_keyboard() -> KeyboardBuilder:
    """Build keyboard with invite link button"""
    kb = KeyboardBuilder(inline=True)
    kb.callback("📤 Пригласить друга", "get_invite_link")
    return kb


async def main():
    bot = Bot(
        token=os.getenv("MAX_BOT_TOKEN"),
        parse_mode=ParseMode.MARKDOWN,
    )
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    bot_username = me.get("username", "my_bot")
    print(f"Bot started: @{bot_username}")
    print(f"Deep link example: https://max.ru/{bot_username}?start=ref_12345")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
