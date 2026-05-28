"""
Tests for i18n module
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aioscam.i18n import I18n


# ============================================================
# I18n loading tests
# ============================================================

class TestI18nLoading:
    def test_load_translations(self):
        """Should load JSON translation files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create translation files
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({"greeting": "Hello"}, f)
            with open(Path(tmpdir) / "ru.json", "w") as f:
                json.dump({"greeting": "Привет"}, f)

            i18n = I18n(path=tmpdir, default_locale="en")
            assert "en" in i18n.available_locales()
            assert "ru" in i18n.available_locales()

    def test_missing_locales_directory(self):
        """Should handle missing locales directory gracefully"""
        i18n = I18n(path="/nonexistent/path", default_locale="en")
        assert i18n.available_locales() == []

    def test_invalid_json(self, caplog):
        """Should handle invalid JSON gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.json", "w") as f:
                f.write("{invalid json")

            i18n = I18n(path=tmpdir, default_locale="en")
            assert i18n.available_locales() == []
            assert "Failed to load" in caplog.text


# ============================================================
# I18n locale detection tests
# ============================================================

class TestI18nLocaleDetection:
    def setup_method(self):
        """Create i18n instance with test translations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({"greeting": "Hello"}, f)
            with open(Path(tmpdir) / "ru.json", "w") as f:
                json.dump({"greeting": "Привет"}, f)
            self.tmpdir = tmpdir
            self.i18n = I18n(path=tmpdir, default_locale="en")

    def _make_event(self, user_locale=None, data=None):
        """Create a mock event"""
        event = MagicMock()
        event.user_locale = user_locale
        event.data = data or {}
        return event

    def test_detect_locale_from_user_locale(self):
        """Should detect locale from event.user_locale"""
        event = self._make_event(user_locale="ru")
        assert self.i18n.get_locale(event) == "ru"

    def test_detect_locale_from_data(self):
        """Should detect locale from event.data['locale']"""
        event = self._make_event(user_locale="en", data={"locale": "ru"})
        assert self.i18n.get_locale(event) == "ru"

    def test_default_locale_fallback(self):
        """Should fallback to default locale if not found"""
        event = self._make_event(user_locale="unknown")
        assert self.i18n.get_locale(event) == "en"

    def test_unknown_locale_returns_default(self):
        """Should return default for unknown locale"""
        event = self._make_event(user_locale="de")
        assert self.i18n.get_locale(event) == "en"


# ============================================================
# I18n gettext tests
# ============================================================

class TestI18nGettext:
    def setup_method(self):
        """Create i18n instance with test translations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({
                    "greeting": "Hello!",
                    "welcome": "Welcome, {name}!",
                }, f)
            with open(Path(tmpdir) / "ru.json", "w") as f:
                json.dump({
                    "greeting": "Привет!",
                    "welcome": "Добро пожаловать, {name}!",
                }, f)
            self.tmpdir = tmpdir
            self.i18n = I18n(path=tmpdir, default_locale="en")

    def _make_event(self, user_locale="en"):
        event = MagicMock()
        event.user_locale = user_locale
        event.data = {}
        return event

    def test_gettext_english(self):
        """Should return English translation"""
        event = self._make_event(user_locale="en")
        assert self.i18n.gettext(event, "greeting") == "Hello!"

    def test_gettext_russian(self):
        """Should return Russian translation"""
        event = self._make_event(user_locale="ru")
        assert self.i18n.gettext(event, "greeting") == "Привет!"

    def test_gettext_with_formatting(self):
        """Should format translation with variables"""
        event = self._make_event(user_locale="en")
        assert self.i18n.gettext(event, "welcome", name="John") == "Welcome, John!"

    def test_gettext_with_formatting_russian(self):
        """Should format translation with variables in Russian"""
        event = self._make_event(user_locale="ru")
        assert self.i18n.gettext(event, "welcome", name="Иван") == "Добро пожаловать, Иван!"

    def test_gettext_missing_key(self):
        """Should return key if translation not found"""
        event = self._make_event(user_locale="en")
        assert self.i18n.gettext(event, "nonexistent") == "nonexistent"

    def test_call_alias(self):
        """Should work with i18n(event, key) alias"""
        event = self._make_event(user_locale="en")
        assert self.i18n(event, "greeting") == "Hello!"


# ============================================================
# I18n pluralization tests
# ============================================================

class TestI18nPluralization:
    def setup_method(self):
        """Create i18n instance with test translations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({
                    "one_item": "1 item",
                    "many_items": "{count} items",
                }, f)
            self.tmpdir = tmpdir
            self.i18n = I18n(path=tmpdir, default_locale="en")

    def _make_event(self, user_locale="en"):
        event = MagicMock()
        event.user_locale = user_locale
        event.data = {}
        return event

    def test_ngettext_singular(self):
        """Should return singular form for count=1"""
        event = self._make_event()
        assert self.i18n.ngettext(event, "one_item", "many_items", 1) == "1 item"

    def test_ngettext_plural(self):
        """Should return plural form for count>1"""
        event = self._make_event()
        assert self.i18n.ngettext(event, "one_item", "many_items", 5) == "5 items"

    def test_ngettext_zero(self):
        """Should return plural form for count=0"""
        event = self._make_event()
        assert self.i18n.ngettext(event, "one_item", "many_items", 0) == "0 items"


# ============================================================
# I18n repr tests
# ============================================================

class TestI18nRepr:
    def test_repr(self):
        """Should have useful repr"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({"key": "value"}, f)

            i18n = I18n(path=tmpdir, default_locale="en")
            repr_str = repr(i18n)
            assert "I18n" in repr_str
            assert "en" in repr_str
