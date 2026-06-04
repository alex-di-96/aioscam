"""
Keyboard Format Test Bot — visual rendering test tool

NOTE: This is a visual QA tool, not a learning example.
      Run it to manually verify how Max Messenger renders
      button text and message formatting.

DEMONSTRATES
────────────
  • ParseMode.HTML vs ParseMode.MARKDOWN  — formatting in messages
  • Long button text (up to 128 chars)    — max button label length
  • Multiline button text (\\n in labels) — how Max renders line breaks
  • KeyboardBuilder.callback()            — inline callback buttons

COMMANDS
────────
  /start  — send 3 test messages with different keyboard configurations

VISUAL IN MAX MESSENGER
───────────────────────
  Test 1 (HTML):     <b>bold</b>, <i>italic</i> + 128-char button
  Test 2 (Markdown): **bold**, *italic* + normal buttons
  Test 3:            buttons containing \\n newline characters

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python keyboard_format_test_bot.py
"""

import asyncio
import logging
from aioscam import Bot, Dispatcher, Router, Command
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.enums import ParseMode

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Test button text length and formatting"""
    logger.info("Handling /start command")
    
    # === ТЕСТ 1: HTML формат с длинной кнопкой ===
    html_text = (
        "<b>Тест 1: HTML формат</b>\n\n"
        "Это сообщение в <b>HTML</b> формате.\n"
        "Поддерживаемые теги:\n"
        "• <b>жирный</b>\n"
        "• <i>курсив</i>\n"
        "• <code>код</code>\n"
        "• <a href='https://example.com'>ссылка</a>\n\n"
        "Кнопка ниже содержит 128 символов:"
    )
    
    # Кнопка с 128 символами
    long_button_text = (
        "🔘 Очень длинная кнопка для тестирования максимального размера текста "
        "который может отображаться в Max Messenger без обрезания"
    )
    logger.info(f"Button 1 length: {len(long_button_text)} chars")
    
    builder1 = KeyboardBuilder(inline=True)
    builder1.callback(long_button_text, "test_128_chars")
    keyboard1 = builder1.build()
    
    await event.answer(
        html_text,
        keyboard=keyboard1.to_dict(),
        format=ParseMode.HTML
    )
    
    # === ТЕСТ 2: Markdown формат ===
    markdown_text = (
        "**Тест 2: Markdown формат**\n\n"
        "Это сообщение в **Markdown** формате.\n"
        "Поддерживаемые элементы:\n"
        "- **жирный**\n"
        "- *курсив*\n"
        "- `код`\n"
        "- [ссылка](https://example.com)\n\n"
        "Сравнение с HTML:\n"
        "HTML: `<b>текст</b>`\n"
        "Markdown: `**текст**`\n\n"
        "Переносы строк работают одинаково?"
    )
    
    builder2 = KeyboardBuilder(inline=True)
    builder2.callback("✅ HTML работает", "html_ok")
    builder2.callback("✅ Markdown работает", "markdown_ok")
    builder2.row()
    builder2.callback("❌ Что-то не так", "something_wrong")
    keyboard2 = builder2.build()
    
    await event.answer(
        markdown_text,
        keyboard=keyboard2.to_dict(),
        format=ParseMode.MARKDOWN
    )
    
    # === ТЕСТ 3: Многострочный текст кнопки ===
    multiline_button = "Первая строка\nВторая строка\nТретья строка"
    logger.info(f"Button 3 (multiline): {repr(multiline_button)}")
    
    builder3 = KeyboardBuilder(inline=True)
    builder3.callback(multiline_button, "multiline_test")
    builder3.row()
    builder3.callback("Короткая кнопка", "short_button")
    keyboard3 = builder3.build()
    
    await event.answer(
        "**Тест 3: Многострочные кнопки**\n\n"
        "Кнопка выше содержит символы `\\n`.\n"
        "Отображается ли она в несколько строк?",
        keyboard=keyboard3.to_dict(),
        format=ParseMode.MARKDOWN
    )


@router.callback_query()
async def handle_callback(event):
    """Handle callback queries"""
    callback_data = event.callback_data
    callback_id = event.callback_id
    logger.info(f"Callback received: {callback_data}")

    responses = {
        "test_128_chars": "✅ Длинная кнопка (128 символов) нажата!",
        "html_ok": "✅ HTML формат работает корректно!",
        "markdown_ok": "✅ Markdown формат работает корректно!",
        "something_wrong": "❌ Что-то пошло не так. Опишите проблему.",
        "multiline_test": "✅ Многострочная кнопка нажата!",
        "short_button": "✅ Короткая кнопка нажата!",
    }

    response = responses.get(callback_data, f"🔘 Кнопка: {callback_data}")
    await event.bot.send_callback(callback_id=callback_id, message=response)


# Include router into dispatcher
dp.include_router(router)


async def main():
    """Main function"""
    bot = Bot()
    
    logger.info("Starting Keyboard Format Test Bot...")
    logger.info("Send /start to test button formatting")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
