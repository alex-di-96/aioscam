"""
Extended tests for utils: TextFormat, KeyboardBuilder, deep_linking.
"""

import pytest
from aioscam.utils.formatting import TextFormat, Bold, Italic, Code, Pre, Link, Mention
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.utils.deep_linking import create_deep_link, create_group_deep_link, parse_deep_link
from aioscam.types.keyboard import InlineKeyboard, CallbackButton, LinkButton
from aioscam.enums import ButtonType


# ─── TextFormat ──────────────────────────────────────────────────────────────

class TestTextFormat:
    def test_bold(self):
        assert TextFormat.bold("text") == "**text**"

    def test_italic(self):
        assert TextFormat.italic("text") == "_text_"

    def test_underline(self):
        assert TextFormat.underline("text") == "__text__"

    def test_italic_differs_from_underline(self):
        assert TextFormat.italic("x") != TextFormat.underline("x")

    def test_strikethrough(self):
        assert TextFormat.strikethrough("text") == "~~text~~"

    def test_code(self):
        assert TextFormat.code("x = 1") == "`x = 1`"

    def test_pre_no_language(self):
        assert TextFormat.pre("code") == "```\ncode\n```"

    def test_pre_with_language(self):
        result = TextFormat.pre("x = 1", "python")
        assert result == "```python\nx = 1\n```"

    def test_link(self):
        assert TextFormat.link("click", "https://example.com") == "[click](https://example.com)"

    def test_mention(self):
        assert TextFormat.mention("User", 123) == "[User](user://123)"

    def test_aliases(self):
        assert Bold("hi") == TextFormat.bold("hi")
        assert Italic("hi") == TextFormat.italic("hi")
        assert Code("hi") == TextFormat.code("hi")
        assert Pre("hi") == TextFormat.pre("hi")
        assert Link("hi", "u") == TextFormat.link("hi", "u")
        assert Mention("hi", 1) == TextFormat.mention("hi", 1)

    def test_nested_bold_italic(self):
        result = TextFormat.bold(TextFormat.italic("text"))
        assert result == "**_text_**"

    def test_empty_string(self):
        assert TextFormat.bold("") == "****"
        assert TextFormat.italic("") == "__"


# ─── KeyboardBuilder ─────────────────────────────────────────────────────────

class TestKeyboardBuilder:
    def test_single_callback_button(self):
        kb = KeyboardBuilder().callback("Click", "data:1").build()
        assert len(kb.buttons) == 1
        assert len(kb.buttons[0]) == 1
        assert kb.buttons[0][0].callback_data == "data:1"

    def test_multiple_buttons_in_one_row(self):
        kb = (
            KeyboardBuilder()
            .callback("A", "a")
            .callback("B", "b")
            .build()
        )
        assert len(kb.buttons) == 1
        assert len(kb.buttons[0]) == 2

    def test_row_separator(self):
        kb = (
            KeyboardBuilder()
            .callback("A", "a")
            .row()
            .callback("B", "b")
            .build()
        )
        assert len(kb.buttons) == 2
        assert len(kb.buttons[0]) == 1
        assert len(kb.buttons[1]) == 1

    def test_link_button(self):
        kb = KeyboardBuilder().link("Open", "https://example.com").build()
        btn = kb.buttons[0][0]
        assert btn.url == "https://example.com"
        assert btn.type == ButtonType.LINK

    def test_request_contact_button(self):
        kb = KeyboardBuilder().request_contact("Share").build()
        btn = kb.buttons[0][0]
        assert btn.type == ButtonType.REQUEST_CONTACT

    def test_request_location_button(self):
        kb = KeyboardBuilder().request_location("Share Location").build()
        btn = kb.buttons[0][0]
        assert btn.type == ButtonType.REQUEST_GEO_LOCATION

    def test_clipboard_button(self):
        kb = KeyboardBuilder().clipboard("Copy", "text to copy").build()
        btn = kb.buttons[0][0]
        assert btn.type == ButtonType.CLIPBOARD
        assert btn.payload == "text to copy"

    def test_empty_row_not_added(self):
        kb = (
            KeyboardBuilder()
            .row()  # empty row before any buttons
            .callback("X", "x")
            .build()
        )
        # Empty row() call should not add empty row
        assert len(kb.buttons) == 1

    def test_reset_clears_state(self):
        builder = KeyboardBuilder()
        builder.callback("A", "a")
        builder.reset()
        kb = builder.build()
        assert len(kb.buttons) == 0

    def test_chaining_returns_self(self):
        builder = KeyboardBuilder()
        result = builder.callback("X", "x")
        assert result is builder

    def test_inline_keyboard_type(self):
        kb = KeyboardBuilder(inline=True).callback("Click", "x").build()
        assert isinstance(kb, InlineKeyboard)


class TestInlineKeyboardToDict:
    def test_callback_button_structure(self):
        kb = KeyboardBuilder(inline=True).callback("Click me", "action:test").build()
        d = kb.to_dict()
        assert d["type"] == "inline_keyboard"
        buttons = d["payload"]["buttons"]
        assert len(buttons) == 1
        btn = buttons[0][0]
        assert btn["text"] == "Click me"
        assert btn["type"] == "callback"
        assert btn["payload"] == "action:test"

    def test_link_button_structure(self):
        kb = KeyboardBuilder(inline=True).link("Visit", "https://max.ru").build()
        d = kb.to_dict()
        btn = d["payload"]["buttons"][0][0]
        assert btn["type"] == "link"
        assert btn["url"] == "https://max.ru"

    def test_multi_row_structure(self):
        kb = (
            KeyboardBuilder(inline=True)
            .callback("Row1", "r1")
            .row()
            .callback("Row2", "r2")
            .build()
        )
        d = kb.to_dict()
        rows = d["payload"]["buttons"]
        assert len(rows) == 2


# ─── Deep linking ────────────────────────────────────────────────────────────

class TestDeepLinking:
    def test_create_simple_deep_link(self):
        url = create_deep_link("my_bot", "ref_123")
        assert url == "https://max.ru/my_bot?start=ref_123"

    def test_create_deep_link_url_encodes_payload(self):
        url = create_deep_link("my_bot", "hello world")
        assert "hello%20world" in url or "hello+world" in url

    def test_create_deep_link_encodes_special_chars(self):
        url = create_deep_link("bot", "a=1&b=2")
        assert "a=1&b=2" not in url  # must be encoded

    def test_create_group_deep_link(self):
        url = create_group_deep_link("my_bot", 12345)
        assert "add_to_group=12345" in url

    def test_create_group_deep_link_with_payload(self):
        url = create_group_deep_link("my_bot", 12345, "payload")
        assert "start=" in url
        assert "add_to_group=12345" in url

    def test_parse_simple_deep_link(self):
        result = parse_deep_link("https://max.ru/my_bot?start=ref_123")
        assert result["bot_username"] == "my_bot"
        assert result["payload"] == "ref_123"
        assert result["group_id"] is None

    def test_parse_deep_link_decodes_payload(self):
        result = parse_deep_link("https://max.ru/bot?start=hello%20world")
        assert result["payload"] == "hello world"

    def test_parse_group_deep_link(self):
        result = parse_deep_link("https://max.ru/my_bot?add_to_group=999&start=x")
        assert result["group_id"] == 999
        assert result["payload"] == "x"

    def test_parse_invalid_url_returns_nones(self):
        result = parse_deep_link("https://other.com/bot?start=x")
        assert result["bot_username"] is None
        assert result["payload"] is None

    def test_roundtrip(self):
        original = "ref_12345"
        url = create_deep_link("bot", original)
        parsed = parse_deep_link(url)
        assert parsed["payload"] == original

    def test_roundtrip_special_chars(self):
        original = "user=42&type=join"
        url = create_deep_link("bot", original)
        parsed = parse_deep_link(url)
        assert parsed["payload"] == original
