"""
Router and filters example

This example demonstrates advanced routing and filtering.
"""

import asyncio
import logging
from aioscam import Bot, Dispatcher, Router, Command, F

# Setup logging
logging.basicConfig(level=logging.INFO)

# Create dispatcher
dp = Dispatcher()

# Create routers for different features
admin_router = Router(name="admin")
user_router = Router(name="user")
common_router = Router(name="common")


# ==================== Admin Router ====================

@admin_router.message_created(Command(["admin", "stats"]))
async def cmd_admin(event):
    """Admin command"""
    await event.answer("👑 Админ панель\n\n📊 Статистика бота активна")


@admin_router.message_created(F.message.body.text.func(lambda t: t.startswith("!")))
async def admin_command(event):
    """Handle admin commands starting with !"""
    await event.answer(f"⚙️ Выполняю: {event.message.text}")


# ==================== User Router ====================

@user_router.message_created(Command("profile"))
async def cmd_profile(event):
    """Show user profile"""
    await event.answer("👤 Профиль пользователя")


@user_router.message_created(Command("settings"))
async def cmd_settings(event):
    """Show settings"""
    await event.answer("⚙️ Настройки")


@user_router.message_created(F.message.body.text.contains(["помощь", "help"]))
async def help_filter(event):
    """Handle messages containing 'помощь' or 'help'"""
    await event.answer("💡 Для помощи используйте /help")


# ==================== Common Router ====================

@common_router.message_created(Command("start"))
async def cmd_start(event):
    """Handle /start command"""
    await event.answer(
        "👋 Добро пожаловать!\n\n"
        "Доступные команды:\n"
        "/admin - Админ панель\n"
        "/profile - Профиль\n"
        "/settings - Настройки\n"
        "/help - Помощь"
    )


@common_router.message_created(Command("help"))
async def cmd_help(event):
    """Handle /help command"""
    await event.answer(
        "📖 Справка:\n\n"
        "Это демонстрационный бот с несколькими роутерами.\n"
        "Попробуйте разные команды!"
    )


@common_router.message_created(F.message.body.text.func(lambda t: "привет" in t.lower()))
async def hello_handler(event):
    """Handle hello messages"""
    await event.answer("👋 Привет! Как дела?")


# Include routers in order
dp.include_router(admin_router)
dp.include_router(user_router)
dp.include_router(common_router)


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
