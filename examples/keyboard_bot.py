"""
Keyboard example

This example demonstrates how to create and use keyboards with buttons.
"""

import asyncio
import logging
from aioscam import Bot, Dispatcher, Router, Command
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.enums import ButtonType

# Setup logging
logging.basicConfig(level=logging.INFO)

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Handle /start command with keyboard"""
    # Create inline keyboard
    builder = KeyboardBuilder(inline=True)
    
    builder.callback("📊 Статистика", "stats")
    builder.callback("⚙️ Настройки", "settings")
    builder.row()
    builder.link("🌐 Наш сайт", "https://example.com")
    builder.callback("ℹ️ Помощь", "help")
    
    keyboard = builder.build()
    
    await event.answer(
        "👋 Добро пожаловать!\n\n"
        "Выберите действие:",
        keyboard=keyboard.to_dict()
    )


@router.message_created(Command("menu"))
async def cmd_menu(event):
    """Show main menu"""
    builder = KeyboardBuilder(inline=True)
    
    # First row
    builder.callback("📦 Заказы", "orders")
    builder.callback("🛒 Корзина", "cart")
    builder.row()
    
    # Second row
    builder.callback("👤 Профиль", "profile")
    builder.callback("📞 Контакты", "contacts")
    builder.row()
    
    # Third row
    builder.callback("❓ Помощь", "help")
    builder.callback("🚪 Выход", "logout")
    
    keyboard = builder.build()
    
    await event.answer(
        "📱 Главное меню:",
        keyboard=keyboard.to_dict()
    )


@router.callback_query()
async def handle_callback(event):
    """Handle callback queries — must use send_callback() to dismiss the button spinner"""
    callback_data = event.callback_data
    callback_id = event.callback_id

    if callback_data == "stats":
        await event.bot.send_callback(callback_id=callback_id, message="📊 Статистика: пока нет данных")
    elif callback_data == "settings":
        await event.bot.send_callback(callback_id=callback_id, message="⚙️ Настройки откроются soon")
    elif callback_data == "help":
        await event.bot.send_callback(callback_id=callback_id, message="ℹ️ Справка: используйте /start")
    elif callback_data == "orders":
        await event.bot.send_callback(callback_id=callback_id, message="📦 У вас пока нет заказов")
    elif callback_data == "cart":
        await event.bot.send_callback(callback_id=callback_id, message="🛒 Корзина пуста")
    else:
        await event.bot.send_callback(callback_id=callback_id, message=f"🔘 Нажата кнопка: {callback_data}")


# Include router into dispatcher
dp.include_router(router)


async def main():
    """Main function"""
    bot = Bot()
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
