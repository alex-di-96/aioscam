"""
I18n Example — Multilingual Bot

Demonstrates internationalization support:
- Automatic locale detection from event.user_locale (Max API)
- JSON-based translations in locales/ directory
- gettext-like API: i18n(event, "key") or i18n.gettext(event, "key")
- Pluralization: i18n.ngettext(event, "one_item", "many_items", count)
- Format variables: i18n(event, "welcome", name="John")

Locales directory structure:
    locales/
    ├── en.json
    ├── ru.json
    └── uk.json

Each file is a flat dict: {"key": "translated text"}
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.i18n import I18n
from aioscam.utils.keyboard import KeyboardBuilder

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize I18n with locales directory
i18n = I18n(path="locales", default_locale="en")

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.message_created(Command("start"))
async def cmd_start(event):
    """Greeting — automatically uses user's locale"""
    # i18n(event, "greeting") auto-detects locale from event.user_locale
    text = i18n(event, "greeting")
    
    # Show detected locale
    locale = i18n.get_locale(event)
    text += f"\n\n(Your locale: {locale})"
    
    await event.answer(text)


@router.message_created(Command("help"))
async def cmd_help(event):
    """Help text — automatically translated"""
    await event.answer(i18n(event, "help"))


@router.message_created(Command("lang"))
async def cmd_lang(event):
    """Show language selection keyboard"""
    builder = KeyboardBuilder(inline=True)
    builder.callback("🇬🇧 English", "lang:en")
    builder.callback("🇷🇺 Русский", "lang:ru")
    builder.row()
    builder.callback("🇺🇦 Українська", "lang:uk")

    await event.answer(
        i18n(event, "select_language"),
        keyboard=builder.build().to_dict()
    )


@router.callback_query()
async def handle_callback(event):
    """Handle language selection and other callbacks"""
    callback_data = event.callback_data or ""

    if callback_data.startswith("lang:"):
        # User selected a language
        locale = callback_data.split(":")[1]
        
        # Save locale in event data (persists via FSM if used)
        event.data['locale'] = locale
        
        # Respond in the new locale
        # Temporarily override locale for this response
        event.data['locale'] = locale
        text = i18n(event, "lang_changed")
        await event.answer(text)

    else:
        # Default callback handling
        await event.answer(f"🔘 Callback: {callback_data}")


@router.message_created()
async def echo_message(event):
    """Echo messages — shows translation with format variables"""
    if event.message.has_text:
        text = event.text
        
        # Check if user wants to test formatting
        if text.lower() == "count":
            await event.answer(i18n.ngettext(event, "one_item", "many_items", count=1))
            await event.answer(i18n.ngettext(event, "one_item", "many_items", count=5))
        elif text.lower() == "welcome":
            await event.answer(i18n(event, "welcome", name="User"))
        else:
            # Echo with translation
            await event.answer(i18n(event, "echo", text=text))


# Include router
dp.include_router(router)


async def main():
    """Main function"""
    bot = Bot()

    print(f"🌐 I18n locales: {i18n.available_locales()}")
    print(f"🌐 Default locale: {i18n.default_locale}")
    print(f"🌐 Locales path: {i18n.path}")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
