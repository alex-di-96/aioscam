"""
Tests for Dispatcher._process_update routing, Update event property,
lifecycle event dispatching (bot_stopped, user_added, etc.).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam import Bot, Dispatcher
from aioscam.dispatcher.router import Router
from aioscam.dispatcher.event import EventContext
from aioscam.types.update import Update
from aioscam.types.user import User
from aioscam.types.message import Message, MessageBody, Recipient


# ─── Update.event property ───────────────────────────────────────────────────

class TestUpdateEventProperty:
    def test_message_created_returns_self(self):
        u = Update(update_type="message_created", timestamp=1)
        assert u.event is u

    def test_message_callback_returns_self(self):
        u = Update(update_type="message_callback", timestamp=1)
        assert u.event is u

    def test_bot_started_returns_self(self):
        u = Update(update_type="bot_started", timestamp=1)
        assert u.event is u

    def test_bot_stopped_returns_self(self):
        """Bug fix: was returning None for lifecycle events"""
        u = Update(update_type="bot_stopped", timestamp=1)
        assert u.event is u

    def test_bot_added_returns_self(self):
        u = Update(update_type="bot_added", timestamp=1)
        assert u.event is u

    def test_bot_removed_returns_self(self):
        u = Update(update_type="bot_removed", timestamp=1)
        assert u.event is u

    def test_user_added_returns_self(self):
        u = Update(update_type="user_added", timestamp=1)
        assert u.event is u

    def test_user_removed_returns_self(self):
        u = Update(update_type="user_removed", timestamp=1)
        assert u.event is u

    def test_message_edited_returns_self(self):
        u = Update(update_type="message_edited", timestamp=1)
        assert u.event is u

    def test_message_removed_returns_self(self):
        u = Update(update_type="message_removed", timestamp=1)
        assert u.event is u

    def test_message_chat_created_returns_self(self):
        u = Update(update_type="message_chat_created", timestamp=1)
        assert u.event is u

    def test_chat_title_changed_returns_self(self):
        u = Update(update_type="chat_title_changed", timestamp=1)
        assert u.event is u

    def test_dialog_cleared_returns_self(self):
        u = Update(update_type="dialog_cleared", timestamp=1)
        assert u.event is u

    def test_none_update_type_returns_none(self):
        u = Update(update_type=None)
        assert u.event is None

    def test_event_type_property(self):
        u = Update(update_type="message_created", timestamp=1)
        assert u.event_type == "message_created"


class TestUpdateProperties:
    def test_text_from_message_body(self):
        body = MessageBody(text="hello")
        recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
        sender = User(user_id=1, first_name="T", is_bot=False)
        msg = Message(recipient=recipient, sender=sender, body=body)
        u = Update(update_type="message_created", message=msg)
        assert u.text == "hello"

    def test_text_none_when_no_message(self):
        u = Update(update_type="bot_started")
        assert u.text is None

    def test_sender_from_message(self):
        sender = User(user_id=99, first_name="S", is_bot=False)
        recipient = Recipient(chat_id=1, chat_type="dialog", user_id=1)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody())
        u = Update(update_type="message_created", message=msg)
        assert u.sender.id == 99  # User.id is the field name; alias is user_id

    def test_sender_from_bot_started_user(self):
        user = User(user_id=42, first_name="U", is_bot=False)
        u = Update(update_type="bot_started", user=user)
        assert u.sender.id == 42

    def test_recipient_from_message(self):
        recipient = Recipient(chat_id=777, chat_type="dialog", user_id=1)
        sender = User(user_id=1, first_name="T", is_bot=False)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody())
        u = Update(update_type="message_created", message=msg)
        assert u.recipient.chat_id == 777

    def test_recipient_from_bot_started_chat_id(self):
        u = Update(update_type="bot_started", chat_id=555, user_id=42)
        assert u.recipient.chat_id == 555

    def test_update_id_from_timestamp(self):
        u = Update(update_type="message_created", timestamp=9999)
        assert u.update_id == 9999


# ─── Dispatcher._process_update routing ──────────────────────────────────────

def _make_bot():
    bot = Bot(token="test_token")
    bot._client.request = AsyncMock(return_value=MagicMock(result={}, ok=True))
    return bot


class TestDispatcherProcessUpdate:

    @pytest.mark.asyncio
    async def test_message_created_routes_to_process_message(self):
        dp = Dispatcher()
        results = []

        @dp.message_created()
        async def h(event):
            results.append("message_created")
            return "ok"

        sender = User(user_id=1, first_name="T", is_bot=False)
        recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody(text="hi"))
        update = Update(update_type="message_created", message=msg)

        await dp._process_update(_make_bot(), update)
        assert "message_created" in results

    @pytest.mark.asyncio
    async def test_message_callback_routes_to_process_callback(self):
        dp = Dispatcher()
        results = []

        @dp.callback_query()
        async def h(event):
            results.append("callback")
            return "ok"

        update = Update(
            update_type="message_callback",
            callback={"callback_id": "cb1", "data": "test"},
            timestamp=1,
        )
        await dp._process_update(_make_bot(), update)
        assert "callback" in results

    @pytest.mark.asyncio
    async def test_bot_started_routes_to_process_event(self):
        dp = Dispatcher()
        results = []

        @dp.bot_started()
        async def h(event):
            results.append("bot_started")
            return "ok"

        update = Update(
            update_type="bot_started",
            user=User(user_id=42, first_name="U", is_bot=False),
            chat_id=10,
        )
        await dp._process_update(_make_bot(), update)
        assert "bot_started" in results

    @pytest.mark.asyncio
    async def test_bot_stopped_routes_to_process_event(self):
        """Bug fix: bot_stopped must now fire handler (was blocked by Update.event returning None)"""
        dp = Dispatcher()
        results = []

        @dp.bot_stopped()
        async def h(event):
            results.append("bot_stopped")
            return "ok"

        update = Update(update_type="bot_stopped", timestamp=1)
        await dp._process_update(_make_bot(), update)
        assert "bot_stopped" in results

    @pytest.mark.asyncio
    async def test_user_added_routes_to_process_event(self):
        dp = Dispatcher()
        results = []

        @dp.user_added()
        async def h(event):
            results.append("user_added")
            return "ok"

        update = Update(update_type="user_added", timestamp=1)
        await dp._process_update(_make_bot(), update)
        assert "user_added" in results

    @pytest.mark.asyncio
    async def test_message_edited_routes_to_process_event(self):
        dp = Dispatcher()
        results = []

        @dp.message_edited()
        async def h(event):
            results.append("message_edited")
            return "ok"

        sender = User(user_id=1, first_name="T", is_bot=False)
        recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody(text="edited"))
        update = Update(update_type="message_edited", message=msg)
        await dp._process_update(_make_bot(), update)
        assert "message_edited" in results

    @pytest.mark.asyncio
    async def test_unknown_event_type_no_crash(self):
        dp = Dispatcher()
        update = Update(update_type="future_event_type", timestamp=1)
        # Should not raise — just log warning
        await dp._process_update(_make_bot(), update)

    @pytest.mark.asyncio
    async def test_none_update_type_no_crash(self):
        dp = Dispatcher()
        update = Update(update_type=None)
        await dp._process_update(_make_bot(), update)


# ─── Dispatcher state injection in process_message ───────────────────────────

class TestDispatcherStateInjection:

    @pytest.mark.asyncio
    async def test_state_injected_into_event_data(self):
        dp = Dispatcher()
        captured = {}

        @dp.message_created()
        async def h(event):
            captured["state"] = event.data.get("state")
            return "ok"

        sender = User(user_id=1, first_name="T", is_bot=False)
        recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody(text="hi"))

        class FakeEvent:
            message = msg
            text = "hi"
            data = {}

        context = EventContext(FakeEvent(), _make_bot())
        await dp.process_message(context)

        assert "state" in captured
        assert captured["state"] is not None

    @pytest.mark.asyncio
    async def test_state_guard_blocks_unknown_command_during_fsm(self):
        from aioscam.fsm.memory import MemoryStorage
        from aioscam.dispatcher.state import StateContext

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        results = []

        @dp.message_created()
        async def h(event):
            results.append("reached")
            return "ok"

        # Pre-set state so guard triggers
        await storage.set_state(10, "Form:step1", user_id=1)

        sender = User(user_id=1, first_name="T", is_bot=False)
        recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody(text="/unknown"))

        class FakeEvent:
            message = msg
            text = "/unknown"
            data = {}

        bot = _make_bot()
        bot.send_message = AsyncMock(return_value={})
        context = EventContext(FakeEvent(), bot)

        result = await dp.process_message(context)
        # Handler must be blocked, send_message with hint must be called
        assert result is None
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_guard_allows_cancel_command_during_fsm(self):
        from aioscam.fsm.memory import MemoryStorage

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        results = []

        @dp.message_created()
        async def h(event):
            results.append("cancel_reached")
            return "ok"

        await storage.set_state(10, "Form:step1", user_id=1)

        sender = User(user_id=1, first_name="T", is_bot=False)
        recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
        msg = Message(recipient=recipient, sender=sender, body=MessageBody(text="/cancel"))

        class FakeEvent:
            message = msg
            text = "/cancel"
            data = {}

        context = EventContext(FakeEvent(), _make_bot())
        await dp.process_message(context)
        assert "cancel_reached" in results


# ─── Dispatcher.stop_polling / stop_webhook ──────────────────────────────────

class TestDispatcherControls:
    @pytest.mark.asyncio
    async def test_stop_polling_sets_flag(self):
        dp = Dispatcher()
        dp._running = True
        await dp.stop_polling()
        assert dp._running is False

    def test_stop_webhook_sets_event(self):
        import asyncio
        dp = Dispatcher()
        dp._webhook_stop_event = asyncio.Event()
        dp.stop_webhook()
        assert dp._webhook_stop_event.is_set()

    def test_stop_webhook_no_event_no_crash(self):
        dp = Dispatcher()
        dp._webhook_stop_event = None
        dp.stop_webhook()  # should not raise
