"""
Tests for:
- StartCommand filter (all match modes)
- ContentType filter
- AllFilter
- Scene class
- StateGuardMiddleware standalone
- I18n fallback locale (bug fix)
- create_group_deep_link URL encoding (bug fix)
- AiohttpWebhookHandler
- Bot.request_contact / Bot.request_location
- Bot.send_action / Bot.delete_message / Bot.get_messages
"""

import json
import tempfile
from pathlib import Path
from typing import Optional

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam import Bot
from aioscam.filters.builtin import StartCommand, ContentType, AllFilter, Command, Text
from aioscam.fsm.scene import Scene
from aioscam.middleware.manager import StateGuardMiddleware
from aioscam.dispatcher.event import EventContext
from aioscam.types.user import User
from aioscam.types.message import Message, MessageBody, Recipient
from aioscam.i18n.i18n import I18n
from aioscam.utils.deep_linking import create_group_deep_link, parse_deep_link
from aioscam.client.response import Response


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_event(text: Optional[str] = None, payload: Optional[str] = None):
    sender = User(user_id=1, first_name="T", is_bot=False)
    recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
    body = MessageBody(text=text)
    msg = Message(recipient=recipient, sender=sender, body=body)

    class FakeEvent:
        def __init__(self):
            self.message = msg
            self.payload = payload

        @property
        def text(self):
            return text

    return EventContext(FakeEvent(), MagicMock())


# ─── StartCommand filter ─────────────────────────────────────────────────────

class TestStartCommandFilter:

    @pytest.mark.asyncio
    async def test_any_payload_passes(self):
        f = StartCommand()
        event = _make_event(payload="some_payload")
        result = await f(event)
        assert result.passed is True
        assert result.data.get("start_payload") == "some_payload"

    @pytest.mark.asyncio
    async def test_no_payload_fails(self):
        f = StartCommand()
        event = _make_event()
        result = await f(event)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_equals_exact_match(self):
        f = StartCommand(equals="ref_123")
        event = _make_event(payload="ref_123")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_equals_no_match(self):
        f = StartCommand(equals="ref_123")
        event = _make_event(payload="ref_456")
        result = await f(event)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_startswith_match(self):
        f = StartCommand(startswith="ref_")
        event = _make_event(payload="ref_12345")
        result = await f(event)
        assert result.passed is True
        assert result.data["start_payload"] == "ref_12345"

    @pytest.mark.asyncio
    async def test_startswith_no_match(self):
        f = StartCommand(startswith="ref_")
        event = _make_event(payload="invite_abc")
        result = await f(event)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_contains_match(self):
        f = StartCommand(contains="promo")
        event = _make_event(payload="summer_promo_2026")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_contains_no_match(self):
        f = StartCommand(contains="promo")
        event = _make_event(payload="just_a_ref")
        result = await f(event)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_regex_match(self):
        f = StartCommand(regex=r"^user_\d+$")
        event = _make_event(payload="user_42")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_regex_no_match(self):
        f = StartCommand(regex=r"^user_\d+$")
        event = _make_event(payload="admin_42")
        result = await f(event)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_payload_from_start_command_text(self):
        """Repeat visits: /start <payload> in message text, no top-level payload"""
        f = StartCommand()
        event = _make_event(text="/start my_payload")
        result = await f(event)
        assert result.passed is True
        assert result.data["start_payload"] == "my_payload"

    @pytest.mark.asyncio
    async def test_bare_start_no_payload_fails(self):
        f = StartCommand()
        event = _make_event(text="/start")
        result = await f(event)
        assert result.passed is False


# ─── ContentType filter ──────────────────────────────────────────────────────

class TestContentTypeFilter:

    @pytest.mark.asyncio
    async def test_text_type_with_text(self):
        f = ContentType("text")
        event = _make_event(text="hello")
        result = await f(event)
        assert result.passed is True
        assert result.data.get("content_type") == "text"

    @pytest.mark.asyncio
    async def test_text_type_without_text(self):
        f = ContentType("text")
        event = _make_event()
        result = await f(event)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_list_of_types(self):
        f = ContentType(["text", "image"])
        event = _make_event(text="hello")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_no_message_fails(self):
        f = ContentType("text")

        class EmptyEvent:
            message = None
            data = {}

        result = await f(EmptyEvent())
        assert result.passed is False


# ─── AllFilter ───────────────────────────────────────────────────────────────

class TestAllFilter:

    @pytest.mark.asyncio
    async def test_always_passes_with_text(self):
        f = AllFilter()
        event = _make_event(text="anything")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_always_passes_without_text(self):
        f = AllFilter()
        event = _make_event()
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_always_passes_for_none_event(self):
        f = AllFilter()

        class Empty:
            pass

        result = await f(Empty())
        assert result.passed is True


# ─── Scene ───────────────────────────────────────────────────────────────────

class TestScene:

    def test_scene_name(self):
        s = Scene("registration")
        assert s.name == "registration"

    def test_handler_decorator_registers(self):
        s = Scene("test")

        @s.handler()
        async def step_one(self_, event):
            pass

        assert len(s.handlers) == 1

    @pytest.mark.asyncio
    async def test_start_sets_event(self):
        s = Scene("test")
        event = _make_event(text="hello")
        await s.start(event, data={"key": "value"})
        assert s.event is event
        assert s._data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_update_data(self):
        s = Scene("test")
        await s.update_data(name="Alice", age=25)
        assert s._data["name"] == "Alice"
        assert s._data["age"] == 25

    def test_get_data_returns_copy(self):
        s = Scene("test")
        s._data = {"x": 1}
        data = s.get_data()
        data["x"] = 99
        assert s._data["x"] == 1  # original unchanged

    @pytest.mark.asyncio
    async def test_next_does_not_raise(self):
        s = Scene("test")
        await s.next()  # should be no-op without error

    @pytest.mark.asyncio
    async def test_start_default_data_is_empty(self):
        s = Scene("test")
        await s.start(_make_event())
        assert s._data == {}


# ─── StateGuardMiddleware ─────────────────────────────────────────────────────

class TestStateGuardMiddleware:

    @pytest.mark.asyncio
    async def test_non_command_passes_through(self):
        mw = StateGuardMiddleware()
        handler = AsyncMock(return_value="ok")
        event = _make_event(text="hello world")
        result = await mw(event, handler)
        assert result == "ok"
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_allowed_command_passes_through(self):
        mw = StateGuardMiddleware()
        handler = AsyncMock(return_value="ok")
        event = _make_event(text="/cancel")
        result = await mw(event, handler)
        assert result == "ok"
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_allowed_start_passes_through(self):
        mw = StateGuardMiddleware()
        handler = AsyncMock(return_value="ok")
        event = _make_event(text="/start")
        result = await mw(event, handler)
        assert result == "ok"
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_command_with_no_state_passes(self):
        mw = StateGuardMiddleware()
        handler = AsyncMock(return_value="ok")

        state_ctx = AsyncMock()
        state_ctx.get_state = AsyncMock(return_value=None)

        class FakeEvent:
            text = "/unknown"
            data = {"state": state_ctx}

        result = await mw(FakeEvent(), handler)
        assert result == "ok"
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_command_with_active_state_blocks(self):
        mw = StateGuardMiddleware(hints={"Form:step": "введите имя"})

        state_ctx = AsyncMock()
        state_ctx.get_state = AsyncMock(return_value="Form:step")

        answer_called = []

        class FakeEvent:
            text = "/badcmd"
            data = {"state": state_ctx}

            async def answer(self, text):
                answer_called.append(text)

        handler = AsyncMock(return_value="ok")
        result = await mw(FakeEvent(), handler)

        assert result is None
        handler.assert_not_called()
        assert len(answer_called) == 1
        assert "введите имя" in answer_called[0]

    @pytest.mark.asyncio
    async def test_custom_hint_displayed(self):
        mw = StateGuardMiddleware(hints={"Order:amount": "введите сумму"})

        state_ctx = AsyncMock()
        state_ctx.get_state = AsyncMock(return_value="Order:amount")
        answer_msgs = []

        class FakeEvent:
            text = "/stats"
            data = {"state": state_ctx}

            async def answer(self, text):
                answer_msgs.append(text)

        await mw(FakeEvent(), AsyncMock())
        assert any("введите сумму" in m for m in answer_msgs)

    @pytest.mark.asyncio
    async def test_default_hint_when_no_hint_for_state(self):
        mw = StateGuardMiddleware()  # no hints
        state_ctx = AsyncMock()
        state_ctx.get_state = AsyncMock(return_value="UnknownState:step")
        answer_msgs = []

        class FakeEvent:
            text = "/foobar"
            data = {"state": state_ctx}

            async def answer(self, text):
                answer_msgs.append(text)

        await mw(FakeEvent(), AsyncMock())
        assert len(answer_msgs) == 1
        assert "ожидаемые данные" in answer_msgs[0] or "Введите" in answer_msgs[0]


# ─── I18n fallback locale (bug fix) ─────────────────────────────────────────

class TestI18nFallback:
    """Bug fix: gettext fallback to default locale when key absent in requested locale"""

    def _make_i18n(self, tmpdir):
        en_data = {"greeting": "Hello!", "only_en": "English only"}
        ru_data = {"greeting": "Привет!"}
        with open(Path(tmpdir) / "en.json", "w") as f:
            json.dump(en_data, f)
        with open(Path(tmpdir) / "ru.json", "w") as f:
            json.dump(ru_data, f)
        return I18n(path=tmpdir, default_locale="en")

    def _event(self, locale):
        ev = MagicMock()
        ev.user_locale = locale
        ev.data = {}
        return ev

    def test_existing_key_in_locale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            i18n = self._make_i18n(tmpdir)
            ev = self._event("ru")
            assert i18n.gettext(ev, "greeting") == "Привет!"

    def test_fallback_to_default_locale_for_missing_key(self):
        """Bug fix: was returning key itself instead of default locale translation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            i18n = self._make_i18n(tmpdir)
            ev = self._event("ru")
            result = i18n.gettext(ev, "only_en")
            assert result == "English only"  # must fall back to English

    def test_returns_key_when_missing_everywhere(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            i18n = self._make_i18n(tmpdir)
            ev = self._event("ru")
            result = i18n.gettext(ev, "totally_missing_key")
            assert result == "totally_missing_key"

    @pytest.mark.asyncio
    async def test_reload_updates_translations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({"key": "old"}, f)
            i18n = I18n(path=tmpdir, default_locale="en", lazy=True)
            await i18n.reload()
            ev = self._event("en")
            assert i18n.gettext(ev, "key") == "old"

            # Update file and reload
            with open(Path(tmpdir) / "en.json", "w") as f:
                json.dump({"key": "new"}, f)
            await i18n.reload()
            assert i18n.gettext(ev, "key") == "new"


# ─── create_group_deep_link URL encoding (bug fix) ───────────────────────────

class TestGroupDeepLinkEncoding:

    def test_group_link_without_payload(self):
        url = create_group_deep_link("bot", 99)
        assert url == "https://max.ru/bot?add_to_group=99"

    def test_group_link_payload_url_encoded(self):
        """Bug fix: was not calling quote() on payload"""
        url = create_group_deep_link("bot", 99, "hello world")
        assert "hello%20world" in url or "hello+world" in url
        assert "hello world" not in url

    def test_group_link_special_chars_encoded(self):
        url = create_group_deep_link("bot", 99, "a=1&b=2")
        assert "a=1&b=2" not in url  # must be encoded

    def test_group_link_payload_roundtrip(self):
        original = "user=42&type=join"
        url = create_group_deep_link("bot", 99, original)
        parsed = parse_deep_link(url)
        assert parsed["payload"] == original
        assert parsed["group_id"] == 99


# ─── AiohttpWebhookHandler ───────────────────────────────────────────────────

class TestAiohttpWebhookHandler:

    def _make_handler(self, secret=None):
        from aioscam.webhook.aiohttp import AiohttpWebhookHandler
        bot = Bot(token="test_token")
        from aioscam import Dispatcher
        dp = Dispatcher()
        return AiohttpWebhookHandler(bot, dp, secret_token=secret)

    @pytest.mark.asyncio
    async def test_valid_request_returns_ok(self):
        handler = self._make_handler()
        handler.dispatcher._process_update = AsyncMock()

        sender_data = {"user_id": 1, "name": "T", "first_name": "T", "is_bot": False}
        recipient_data = {"chat_id": 10, "chat_type": "dialog", "user_id": 1}
        body_data = {"text": "hi"}
        msg_data = {"recipient": recipient_data, "sender": sender_data, "body": body_data}
        update_data = {"update_type": "message_created", "message": msg_data, "timestamp": 1}

        request = MagicMock()
        request.json = AsyncMock(return_value=update_data)
        request.remote = "127.0.0.1"

        response = await handler.handle(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_secret_token_valid(self):
        handler = self._make_handler(secret="my_secret")
        handler.dispatcher._process_update = AsyncMock()

        update_data = {"update_type": "bot_started", "timestamp": 1}
        request = MagicMock()
        request.json = AsyncMock(return_value=update_data)
        request.headers = {"X-Max-Secret-Token": "my_secret"}
        request.remote = "127.0.0.1"

        response = await handler.handle(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_secret_token_invalid_returns_401(self):
        handler = self._make_handler(secret="my_secret")

        request = MagicMock()
        request.headers = {"X-Max-Secret-Token": "wrong_secret"}
        request.remote = "127.0.0.1"

        response = await handler.handle(request)
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_no_secret_skips_validation(self):
        handler = self._make_handler(secret=None)
        handler.dispatcher._process_update = AsyncMock()

        update_data = {"update_type": "bot_started", "timestamp": 1}
        request = MagicMock()
        request.json = AsyncMock(return_value=update_data)
        request.headers = {}
        request.remote = "127.0.0.1"

        response = await handler.handle(request)
        assert response.status == 200

    @pytest.mark.asyncio
    async def test_exception_returns_500(self):
        handler = self._make_handler()
        request = MagicMock()
        request.headers = {}
        request.json = AsyncMock(side_effect=Exception("bad json"))
        request.remote = "127.0.0.1"

        response = await handler.handle(request)
        assert response.status == 500


# ─── Bot.request_contact / Bot.request_location ──────────────────────────────

class TestBotRequestContactLocation:

    @pytest.mark.asyncio
    async def test_request_contact_sends_keyboard(self):
        bot = Bot(token="test")
        bot.send_message = AsyncMock(return_value={"id": 1})

        await bot.request_contact(chat_id=10, text="Share contact")

        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 10
        assert call_kwargs["text"] == "Share contact"
        assert call_kwargs["keyboard"] is not None
        keyboard = call_kwargs["keyboard"]
        # bot.request_contact uses KeyboardBuilder() (regular Keyboard, not InlineKeyboard)
        # Keyboard.to_dict() → {"buttons": [[{"text": ..., "type": "request_contact"}]]}
        buttons = keyboard.get("buttons", [[]])
        assert any(
            btn.get("type") == "request_contact"
            for row in buttons for btn in row
        )

    @pytest.mark.asyncio
    async def test_request_location_sends_keyboard(self):
        bot = Bot(token="test")
        bot.send_message = AsyncMock(return_value={"id": 1})

        await bot.request_location(chat_id=10)

        call_kwargs = bot.send_message.call_args.kwargs
        keyboard = call_kwargs["keyboard"]
        buttons = keyboard.get("buttons", [[]])
        assert any(
            btn.get("type") == "request_geo_location"
            for row in buttons for btn in row
        )

    @pytest.mark.asyncio
    async def test_request_contact_custom_button_text(self):
        bot = Bot(token="test")
        bot.send_message = AsyncMock(return_value={"id": 1})

        await bot.request_contact(chat_id=10, button_text="Поделиться")

        call_kwargs = bot.send_message.call_args.kwargs
        keyboard = call_kwargs["keyboard"]
        buttons = keyboard.get("buttons", [[]])
        assert any(
            btn.get("text") == "Поделиться"
            for row in buttons for btn in row
        )


# ─── Bot.send_action / Bot.delete_message / Bot.get_messages ─────────────────

class TestBotMiscMethods:

    @pytest.mark.asyncio
    async def test_send_action(self):
        from aioscam.enums import SenderAction
        bot = Bot(token="test")
        bot._client.request = AsyncMock(return_value=Response(ok=True, result={}))

        await bot.send_action(chat_id=10, action=SenderAction.TYPING_ON)

        call_args = bot._client.request.call_args
        # Path is now /chats/{chat_id}/actions — chat_id is in the URL, not the body
        path = call_args.args[0] if call_args.args else call_args.kwargs.get("path", "")
        assert "10" in path
        assert "actions" in path
        body = call_args.kwargs.get("body", {})
        assert body.get("action") == SenderAction.TYPING_ON.value

    @pytest.mark.asyncio
    async def test_delete_message(self):
        bot = Bot(token="test")
        bot._client.request = AsyncMock(return_value=Response(ok=True, result={}))

        result = await bot.delete_message(message_id="mid.abc")

        assert result is True
        call_args = bot._client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("message_id") == "mid.abc"

    @pytest.mark.asyncio
    async def test_get_messages(self):
        bot = Bot(token="test")
        messages_list = [{"id": 1}, {"id": 2}]
        bot._client.request = AsyncMock(return_value=Response(ok=True, result=messages_list))

        result = await bot.get_messages(chat_id=10)

        assert result == messages_list
        call_args = bot._client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("chat_id") == 10

    @pytest.mark.asyncio
    async def test_get_messages_empty_returns_list(self):
        bot = Bot(token="test")
        bot._client.request = AsyncMock(return_value=Response(ok=True, result=None))
        result = await bot.get_messages(chat_id=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_message_single(self):
        bot = Bot(token="test")
        bot._client.request = AsyncMock(return_value=Response(ok=True, result={"id": 42}))
        result = await bot.get_message(message_id="mid.42")
        assert result == {"id": 42}

    @pytest.mark.asyncio
    async def test_bot_context_manager(self):
        bot = Bot(token="test")
        bot.close = AsyncMock()
        async with bot as b:
            assert b is bot
        bot.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_me_from_chat(self):
        bot = Bot(token="test")
        bot._client.request = AsyncMock(return_value=Response(ok=True, result={}))

        result = await bot.delete_me_from_chat(chat_id=10)

        assert result is True

    @pytest.mark.asyncio
    async def test_kick_chat_member_alias(self):
        bot = Bot(token="test")
        bot._client.request = AsyncMock(return_value=Response(ok=True, result={}))

        result = await bot.kick_chat_member(chat_id=10, user_id=99)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_webhook_deprecated_warning(self):
        import warnings
        bot = Bot(token="test")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            bot.delete_webhook()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
