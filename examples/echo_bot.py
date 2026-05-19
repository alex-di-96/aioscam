"""
Echo bot example

This example demonstrates a simple bot that echoes all messages back to the user.
"""

import asyncio
import logging
from aoscam import Bot, Dispatcher, Router, Command, F

# Setup logging
logging.basicConfig(level=logging.INFO)

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Handle /start command"""
    await event.message.answer(
        "👋 Привет! Я эхо-бот. Отправь мне любое сообщение, и я повторю его!"
    )


@router.message_created(Command("help"))
async def cmd_help(event):
    """Handle /help command"""
    await event.message.answer(
        "📖 Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "\nПросто отправьте мне любое сообщение!"
    )


@router.message_created()
async def echo_message(event):
    """Echo all messages"""
    if event.message.has_text:
        # Show typing action
        from aioscam.enums import SenderAction
        await event.bot.send_action(event.message.chat.id, SenderAction.TYPING)
        
        # Echo the message
        await event.message.answer(f"🔁 {event.message.text}")


@router.message_created(F.message.body.text.func(lambda t: "привет" in t.lower()))
async def handle_hello(event):
    """Handle hello messages"""
    await event.message.answer("👋 Привет! Как дела?")


# Include router into dispatcher
dp.include_router(router)


async def main():
    """Main function"""
    # Create bot (token from MAX_BOT_TOKEN environment variable)
    bot = Bot()
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
