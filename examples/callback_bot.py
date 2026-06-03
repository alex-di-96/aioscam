"""
Callback API Example

Demonstrates callback handling with the new send_callback() API:
- Inline keyboard buttons
- bot.send_callback() — JSON body, matches official Max SDK
- event.answer() — convenience wrapper
- callback_data parsing

SDK alignment:
- URL: https://botapi.max.ru/answers
- Auth: Authorization header (access_token query param deprecated by Max API)
- Body: JSON {"message": {"text": "..."}, "notification": "..."}
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.utils.keyboard import KeyboardBuilder

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] %(name)s | %(message)s',
)
logger = logging.getLogger(__name__)

dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    logger.info("cmd_start: user=%s", getattr(event.from_user, 'user_id', '?'))
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
        "• Authorization header (не access_token в params)",
        keyboard=builder.build().to_dict()
    )


@router.callback_query()
async def handle_callback(event):
    callback_data = event.callback_data or ""
    callback_id = event.callback_id
    logger.info("callback received: data=%r  id=%s", callback_data, callback_id)

    if callback_data == "cb:message":
        result = await event.bot.send_callback(
            callback_id=callback_id,
            message="ℹ️ Это текстовый ответ на callback.",
        )

    elif callback_data == "cb:notify":
        result = await event.bot.send_callback(
            callback_id=callback_id,
            message="🔔 Вы нажали кнопку с уведомлением!",
            notification="Это всплывающее окно!",
        )

    elif callback_data == "cb:close":
        result = await event.bot.send_callback(
            callback_id=callback_id,
        )

    else:
        result = await event.bot.send_callback(
            callback_id=callback_id,
            message=f"🔘 Callback: {callback_data}",
        )

    # Диагностика: показываем что реально вернул send_callback
    # Ожидаем {"success": true} или аналогичный JSON от API
    # Если видим {"raw": "..."} — значит баг с двойным чтением ответа подтверждён
    logger.debug("send_callback result: %s", result)
    if isinstance(result, dict) and "raw" in result and "success" not in result:
        logger.warning("send_callback вернул raw-строку вместо JSON — баг подтверждён! result=%s", result)
    else:
        logger.info("send_callback OK: %s", result)


@router.message_created(Command("help"))
async def cmd_help(event):
    logger.info("cmd_help: user=%s", getattr(event.from_user, 'user_id', '?'))
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
        "• Authorization header (не access_token в params)"
    )


dp.include_router(router)


async def main():
    bot = Bot()
    logger.info("Callback bot started | commands: /start /help")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
