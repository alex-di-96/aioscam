"""
Tests for v0.1.5 features:
- New event decorators (11 types)
- set_my_commands()
- hide_keyboard() / answer_and_hide_keyboard()
- edit_message(message_id) — chat_id optional
- delete_pin_message(chat_id)
- StateGuard configuration
- ClipboardButton payload
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam import Bot, Dispatcher, Router, Command, F, BotCommand
from aioscam.dispatcher.event import EventContext
from aioscam.dispatcher.router import Router as RouterClass
from aioscam.fsm import State, StatesGroup, MemoryStorage
from aioscam.types.keyboard import ClipboardButton
from aioscam.types.update import Update, MessageCreated, BotStarted
from aioscam.types.user import User
from aioscam.types.chat import Chat, ChatType as ChatTypeEnum
from aioscam.types.message import Message, MessageBody, Recipient
from aioscam.utils.keyboard import KeyboardBuilder


def _make_bot():
    bot = Bot(token="test_token")
    bot._client.request = AsyncMock(return_value=MagicMock(result={}, ok=True))
    return bot


class TestNewEventDecorators:
    """Test all 11 new event decorators"""

    @pytest.mark.asyncio
    async def test_bot_started_decorator(self):
        """Test @router.bot_started()"""
        router = RouterClass()
        called = []

        @router.bot_started()
        async def handler(event):
            called.append(True)
            return "bot_started_handler"

        assert 'bot_started' in router._event_handlers
        assert len(router._event_handlers['bot_started']) == 1

    @pytest.mark.asyncio
    async def test_bot_stopped_decorator(self):
        """Test @router.bot_stopped()"""
        router = RouterClass()

        @router.bot_stopped()
        async def handler(event):
            return "bot_stopped_handler"

        assert 'bot_stopped' in router._event_handlers
        assert len(router._event_handlers['bot_stopped']) == 1

    @pytest.mark.asyncio
    async def test_bot_added_decorator(self):
        """Test @router.bot_added()"""
        router = RouterClass()

        @router.bot_added()
        async def handler(event):
            return "bot_added_handler"

        assert 'bot_added' in router._event_handlers
        assert len(router._event_handlers['bot_added']) == 1

    @pytest.mark.asyncio
    async def test_bot_removed_decorator(self):
        """Test @router.bot_removed()"""
        router = RouterClass()

        @router.bot_removed()
        async def handler(event):
            return "bot_removed_handler"

        assert 'bot_removed' in router._event_handlers
        assert len(router._event_handlers['bot_removed']) == 1

    @pytest.mark.asyncio
    async def test_message_chat_created_decorator(self):
        """Test @router.message_chat_created()"""
        router = RouterClass()

        @router.message_chat_created()
        async def handler(event):
            return "chat_created_handler"

        assert 'message_chat_created' in router._event_handlers
        assert len(router._event_handlers['message_chat_created']) == 1

    @pytest.mark.asyncio
    async def test_chat_title_changed_decorator(self):
        """Test @router.chat_title_changed()"""
        router = RouterClass()

        @router.chat_title_changed()
        async def handler(event):
            return "title_changed_handler"

        assert 'chat_title_changed' in router._event_handlers
        assert len(router._event_handlers['chat_title_changed']) == 1

    @pytest.mark.asyncio
    async def test_dialog_cleared_decorator(self):
        """Test @router.dialog_cleared()"""
        router = RouterClass()

        @router.dialog_cleared()
        async def handler(event):
            return "dialog_cleared_handler"

        assert 'dialog_cleared' in router._event_handlers
        assert len(router._event_handlers['dialog_cleared']) == 1

    @pytest.mark.asyncio
    async def test_dialog_muted_decorator(self):
        """Test @router.dialog_muted()"""
        router = RouterClass()

        @router.dialog_muted()
        async def handler(event):
            return "dialog_muted_handler"

        assert 'dialog_muted' in router._event_handlers
        assert len(router._event_handlers['dialog_muted']) == 1

    @pytest.mark.asyncio
    async def test_dialog_unmuted_decorator(self):
        """Test @router.dialog_unmuted()"""
        router = RouterClass()

        @router.dialog_unmuted()
        async def handler(event):
            return "dialog_unmuted_handler"

        assert 'dialog_unmuted' in router._event_handlers
        assert len(router._event_handlers['dialog_unmuted']) == 1

    @pytest.mark.asyncio
    async def test_user_added_decorator(self):
        """Test @router.user_added()"""
        router = RouterClass()

        @router.user_added()
        async def handler(event):
            return "user_added_handler"

        assert 'user_added' in router._event_handlers
        assert len(router._event_handlers['user_added']) == 1

    @pytest.mark.asyncio
    async def test_user_removed_decorator(self):
        """Test @router.user_removed()"""
        router = RouterClass()

        @router.user_removed()
        async def handler(event):
            return "user_removed_handler"

        assert 'user_removed' in router._event_handlers
        assert len(router._event_handlers['user_removed']) == 1


class TestSetMyCommands:
    """Test set_my_commands() method"""

    @pytest.mark.asyncio
    async def test_set_my_commands(self):
        """Test set_my_commands sends correct request"""
        from aioscam.client.client import AioScamClient
        from aioscam.client.response import Response

        client = AsyncMock()
        client.request = AsyncMock(return_value=Response(
            ok=True,
            result={"name": "TestBot", "commands": [{"name": "start", "description": "Start"}]}
        ))

        bot = Bot(token="test")
        bot._client = client

        commands = [
            BotCommand(name="start", description="Запуск бота"),
            BotCommand(name="help", description="Помощь"),
        ]

        result = await bot.set_my_commands(commands)

        client.request.assert_called_once()
        call_args = client.request.call_args
        assert call_args.kwargs.get("method").value == "PATCH"
        expected_body = {"commands": [{"name": "start", "description": "Запуск бота"}, {"name": "help", "description": "Помощь"}]}
        assert call_args.kwargs.get("body") == expected_body
        assert result["name"] == "TestBot"


class TestHideKeyboard:
    """Test hide_keyboard() and answer_and_hide_keyboard()"""

    @pytest.mark.asyncio
    async def test_hide_keyboard(self):
        """Test event.hide_keyboard() calls edit_message without keyboard"""
        sender = User(user_id=123, first_name="Test", is_bot=False)
        recipient = Recipient(chat_id=456, chat_type="dialog", user_id=789)
        body = MessageBody(mid="mid.abc123", text="Hello")
        msg = Message(recipient=recipient, sender=sender, body=body)

        class FakeEvent:
            def __init__(self):
                self.message = msg
                self.timestamp = 1776345558644
                self.update_type = "message_created"

        bot = MagicMock()
        bot.edit_message = AsyncMock(return_value={"ok": True})

        context = EventContext(FakeEvent(), bot)

        await context.hide_keyboard()

        bot.edit_message.assert_called_once()
        call_kwargs = bot.edit_message.call_args.kwargs
        assert call_kwargs["message_id"] == "mid.abc123"
        assert call_kwargs["keyboard"] is None

    @pytest.mark.asyncio
    async def test_answer_and_hide_keyboard_with_text(self):
        """Test answer_and_hide_keyboard with new text"""
        sender = User(user_id=123, first_name="Test", is_bot=False)
        recipient = Recipient(chat_id=456, chat_type="dialog", user_id=789)
        body = MessageBody(mid="mid.xyz", text="Original")
        msg = Message(recipient=recipient, sender=sender, body=body)

        class FakeEvent:
            def __init__(self):
                self.message = msg

        bot = MagicMock()
        bot.edit_message = AsyncMock(return_value={"ok": True})

        context = EventContext(FakeEvent(), bot)

        await context.answer_and_hide_keyboard(text="✅ Done!")

        call_kwargs = bot.edit_message.call_args.kwargs
        assert call_kwargs["text"] == "✅ Done!"
        assert call_kwargs["keyboard"] is None

    @pytest.mark.asyncio
    async def test_answer_and_hide_keyboard_with_new_keyboard(self):
        """Test answer_and_hide_keyboard replacing keyboard"""
        sender = User(user_id=123, first_name="Test", is_bot=False)
        recipient = Recipient(chat_id=456, chat_type="dialog", user_id=789)
        body = MessageBody(mid="mid.123", text="Choose")
        msg = Message(recipient=recipient, sender=sender, body=body)

        class FakeEvent:
            def __init__(self):
                self.message = msg

        bot = MagicMock()
        bot.edit_message = AsyncMock(return_value={"ok": True})

        context = EventContext(FakeEvent(), bot)

        new_kb = {"type": "inline_keyboard", "buttons": []}
        await context.answer_and_hide_keyboard(text="Next step", keyboard=new_kb)

        call_kwargs = bot.edit_message.call_args.kwargs
        assert call_kwargs["text"] == "Next step"
        assert call_kwargs["keyboard"] == new_kb


class TestEditMessageSignature:
    """Test edit_message(message_id, ...) — chat_id optional"""

    @pytest.mark.asyncio
    async def test_edit_message_without_chat_id(self):
        """Test edit_message works without chat_id"""
        from aioscam.client.response import Response

        client = AsyncMock()
        client.request = AsyncMock(return_value=Response(ok=True, result={"ok": True}))

        bot = Bot(token="test")
        bot._client = client

        await bot.edit_message(message_id="mid.123", text="Updated")

        call_args = client.request.call_args
        params = call_args.kwargs.get("params", {})
        body = call_args.kwargs.get("body", {})
        assert params.get("message_id") == "mid.123"
        assert body.get("text") == "Updated"
        assert "chat_id" not in params

    @pytest.mark.asyncio
    async def test_edit_message_with_chat_id(self):
        """Test edit_message with chat_id"""
        from aioscam.client.response import Response

        client = AsyncMock()
        client.request = AsyncMock(return_value=Response(ok=True, result={"ok": True}))

        bot = Bot(token="test")
        bot._client = client

        await bot.edit_message(message_id="mid.123", text="Updated", chat_id=456)

        call_args = client.request.call_args
        params = call_args.kwargs.get("params", {})
        body = call_args.kwargs.get("body", {})
        assert params.get("message_id") == "mid.123"
        assert params.get("chat_id") == 456
        assert body.get("text") == "Updated"


class TestDeletePinMessage:
    """Test delete_pin_message(chat_id)"""

    @pytest.mark.asyncio
    async def test_delete_pin_message_takes_chat_id(self):
        """Test delete_pin_message accepts chat_id"""
        from aioscam.client.response import Response

        client = AsyncMock()
        client.request = AsyncMock(return_value=Response(ok=True, result={"ok": True}))

        bot = Bot(token="test")
        bot._client = client

        result = await bot.delete_pin_message(chat_id=789)

        assert result is True
        call_args = client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["chat_id"] == 789


class TestStateGuardConfig:
    """Test StateGuard configuration in Dispatcher"""

    def test_default_state_guard(self):
        """Test default StateGuard settings"""
        dp = Dispatcher()

        assert set(dp._guard_allowed_commands) == {'/cancel', '/start'}
        assert set(dp._guard_allowed_callbacks) == {'action:cancel'}
        assert dp._guard_hint_func is None

    def test_custom_state_guard_commands(self):
        """Test custom StateGuard allowed commands"""
        dp = Dispatcher(state_guard_commands=['/cancel', '/help', '/commands'])

        assert '/help' in dp._guard_allowed_commands
        assert '/commands' in dp._guard_allowed_commands
        assert '/start' not in dp._guard_allowed_commands

    def test_custom_state_guard_callbacks(self):
        """Test custom StateGuard allowed callbacks"""
        dp = Dispatcher(state_guard_callbacks=['action:cancel', 'action:back'])

        assert 'action:back' in dp._guard_allowed_callbacks
        assert 'action:stats' not in dp._guard_allowed_callbacks


class TestCallbackGuardMatcher:
    """Test Dispatcher._callback_guard_allowed — exact strings + MagicFilter patterns"""

    def test_exact_string_match(self):
        allowed = {'action:cancel'}
        assert Dispatcher._callback_guard_allowed('action:cancel', allowed) is True
        assert Dispatcher._callback_guard_allowed('action:cancel|1', allowed) is False

    def test_magicfilter_startswith_matches_payload_with_params(self):
        allowed = [F.startswith('confirm_yes')]
        assert Dispatcher._callback_guard_allowed('confirm_yes|52507', allowed) is True
        assert Dispatcher._callback_guard_allowed('confirm_no|52507', allowed) is False

    def test_magicfilter_regexp(self):
        allowed = [F.regexp(r'^nav:(back|next)$')]
        assert Dispatcher._callback_guard_allowed('nav:back', allowed) is True
        assert Dispatcher._callback_guard_allowed('nav:sideways', allowed) is False

    def test_magicfilter_and_or_not(self):
        allowed = [F.startswith('confirm_') & ~F.contains('admin')]
        assert Dispatcher._callback_guard_allowed('confirm_yes|1', allowed) is True
        assert Dispatcher._callback_guard_allowed('confirm_admin|1', allowed) is False

    def test_mixed_string_and_magicfilter(self):
        allowed = ['action:cancel', F.startswith('confirm_')]
        assert Dispatcher._callback_guard_allowed('action:cancel', allowed) is True
        assert Dispatcher._callback_guard_allowed('confirm_yes|1', allowed) is True
        assert Dispatcher._callback_guard_allowed('menu_back', allowed) is False

    @pytest.mark.asyncio
    async def test_process_callback_allows_magicfilter_match_during_fsm(self):
        from aioscam.fsm.memory import MemoryStorage
        from aioscam.types.update import Update

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage, state_guard_callbacks=[F.startswith('confirm_')])

        @dp.callback_query()
        async def h(event):
            return "ok"

        await storage.set_state(10, "Form:step1", user_id=1)

        update = Update(
            update_type="message_callback",
            callback={"callback_id": "cb1", "data": "confirm_yes|52507", "user": {"user_id": 1}},
            chat_id=10,
            timestamp=1,
        )

        bot = _make_bot()
        bot.send_message = AsyncMock(return_value={})
        result = await dp._process_update(bot, update)

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_callback_blocks_unmatched_during_fsm(self):
        from aioscam.fsm.memory import MemoryStorage
        from aioscam.types.update import Update

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage, state_guard_callbacks=[F.startswith('confirm_')])

        @dp.callback_query()
        async def h(event):
            return "ok"

        await storage.set_state(10, "Form:step1", user_id=1)

        update = Update(
            update_type="message_callback",
            callback={"callback_id": "cb1", "data": "menu_back", "user": {"user_id": 1}},
            chat_id=10,
            timestamp=1,
        )

        bot = _make_bot()
        bot.send_message = AsyncMock(return_value={})
        await dp._process_update(bot, update)

        bot.send_message.assert_called_once()

    def test_custom_hint_func(self):
        """Test custom hint function"""
        hints = {"Form:name": "введите имя", "Form:age": "введите возраст"}
        dp = Dispatcher(state_guard_hint_func=lambda s: hints.get(s, "данные"))

        assert dp._get_state_hint("Form:name") == "введите имя"
        assert dp._get_state_hint("Form:age") == "введите возраст"
        assert dp._get_state_hint("UnknownState") == "данные"

    def test_default_hint_fallback(self):
        """Test default hint fallback"""
        dp = Dispatcher()
        assert dp._get_state_hint("SomeState") == "ожидаемые данные"


class TestCommandGuardMatcher:
    """Test Dispatcher._command_guard_allowed — exact strings + MagicFilter patterns"""

    def test_exact_string_match(self):
        allowed = ['/cancel', '/start']
        assert Dispatcher._command_guard_allowed('/cancel', allowed) is True
        assert Dispatcher._command_guard_allowed('/start', allowed) is True
        assert Dispatcher._command_guard_allowed('/pay', allowed) is False

    def test_exact_match_is_case_sensitive(self):
        allowed = ['/cancel']
        assert Dispatcher._command_guard_allowed('/cancel', allowed) is True
        assert Dispatcher._command_guard_allowed('/Cancel', allowed) is False

    def test_magicfilter_startswith(self):
        allowed = [F.startswith('/cmd_')]
        assert Dispatcher._command_guard_allowed('/cmd_15', allowed) is True
        assert Dispatcher._command_guard_allowed('/cmd_999', allowed) is True
        assert Dispatcher._command_guard_allowed('/pay_15', allowed) is False

    def test_magicfilter_regexp(self):
        allowed = [F.regexp(r'^/item_\d+$')]
        assert Dispatcher._command_guard_allowed('/item_42', allowed) is True
        assert Dispatcher._command_guard_allowed('/item_abc', allowed) is False
        assert Dispatcher._command_guard_allowed('/item_', allowed) is False

    def test_magicfilter_and_not(self):
        allowed = [F.startswith('/nav_') & ~F.contains('admin')]
        assert Dispatcher._command_guard_allowed('/nav_back', allowed) is True
        assert Dispatcher._command_guard_allowed('/nav_admin', allowed) is False

    def test_mixed_string_and_magicfilter(self):
        allowed = ['/cancel', F.startswith('/cmd_')]
        assert Dispatcher._command_guard_allowed('/cancel', allowed) is True
        assert Dispatcher._command_guard_allowed('/cmd_15', allowed) is True
        assert Dispatcher._command_guard_allowed('/pay', allowed) is False

    @pytest.mark.asyncio
    async def test_process_message_allows_magicfilter_command_during_fsm(self):
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage, state_guard_commands=['/cancel', F.startswith('/cmd_')])

        @dp.message_created()
        async def h(event):
            return "ok"

        await storage.set_state(10, "Form:step1", user_id=1)

        update = Update(
            update_type="message_created",
            message={
                "sender": {"user_id": 1, "first_name": "Test", "is_bot": False},
                "recipient": {"chat_id": 10, "chat_type": "dialog", "user_id": 1},
                "body": {"mid": "mid.1", "text": "/cmd_15"},
                "timestamp": 1,
            },
            timestamp=1,
        )

        bot = _make_bot()
        bot.send_message = AsyncMock(return_value={})
        await dp._process_update(bot, update)

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_blocks_unmatched_command_during_fsm(self):
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage, state_guard_commands=['/cancel', F.startswith('/cmd_')])

        @dp.message_created()
        async def h(event):
            return "ok"

        await storage.set_state(10, "Form:step1", user_id=1)

        update = Update(
            update_type="message_created",
            message={
                "sender": {"user_id": 1, "first_name": "Test", "is_bot": False},
                "recipient": {"chat_id": 10, "chat_type": "dialog", "user_id": 1},
                "body": {"mid": "mid.2", "text": "/pay"},
                "timestamp": 1,
            },
            timestamp=1,
        )

        bot = _make_bot()
        bot.send_message = AsyncMock(return_value={})
        await dp._process_update(bot, update)

        bot.send_message.assert_called_once()


class TestClipboardButtonPayload:
    """Test ClipboardButton copy_text payload"""

    def test_clipboard_button_payload(self):
        """Test ClipboardButton stores copy_text in payload"""
        btn = ClipboardButton(text="Copy", payload="text to copy")

        assert btn.text == "Copy"
        assert btn.payload == "text to copy"

    def test_keyboard_builder_clipboard(self):
        """Test KeyboardBuilder passes copy_text to payload"""
        builder = KeyboardBuilder(inline=True)
        builder.clipboard("Copy email", "user@example.com")
        kb = builder.build()

        assert len(kb.buttons) == 1
        assert len(kb.buttons[0]) == 1
        btn = kb.buttons[0][0]
        assert btn.text == "Copy email"
        assert btn.payload == "user@example.com"

    def test_clipboard_button_to_dict(self):
        """Test ClipboardButton serializes with payload"""
        from aioscam.types.keyboard import InlineKeyboard

        kb = InlineKeyboard(buttons=[[ClipboardButton(text="Copy", payload="secret")]])
        data = kb.to_dict()

        assert data["type"] == "inline_keyboard"
        assert data["payload"]["buttons"][0][0]["type"] == "clipboard"
        assert data["payload"]["buttons"][0][0]["payload"] == "secret"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
