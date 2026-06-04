"""
I18n Bot — multilingual bot with automatic locale detection

DEMONSTRATES
────────────
  • I18n(path, default_locale)       — load JSON translation files
  • i18n(event, key)                 — translate key for user's locale
  • i18n.gettext(event, key)         — same as i18n(event, key)
  • i18n.ngettext(event, sg, pl, n)  — pluralisation
  • i18n.get_locale(event)           — detect locale from Max API user_locale
  • i18n.available_locales()         — list loaded locales
  • locale stored in event.data      — manual override via callback

COMMANDS
────────
  /start    — greet in the user's locale (auto-detected from Max Messenger)
  /help     — help text in user's locale
  /lang     — show language selection keyboard
  /plural   — pluralisation demo (1 item vs 5 items)

VISUAL IN MAX MESSENGER
───────────────────────
  /start (RU user) → "Привет! ..."
  /start (EN user) → "Hello! ..."
  /lang   → inline keyboard: "🇺🇸 English" / "🇷🇺 Русский"
  Click RU → "Язык изменён на русский" — all following messages in RU

SETUP
─────
  Create locales/ directory next to i18n_bot.py with:

    locales/en.json:
      {"greeting": "Hello!", "help": "Help text", "select_language": "Choose language",
       "lang_changed": "Language changed", "echo": "You said: {text}",
       "one_item": "{count} item", "many_items": "{count} items"}

    locales/ru.json:
      {"greeting": "Привет!", "help": "Справка", "select_language": "Выберите язык",
       "lang_changed": "Язык изменён", "echo": "Вы написали: {text}",
       "one_item": "{count} предмет", "many_items": "{count} предметов"}

  export MAX_BOT_TOKEN=your_token_here
  python i18n_bot.py

HOW LOCALE DETECTION WORKS
───────────────────────────
  Max Messenger sends user_locale (IETF BCP 47, e.g. "ru", "en") in each update.
  I18n reads it from event.user_locale via event.locale property.
  If the user manually selects a language, store it in event.data['locale']
  — it takes priority over the API-provided locale.
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command, BotCommand
from aioscam.i18n import I18n
from aioscam.utils.keyboard import KeyboardBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── I18n setup ────────────────────────────────────────────────────────────────

# Path is relative to the working directory. Adjust if needed.
i18n = I18n(path="locales", default_locale="en")

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """
    Greet the user in their locale.

    i18n(event, key) is shorthand for i18n.gettext(event, key).
    It detects the locale from event.locale (checks event.data first,
    then falls back to the Max API user_locale field).
    """
    text = i18n(event, "greeting")
    locale = i18n.get_locale(event)
    await event.answer(f"{text}\n\n_(locale: {locale})_")


@router.message_created(Command("help"))
async def cmd_help(event):
    """Help text — automatically in the user's locale."""
    await event.answer(i18n(event, "help"))


@router.message_created(Command("lang"))
async def cmd_lang(event):
    """Language selection keyboard."""
    builder = KeyboardBuilder(inline=True)
    builder.callback("🇺🇸 English", "lang:en")
    builder.callback("🇷🇺 Русский", "lang:ru")

    await event.answer(
        i18n(event, "select_language"),
        keyboard=builder.build().to_dict(),
    )


@router.message_created(Command("plural"))
async def cmd_plural(event):
    """
    Demonstrate ngettext (pluralisation).

    ngettext picks the right translation form based on count
    and substitutes {count} in the translated string.
    """
    lines = []
    for n in (1, 2, 5, 21):
        form = i18n.ngettext(event, "one_item", "many_items", count=n)
        lines.append(f"• n={n}: {form}")
    await event.answer("**Pluralisation:**\n\n" + "\n".join(lines))


@router.callback_query()
async def handle_callback(event):
    """
    Language selection callback.

    Storing locale in event.data['locale'] makes I18n use it for all
    subsequent messages (takes priority over user_locale from Max API).
    """
    callback_data = event.callback_data or ""
    callback_id = event.callback_id

    if callback_data.startswith("lang:"):
        locale = callback_data.split(":", 1)[1]
        event.data["locale"] = locale
        text = i18n(event, "lang_changed")
        await event.bot.send_callback(callback_id=callback_id, message=text)
    else:
        await event.bot.send_callback(
            callback_id=callback_id,
            message=f"🔘 Callback: {callback_data}",
        )


@router.message_created()
async def echo_message(event):
    """Echo any text using the 'echo' translation key (supports {text} substitution)."""
    if event.message and event.message.has_text:
        await event.answer(i18n(event, "echo", text=event.text or ""))


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start",  description="Приветствие на языке пользователя"),
        BotCommand(name="help",   description="Справка (автоперевод)"),
        BotCommand(name="lang",   description="Выбрать язык"),
        BotCommand(name="plural", description="Демо склонения чисел"),
    ])
    print(f"Locales loaded: {i18n.available_locales()}")
    print(f"Default locale: {i18n.default_locale}")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
