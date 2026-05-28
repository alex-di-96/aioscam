"""
I18n storage and translation engine
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

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
        i18n = I18n(path="locales", default_locale="en")

        # In handler:
        @router.message_created(Command("start"))
        async def cmd_start(event, state):
            text = i18n.gettext(event, "greeting")
            # or: text = i18n(event, "greeting")
            await event.answer(text)

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
    ):
        """
        Initialize I18n

        Args:
            path: Path to locales directory
            default_locale: Default locale if user locale not found
            domain: Translation domain (filename without .json)
        """
        self.path = Path(path)
        self.default_locale = default_locale
        self.domain = domain
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files from the locales directory"""
        if not self.path.exists():
            logger.warning(f"Locales directory not found: {self.path}")
            return

        for file in self.path.glob(f"{self.domain}_*.json"):
            locale = file.stem.replace(f"{self.domain}_", "")
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self._translations[locale] = json.load(f)
                logger.info(f"Loaded locale '{locale}': {len(self._translations[locale])} keys")
            except Exception as e:
                logger.error(f"Failed to load locale '{locale}': {e}")

        # Also try loading without domain prefix (e.g., "en.json")
        if not self._translations:
            for file in self.path.glob("*.json"):
                locale = file.stem
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        self._translations[locale] = json.load(f)
                    logger.info(f"Loaded locale '{locale}': {len(self._translations[locale])} keys")
                except Exception as e:
                    logger.error(f"Failed to load locale '{locale}': {e}")

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
        locale = self.get_locale(event)
        translations = self._translations.get(locale, {})
        text = translations.get(key, translations.get(self.default_locale, {}).get(key, key))

        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass

        return text

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
