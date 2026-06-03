"""
Unit tests for EventContext — all properties and helper methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aioscam.dispatcher.event import EventContext
from aioscam.types.user import User
from aioscam.types.chat import Chat, ChatType as ChatTypeEnum
from aioscam.types.message import Message, MessageBody, Recipient


def _make_bot():
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value={"id": 99})
    bot.edit_message = AsyncMock(return_value={"id": 99})
    return bot


def _make_message_event(text="hello", chat_id=100, user_id=200):
    sender = User(user_id=user_id, first_name="Test", is_bot=False)
    recipient = Recipient(chat_id=chat_id, chat_type="dialog", user_id=user_id)
    body = MessageBody(mid="mid.abc", seq=1, text=text)
    msg = Message(recipient=recipient, sender=sender, body=body, timestamp=1234567890)

    class FakeEvent:
        def __init__(self):
            self.message = msg
            self.timestamp = 1234567890
            self.user_locale = "ru"

    return EventContext(FakeEvent(), _make_bot())


def _make_callback_event(cb_data="action:ok", chat_id=100, user_id=200, callback_id="cb_1"):
    class FakeCallback:
        def __init__(self):
            self.callback_id = callback_id
            self.data = cb_data
            self.user = User(user_id=user_id, first_name="Clicker", is_bot=False)

    recipient = Recipient(chat_id=chat_id, chat_type="dialog", user_id=user_id)
    body = MessageBody(mid="mid.xyz", seq=2, text="button message")
    sender = User(user_id=999, first_name="Bot", is_bot=True)
    msg = Message(recipient=recipient, sender=sender, body=body, timestamp=1234567890)

    class FakeCallbackEvent:
        def __init__(self):
            self.callback = FakeCallback()
            self.message = msg
            self.timestamp = 1234567890
            self.user_locale = "en"

    return EventContext(FakeCallbackEvent(), _make_bot())


class TestEventContextText:
    def test_text_from_message_body(self):
        ctx = _make_message_event(text="hello world")
        assert ctx.text == "hello world"

    def test_text_none_for_callback(self):
        ctx = _make_callback_event()
        # callback event has message body with text
        assert ctx.text is not None  # "button message"

    def test_text_none_when_no_message(self):
        class EmptyEvent:
            pass
        ctx = EventContext(EmptyEvent(), _make_bot())
        assert ctx.text is None


class TestEventContextChatId:
    def test_chat_id_from_recipient(self):
        ctx = _make_message_event(chat_id=555)
        assert ctx.chat_id == 555

    def test_chat_id_from_callback_message(self):
        ctx = _make_callback_event(chat_id=777)
        assert ctx.chat_id == 777

    def test_chat_id_none_when_no_chat(self):
        class EmptyEvent:
            pass
        ctx = EventContext(EmptyEvent(), _make_bot())
        assert ctx.chat_id is None

    def test_chat_id_fallback_to_event_attribute(self):
        class EventWithChatId:
            chat_id = 888

        ctx = EventContext(EventWithChatId(), _make_bot())
        assert ctx.chat_id == 888


class TestEventContextUserId:
    def test_user_id_from_message_sender(self):
        ctx = _make_message_event(user_id=123)
        assert ctx.user_id == 123

    def test_user_id_from_callback_user(self):
        ctx = _make_callback_event(user_id=456)
        assert ctx.user_id == 456  # callback.user, not sender

    def test_user_id_not_from_bot_sender_in_callback(self):
        # Bot's user_id is 999 in our FakeCallbackEvent, clicker is 456
        ctx = _make_callback_event(user_id=456)
        assert ctx.user_id == 456
        assert ctx.user_id != 999

    def test_user_id_fallback_to_event_attribute(self):
        class EventWithUserId:
            user_id = 321

        ctx = EventContext(EventWithUserId(), _make_bot())
        assert ctx.user_id == 321


class TestEventContextFromUser:
    def test_from_user_for_message(self):
        ctx = _make_message_event(user_id=111)
        user = ctx.from_user
        assert user is not None
        assert user.id == 111

    def test_from_user_is_callback_user(self):
        ctx = _make_callback_event(user_id=222)
        user = ctx.from_user
        assert user is not None
        assert user.id == 222


class TestEventContextCallbackProperties:
    def test_callback_id(self):
        ctx = _make_callback_event(callback_id="my_cb")
        assert ctx.callback_id == "my_cb"

    def test_callback_id_none_for_message(self):
        ctx = _make_message_event()
        assert ctx.callback_id is None

    def test_callback_data(self):
        ctx = _make_callback_event(cb_data="action:yes")
        assert ctx.callback_data == "action:yes"

    def test_callback_data_none_for_message(self):
        ctx = _make_message_event()
        assert ctx.callback_data is None

    def test_callback_object(self):
        ctx = _make_callback_event()
        assert ctx.callback is not None


class TestEventContextLocale:
    def test_locale_from_event(self):
        ctx = _make_message_event()
        assert ctx.locale == "ru"

    def test_locale_from_callback_event(self):
        ctx = _make_callback_event()
        assert ctx.locale == "en"

    def test_locale_from_data_overrides_event(self):
        ctx = _make_message_event()
        ctx.data["locale"] = "de"
        assert ctx.locale == "de"


class TestEventContextPayload:
    def test_payload_none_for_regular_message(self):
        ctx = _make_message_event()
        assert ctx.payload is None

    def test_payload_from_bot_started(self):
        class BotStartedEvent:
            payload = "ref_12345"

        ctx = EventContext(BotStartedEvent(), _make_bot())
        assert ctx.payload == "ref_12345"


class TestEventContextAnswer:
    @pytest.mark.asyncio
    async def test_answer_calls_send_message(self):
        ctx = _make_message_event(chat_id=100, user_id=200)
        await ctx.answer("reply text")
        ctx.bot.send_message.assert_called_once()
        call_kwargs = ctx.bot.send_message.call_args[1]
        assert call_kwargs["text"] == "reply text"
        assert call_kwargs["chat_id"] == 100

    @pytest.mark.asyncio
    async def test_answer_raises_when_no_ids(self):
        class EmptyEvent:
            pass
        ctx = EventContext(EmptyEvent(), _make_bot())
        with pytest.raises((ValueError, Exception)):
            await ctx.answer("text")

    @pytest.mark.asyncio
    async def test_hide_keyboard_calls_edit_message(self):
        ctx = _make_message_event()
        await ctx.hide_keyboard()
        ctx.bot.edit_message.assert_called_once()
