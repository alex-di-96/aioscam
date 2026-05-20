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
from aioscam.types import Message, Update
from aioscam.types.keyboard import InlineKeyboardBuilder, InlineButton
from aioscam.types.parse_mode import ParseMode
from aioscam.utils import create_deep_link

load_dotenv()

router = Router()


@router.bot_started()
async def on_bot_started(event: Update):
    """Handle bot_started event (user opens bot dialog)"""
    user_id = event.user_id or (event.user.id if event.user else "unknown")

    # Check if this is a deep link (has payload)
    if event.payload:
        await handle_deep_link(event, user_id)
    else:
        # Regular start without deep link
        await event.bot.send_message(
            chat_id=event.chat_id or user_id,
            text="👋 Привет! Я демо-бот диплинков.\n\n"
                 "Нажми кнопку ниже чтобы получить персональную ссылку-приглашение!",
            keyboard=_invite_keyboard(event.bot.username),
        )


async def handle_deep_link(event: Update, user_id):
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
        chat_id=event.chat_id or user_id,
        text=text,
    )


@router.message_created(Command("start"))
async def on_start(event: Update):
    """Handle /start command"""
    user_id = event.user_id or (event.user.id if event.user else "unknown")

    await event.bot.send_message(
        chat_id=event.chat_id or user_id,
        text="👋 Привет!\n\n"
             "Нажми кнопку ниже чтобы получить персональную ссылку-приглашение.\n"
             "Когда кто-то перейдёт по ней — бот узнает кто пригласил!",
        keyboard=_invite_keyboard(event.bot.username),
    )


@router.message_created(Command("help"))
async def on_help(event: Update):
    """Handle /help command"""
    await event.bot.send_message(
        chat_id=event.chat_id or event.user_id,
        text="**Демо диплинков**\n\n"
             "/start — начать работу\n"
             "/help — эта справка\n\n"
             "Используй кнопку 'Пригласить друга' для создания персональной ссылки.",
    )


@router.message_created(F.data.startswith("get_invite_link"))
async def on_get_invite_link(event: Update):
    """Generate personal invite link"""
    user_id = event.user_id or (event.user.id if event.user else 0)
    bot_username = event.bot.username or "my_bot"

    # Create deep link with user's ID as payload
    invite_link = create_deep_link(bot_username, f"ref_{user_id}")

    await event.bot.send_message(
        chat_id=event.chat_id or user_id,
        text=f"📬 Твоя персональная ссылка:\n\n"
             f"`{invite_link}`\n\n"
             f"Поделись ей с друзьями!\n"
             f"Когда они перейдут — бот узнает что их пригласил ты (ID: {user_id})",
    )


def _invite_keyboard(bot_username: str) -> InlineKeyboardBuilder:
    """Build keyboard with invite link button"""
    kb = InlineKeyboardBuilder()
    kb.add_button(InlineButton(text="📤 Пригласить друга", callback_data="get_invite_link"))
    return kb


async def main():
    bot = Bot(
        token=os.getenv("MAX_BOT_TOKEN"),
        parse_mode=ParseMode.MARKDOWN,
    )
    dp = Dispatcher(bot)
    dp.include_router(router)

    print(f"Bot started: @{bot.username}")
    print(f"Deep link example: https://max.ru/{bot.username}?start=ref_12345")

    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
