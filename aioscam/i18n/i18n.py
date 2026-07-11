"""
I18n storage and translation engine
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles

logger = logging.getLogger(__name__)


class I18n:
    """
    Internationalization engine with JSON-based translations

    Loads translation files from a directory and provides gettext-like API.
    Automatically detects user locale from event.user_locale.

    Directory structure:
        locales/
        ├── en.json
        ├── ru.json
        └── uk.json

    Each file is a flat dict: {"key": "translated text"}

    Usage:
        # Create at module level (sync load — safe before event loop starts)
        i18n = I18n(path="locales", default_locale="en")

        # OR: create without loading, then init async inside main()
        i18n = I18n(path="locales", default_locale="en", lazy=True)
        async def main():
            await i18n.reload()   # async load with aiofiles
            await dp.start_polling(bot)

        # In handler:
        @router.message_created(Command("start"))
        async def cmd_start(event, state):
            text = i18n.gettext(event, "greeting")
            await event.answer(text)

        # Hot-reload translations without restarting:
        await i18n.reload()

        # With pluralization:
        text = i18n.ngettext(event, "one_item", "many_items", count=5)

        # With formatting:
        text = i18n.gettext(event, "welcome", name="John")
    """

    def __init__(
        self,
        path: str,
        default_locale: str = "en",
        domain: str = "messages",
        lazy: bool = False,
    ):
        """
        Initialize I18n.

        Args:
            path: Path to locales directory
            default_locale: Default locale if user locale not found
            domain: Translation domain (filename without .json)
            lazy: If True, skip loading in __init__ — call await i18n.reload() manually.
                  Use lazy=True when creating I18n inside an already-running event loop.
        """
        self.path = Path(path)
        self.default_locale = default_locale
        self.domain = domain
        self._translations: Dict[str, Dict[str, str]] = {}

        if not lazy:
            # Sync load — safe when called at module level before event loop starts.
            # If the event loop is already running, use lazy=True and await reload().
            self._load_translations_sync()

    def _load_translations_sync(self) -> None:
        """
        Sync load of all translation files.

        Called from __init__ before the event loop starts.
        For runtime reload (hot-reload), use the async reload() method instead.
        """
        if not self.path.exists():
            logger.warning(f"Locales directory not found: {self.path}")
            return

        files = list(self.path.glob(f"{self.domain}_*.json"))
        if not files:
            # Try without domain prefix: en.json, ru.json, etc.
            files = list(self.path.glob("*.json"))

        for file in files:
            stem = file.stem
            locale = stem.replace(f"{self.domain}_", "") if stem.startswith(f"{self.domain}_") else stem
            try:
                self._translations[locale] = json.loads(file.read_text(encoding="utf-8"))
                logger.info(f"Loaded locale '{locale}': {len(self._translations[locale])} keys")
            except Exception as e:
                logger.error(f"Failed to load locale '{locale}': {e}")

    async def reload(self) -> None:
        """
        Async reload of all translation files using aiofiles.

        Use this:
        - Inside an already-running event loop (lazy=True init)
        - For hot-reload without restarting the bot

        Example:
            i18n = I18n(path="locales", default_locale="ru", lazy=True)
            async def main():
                await i18n.reload()
                await dp.start_polling(bot)
        """
        if not self.path.exists():
            logger.warning(f"Locales directory not found: {self.path}")
            return

        files = list(self.path.glob(f"{self.domain}_*.json"))
        if not files:
            files = list(self.path.glob("*.json"))

        new_translations: Dict[str, Dict[str, str]] = {}
        for file in files:
            stem = file.stem
            locale = stem.replace(f"{self.domain}_", "") if stem.startswith(f"{self.domain}_") else stem
            try:
                async with aiofiles.open(file, "r", encoding="utf-8") as f:
                    content = await f.read()
                new_translations[locale] = json.loads(content)
                logger.info(f"Reloaded locale '{locale}': {len(new_translations[locale])} keys")
            except Exception as e:
                logger.error(f"Failed to reload locale '{locale}': {e}")

        self._translations = new_translations

    def get_locale(self, event: Any) -> str:
        """
        Detect user locale from event

        Priority:
        1. event.user_locale (from Max API)
        2. event.data.get('locale') (manually set)
        3. default_locale

        Args:
            event: EventContext or raw event

        Returns:
            Locale string (e.g., "ru", "en")
        """
        # Try event.user_locale (from Max API update)
        if hasattr(event, 'event') and hasattr(event.event, 'user_locale'):
            locale = event.event.user_locale
            if locale and locale in self._translations:
                return locale

        # Try event.data['locale'] (manually set via FSM or middleware)
        if hasattr(event, 'data') and isinstance(event.data, dict):
            locale = event.data.get('locale')
            if locale and locale in self._translations:
                return locale

        # Try event.user_locale directly (on raw event)
        if hasattr(event, 'user_locale'):
            locale = event.user_locale
            if locale and locale in self._translations:
                return locale

        return self.default_locale

    def translate(self, locale: Optional[str], key: str, **kwargs: Any) -> str:
        """
        Get translated string for an explicit locale (no event needed).

        Useful when the locale is stored rather than derived from the current
        event — e.g. rendering a shared message in its creator's language.

        Args:
            locale: Locale code ("ru", "en", ...); None → default_locale
            key: Translation key
            **kwargs: Format variables

        Returns:
            Translated and formatted string (key itself if missing everywhere)
        """
        translations = self._translations.get(locale or self.default_locale, {})
        text = translations.get(key)
        if text is None:
            text = self._translations.get(self.default_locale, {}).get(key, key)

        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass

        return text

    def gettext(self, event: Any, key: str, **kwargs: Any) -> str:
        """
        Get translated string for the user's locale

        Args:
            event: EventContext or raw event
            key: Translation key
            **kwargs: Format variables (e.g., name="John")

        Returns:
            Translated and formatted string
        """
        return self.translate(self.get_locale(event), key, **kwargs)

    def ngettext(self, event: Any, singular: str, plural: str, count: int, **kwargs: Any) -> str:
        """
        Get translated string with pluralization

        Simple pluralization: uses singular for count=1, plural otherwise.
        For complex pluralization rules, override in subclass.

        Args:
            event: EventContext or raw event
            singular: Key for singular form
            plural: Key for plural form
            count: Item count
            **kwargs: Format variables

        Returns:
            Translated and formatted string
        """
        key = singular if count == 1 else plural
        return self.gettext(event, key, count=count, **kwargs)

    def __call__(self, event: Any, key: str, **kwargs: Any) -> str:
        """Convenience alias for gettext"""
        return self.gettext(event, key, **kwargs)

    def available_locales(self) -> list:
        """List of available locale codes"""
        return list(self._translations.keys())

    def __repr__(self) -> str:
        return f"I18n(path={self.path}, locales={self.available_locales()})"
