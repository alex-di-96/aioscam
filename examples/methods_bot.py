"""
Methods API Example

Demonstrates the structured methods pattern:
- Bot.execute() for executing method objects
- SendMessage, GetMe, GetUpdates as reusable objects
- Methods can be passed around, composed, tested independently
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command
from aioscam import GetMe, SendMessage, GetUpdates
from aioscam.enums import ParseMode

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Show methods API demo"""
    await event.answer(
        "📦 **Methods API Demo**\n\n"
        "Структурированный подход к API вызовам:\n\n"
        "```python\n"
        "# Старый стиль\n"
        "await bot.get_me()\n"
        "await bot.send_message(chat_id=..., text=...)\n\n"
        "# Новый стиль — методы как объекты\n"
        "await bot.execute(GetMe())\n"
        "await bot.execute(SendMessage(chat_id=..., text=...))\n"
        "```\n\n"
        "Команды:\n"
        "/me — получить info о боте через GetMe()\n"
        "/send — отправить сообщение через SendMessage()\n"
        "/updates — получить обновления через GetUpdates()"
    )


@router.message_created(Command("me"))
async def cmd_me(event):
    """Get bot info using GetMe method object"""
    me = await event.bot.execute(GetMe())

    await event.answer(
        f"🤖 **Bot Info (via GetMe())**\n\n"
        f"ID: {me.get('id')}\n"
        f"Username: {me.get('username')}\n"
        f"Name: {me.get('first_name')}"
    )


@router.message_created(Command("send"))
async def cmd_send(event):
    """Send message using SendMessage method object"""
    method = SendMessage(
        chat_id=event.chat_id,
        text="📨 Это сообщение отправлено через **SendMessage()** метод!",
        format="markdown",
    )

    result = await event.bot.execute(method)

    await event.answer(
        f"✅ Сообщение отправлено!\n\n"
        f"Method: {type(method).__name__}\n"
        f"Path: {method.path}\n"
        f"HTTP: {method.http_method.value}"
    )


@router.message_created(Command("updates"))
async def cmd_updates(event):
    """Get updates using GetUpdates method object"""
    method = GetUpdates(
        limit=1,
        timeout=1,
    )

    updates = await event.bot.execute(method)

    count = len(updates) if isinstance(updates, list) else 0
    await event.answer(
        f"📊 **Updates (via GetUpdates())**\n\n"
        f"Получено: {count} обновлений\n"
        f"Path: {method.path}\n"
        f"HTTP: {method.http_method.value}\n"
        f"Params: {method.params}"
    )


# Include router
dp.include_router(router)


async def main():
    """Main function"""
    bot = Bot()

    logging.info("Bot started with Methods API demo")
    logging.info("Commands: /start, /me, /send, /updates")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
