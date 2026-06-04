"""
Keyboard Bot — inline keyboards, reply keyboards, callbacks, hide-on-click

DEMONSTRATES
────────────
  • KeyboardBuilder inline=True   — inline buttons attached to a message
  • KeyboardBuilder inline=False  — reply keyboard (shown below input field)
  • ButtonType.CALLBACK           — triggers callback_query event
  • ButtonType.LINK               — opens URL in browser
  • bot.send_callback()           — acknowledge button click (dismisses spinner)
  • event.hide_keyboard()         — remove inline keyboard after click
  • event.answer_and_hide_keyboard() — reply + remove keyboard in one call

COMMANDS
────────
  /start   — inline keyboard with callback buttons and a link button
  /menu    — multi-row inline keyboard
  /reply   — reply keyboard (shown below the text input field)
  /hide    — demo of hide_keyboard (removes keyboard after first click)

VISUAL IN MAX MESSENGER
───────────────────────
  /start → message with 4 inline buttons appears
  click "📊 Статистика" → spinner dismisses, bot replies "📊 Статистика: нет данных"
  /reply → a persistent keyboard appears below the input field
  /hide  → message with one button; clicking it removes the keyboard

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python keyboard_bot.py

IMPORTANT
─────────
  Callback buttons MUST be acknowledged via bot.send_callback(), NOT event.answer().
  event.answer() sends a new chat message; send_callback() dismisses the button
  loading spinner. Failing to call send_callback() leaves the button spinning.
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command, BotCommand
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.enums import ButtonType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Inline keyboard handlers ──────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """Inline keyboard with callback + link buttons."""
    builder = KeyboardBuilder(inline=True)
    builder.callback("📊 Статистика", "stats")
    builder.callback("⚙️ Настройки", "settings")
    builder.row()                                         # force new button row
    builder.link("🌐 Max Messenger", "https://max.ru")
    builder.callback("ℹ️ Помощь", "help")

    await event.answer(
        "👋 Добро пожаловать!\n\nВыберите действие:",
        keyboard=builder.build().to_dict(),
    )


@router.message_created(Command("menu"))
async def cmd_menu(event):
    """Multi-row inline keyboard — demonstrates .row() for layout control."""
    builder = KeyboardBuilder(inline=True)

    builder.callback("📦 Заказы", "orders")
    builder.callback("🛒 Корзина", "cart")
    builder.row()

    builder.callback("👤 Профиль", "profile")
    builder.callback("📞 Контакты", "contacts")
    builder.row()

    builder.callback("❓ Помощь", "help_menu")

    await event.answer("📱 Главное меню:", keyboard=builder.build().to_dict())


@router.message_created(Command("hide"))
async def cmd_hide(event):
    """
    Demonstrates hide_keyboard / answer_and_hide_keyboard.

    After the user clicks the button, the inline keyboard disappears from the
    message (the message text is preserved, only the keyboard is removed).
    This mimics Telegram's one_time_keyboard=True behavior.
    """
    builder = KeyboardBuilder(inline=True)
    builder.callback("✅ Нажми — клавиатура исчезнет", "do_hide")

    await event.answer(
        "После нажатия кнопки ниже клавиатура исчезнет из этого сообщения:",
        keyboard=builder.build().to_dict(),
    )


# ── Reply keyboard handler ─────────────────────────────────────────────────────

@router.message_created(Command("reply"))
async def cmd_reply(event):
    """
    Reply keyboard — appears below the text input field (not attached to a message).

    Use inline=False to create a reply keyboard. Buttons appear as persistent
    shortcuts. When tapped they send the button text as a regular message.
    """
    builder = KeyboardBuilder(inline=False)   # <-- reply keyboard
    builder.button("🆘 Помощь")
    builder.button("📋 Меню")
    builder.row()
    builder.button("❌ Закрыть клавиатуру")

    await event.answer(
        "Ниже появилась клавиатура с кнопками.\n"
        "Нажатие отправляет текст кнопки как сообщение.",
        keyboard=builder.build().to_dict(),
    )


# ── Callback handler ──────────────────────────────────────────────────────────

@router.callback_query()
async def handle_callback(event):
    """
    Handle all inline button clicks.

    Always call bot.send_callback() — it acknowledges the click and dismisses
    the loading spinner on the button. The optional `message` argument sends a
    small notification visible to the user.
    """
    callback_data = event.callback_data or ""
    callback_id = event.callback_id

    if callback_data == "do_hide":
        # Remove the inline keyboard from the original message, keep the text.
        # answer_and_hide_keyboard() edits the message to remove its keyboard.
        await event.bot.send_callback(callback_id=callback_id)
        await event.answer_and_hide_keyboard()
        return

    responses = {
        "stats":    "📊 Статистика: нет данных",
        "settings": "⚙️ Настройки скоро появятся",
        "help":     "ℹ️ Справка: используйте /start",
        "orders":   "📦 Нет заказов",
        "cart":     "🛒 Корзина пуста",
        "profile":  "👤 Профиль недоступен",
        "contacts": "📞 +7 (000) 000-00-00",
        "help_menu": "❓ Список команд: /start /menu /reply /hide",
    }
    reply = responses.get(callback_data, f"🔘 Нажата кнопка: {callback_data}")

    # send_callback dismisses the spinner; message= is shown as a popup/reply
    await event.bot.send_callback(callback_id=callback_id, message=reply)


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start", description="Inline клавиатура с кнопками"),
        BotCommand(name="menu",  description="Многострочное меню"),
        BotCommand(name="reply", description="Reply клавиатура под полем ввода"),
        BotCommand(name="hide",  description="Клавиатура исчезает после нажатия"),
    ])
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
