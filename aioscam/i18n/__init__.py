"""
I18n — Internationalization support

Loads JSON translations and provides gettext-like API with automatic
locale detection from event.user_locale (Max API).
"""

from aioscam.i18n.i18n import I18n

__all__ = ["I18n"]
