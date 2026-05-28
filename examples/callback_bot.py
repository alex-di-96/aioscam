"""
Callback API Example

Demonstrates callback handling with the new send_callback() API:
- Inline keyboard buttons
- bot.send_callback() — JSON body, matches official Max SDK
- event.answer() — convenience wrapper
- callback_data parsing

SDK alignment:
- URL: https://botapi.max.ru/answers
- Auth: access_token in query params
- Body: JSON {"message": {"text": "..."}, "notification": "..."}
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.utils.keyboard import KeyboardBuilder

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Show callback demo menu"""
    builder = KeyboardBuilder(inline=True)
    builder.callback("ℹ️ Ответ текстом", "cb:message")
    builder.callback("🔔 Ответ + уведомление", "cb:notify")
    builder.row()
    builder.callback("⏹️ Только закрыть", "cb:close")

    await event.answer(
        "🔘 **Callback Demo**\n\n"
        "Нажмите кнопку — бот ответит через `bot.send_callback()`.\n\n"
        "SDK-aligned API:\n"
        "• JSON body\n"
        "• message — структура NewMessageBody\n"
        "• notification — всплывающее окно\n"
        "• access_token в query params",
        keyboard=builder.build().to_dict()
    )


@router.callback_query()
async def handle_callback(event):
    """Handle all callback queries using bot.send_callback()"""
    callback_data = event.callback_data or ""

    if callback_data == "cb:message":
        # Answer with message only (no notification popup)
        await event.bot.send_callback(
            callback_id=event.callback_id,
            message="ℹ️ Это текстовый ответ на callback.",
        )

    elif callback_data == "cb:notify":
        # Answer with both message and notification (popup)
        await event.bot.send_callback(
            callback_id=event.callback_id,
            message="🔔 Вы нажали кнопку с уведомлением!",
            notification="Это всплывающее окно!",
        )

    elif callback_data == "cb:close":
        # Close callback without any message (just dismiss)
        await event.bot.send_callback(
            callback_id=event.callback_id,
        )

    else:
        # Fallback
        await event.bot.send_callback(
            callback_id=event.callback_id,
            message=f"🔘 Callback: {callback_data}",
        )


@router.message_created(Command("help"))
async def cmd_help(event):
    """Show help about callback API"""
    await event.answer(
        "📖 **Callback API (SDK-aligned)**\n\n"
        "**bot.send_callback():**\n"
        "```python\n"
        "await bot.send_callback(\n"
        "    callback_id=event.callback_id,\n"
        "    message='Текст ответа',\n"
        "    notification='Попап',  # опционально\n"
        ")\n"
        "```\n\n"
        "**event.answer()** — удобная обёртка:\n"
        "```python\n"
        "await event.answer('Ответ!')\n"
        "```\n\n"
        "SDK alignment:\n"
        "• URL: botapi.max.ru/answers\n"
        "• JSON body: {message: {text}, notification}\n"
        "• access_token в query params"
    )


# Include router
dp.include_router(router)


async def main():
    """Main function"""
    bot = Bot()

    logging.info("Bot started with Callback API demo")
    logging.info("Commands: /start, /help")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
