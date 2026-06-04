"""
Router Bot — multiple routers, F magic filters, advanced routing

DEMONSTRATES
────────────
  • Multiple Router instances       — split handlers by feature/role
  • Router(name=)                   — named routers for easier debugging
  • dp.include_router()             — registration order is routing priority
  • F.text magic filter             — access event.text with magic_filter.F
  • F.text.func(lambda)             — custom predicate on text content
  • F.text.contains(list)           — match if text contains any of the strings
  • F.text == "exact"               — exact text match

COMMANDS
────────
  /admin  — admin-only command (admin_router)
  /stats  — admin stats (admin_router)
  /profile— user command (user_router)
  /settings — user settings (user_router)
  /start  — common welcome (common_router)
  /help   — common help (common_router)
  "!cmd"  — admin shell commands starting with !
  "помощь"/"help" — any message containing these words → help reply
  "привет" — greeting response

VISUAL IN MAX MESSENGER
───────────────────────
  /admin     → "👑 Админ панель"
  "!deploy"  → "⚙️ Выполняю: !deploy"
  "нужна помощь" → "💡 Для помощи используйте /help"
  "Привет!"  → "👋 Привет! Как дела?"

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python router_bot.py

ROUTING PRIORITY
────────────────
  Routers are checked in registration order. The first handler whose filters
  all pass wins. Here: admin_router → user_router → common_router.
  Use named routers to identify which router matched in logs.
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command, F, BotCommand

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()

# Separate routers — handlers are organized by responsibility
admin_router  = Router(name="admin")
user_router   = Router(name="user")
common_router = Router(name="common")

# ── Admin Router ──────────────────────────────────────────────────────────────

@admin_router.message_created(Command(["admin", "stats"]))
async def cmd_admin(event):
    """Admin commands — in a real bot you'd add an admin-ID check here."""
    await event.answer("👑 Админ панель\n\n📊 Статистика бота активна")


@admin_router.message_created(F.text.func(lambda t: t.startswith("!")))
async def admin_shell_command(event):
    """
    Handle admin commands starting with '!'.

    F.text.func(predicate) applies an arbitrary function to event.text.
    event.text maps to EventContext.text property (handles all message types).
    """
    await event.answer(f"⚙️ Выполняю: {event.text}")


# ── User Router ───────────────────────────────────────────────────────────────

@user_router.message_created(Command("profile"))
async def cmd_profile(event):
    await event.answer("👤 Профиль пользователя")


@user_router.message_created(Command("settings"))
async def cmd_settings(event):
    await event.answer("⚙️ Настройки")


@user_router.message_created(F.text.contains(["помощь", "help"]))
async def help_keyword_handler(event):
    """
    Match messages that contain 'помощь' OR 'help' (case-sensitive).

    F.text.contains(list) checks whether any item from the list appears
    as a substring of event.text.
    """
    await event.answer("💡 Для помощи используйте /help")


# ── Common Router ─────────────────────────────────────────────────────────────

@common_router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "👋 Добро пожаловать!\n\n"
        "Команды:\n"
        "/admin    — Админ панель\n"
        "/profile  — Профиль\n"
        "/settings — Настройки\n"
        "/help     — Помощь"
    )


@common_router.message_created(Command("help"))
async def cmd_help(event):
    await event.answer(
        "📖 Справка:\n\n"
        "Это бот с несколькими роутерами.\n"
        "Команды проверяются в порядке: admin → user → common."
    )


@common_router.message_created(F.text.func(lambda t: "привет" in t.lower()))
async def hello_handler(event):
    """
    Match messages that contain 'привет' (any case).

    .lower() makes it case-insensitive. The lambda runs on event.text.
    """
    await event.answer("👋 Привет! Как дела?")


# ── Router wiring ─────────────────────────────────────────────────────────────
# Order determines priority: admin_router is checked first.

dp.include_router(admin_router)
dp.include_router(user_router)
dp.include_router(common_router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start",    description="Приветствие"),
        BotCommand(name="help",     description="Справка"),
        BotCommand(name="admin",    description="Админ панель (admin_router)"),
        BotCommand(name="profile",  description="Профиль пользователя (user_router)"),
        BotCommand(name="settings", description="Настройки (user_router)"),
    ])
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
