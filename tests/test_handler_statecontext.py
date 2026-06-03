"""
Tests for:
- MessageHandler / CallbackHandler filter data injection into handler kwargs
- Bot._send_with_media() retry logic (attachment.not.ready)
- StateContext with chat_id=0 (bug fix: was falsy)
- BaseHandler.check() with MagicFilter, FSM State, BaseFilter
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam import Bot
from aioscam.handler.message import MessageHandler
from aioscam.handler.callback import CallbackHandler
from aioscam.handler.base import BaseHandler
from aioscam.filters.builtin import Command, Text, StateFilter, AllFilter
from aioscam.filters.base import FilterResult
from aioscam.dispatcher.state import StateContext
from aioscam.fsm.memory import MemoryStorage
from aioscam.fsm.state import State, StatesGroup
from aioscam.dispatcher.event import EventContext
from aioscam.types.user import User
from aioscam.types.message import Message, MessageBody, Recipient
from aioscam.exceptions import ApiError


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_context(text="hello"):
    sender = User(user_id=1, first_name="T", is_bot=False)
    recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
    body = MessageBody(text=text)
    msg = Message(recipient=recipient, sender=sender, body=body)

    class FakeEvent:
        def __init__(self):
            self.message = msg
            self.data = {}

        @property
        def text(self):
            return text

    return EventContext(FakeEvent(), MagicMock())


# ─── MessageHandler: filter data injection ───────────────────────────────────

class TestMessageHandlerInjection:

    @pytest.mark.asyncio
    async def test_event_injected_by_name(self):
        captured = {}

        async def h(event):
            captured["event"] = event

        handler = MessageHandler(h, [])
        ctx = _make_context()
        await handler.handle(ctx, {})
        assert captured["event"] is ctx

    @pytest.mark.asyncio
    async def test_filter_data_injected_as_kwargs(self):
        captured = {}

        async def h(event, command, command_args):
            captured["command"] = command
            captured["command_args"] = command_args

        handler = MessageHandler(h, [Command("start")])
        ctx = _make_context("/start hello")
        check = await handler.check(ctx)
        assert check is not None
        await handler.handle(ctx, check)
        assert captured["command"] == "start"
        assert captured["command_args"] == "hello"

    @pytest.mark.asyncio
    async def test_state_injected_as_kwarg(self):
        captured = {}

        async def h(event, state):
            captured["state"] = state

        storage = MemoryStorage()
        state_ctx = StateContext(storage, chat_id=1, user_id=1)
        handler = MessageHandler(h, [])
        ctx = _make_context("hello")
        await handler.handle(ctx, {"state": state_ctx})
        assert captured["state"] is state_ctx

    @pytest.mark.asyncio
    async def test_handler_without_event_param(self):
        """Handler that doesn't accept event — should still work."""
        results = []

        async def h():
            results.append(True)

        handler = MessageHandler(h, [])
        await handler.handle(_make_context(), {})
        assert results

    @pytest.mark.asyncio
    async def test_sync_handler_supported(self):
        """Sync (non-async) handlers should be called correctly."""
        results = []

        def h(event):
            results.append("sync")

        handler = MessageHandler(h, [])
        await handler.handle(_make_context(), {})
        assert "sync" in results

    @pytest.mark.asyncio
    async def test_no_callback_returns_none(self):
        handler = MessageHandler(None, [])
        result = await handler.handle(_make_context(), {})
        assert result is None

    @pytest.mark.asyncio
    async def test_data_kwarg_injected(self):
        captured = {}

        async def h(event, data):
            captured["data"] = data

        handler = MessageHandler(h, [])
        ctx = _make_context()
        await handler.handle(ctx, {"key": "val"})
        assert captured["data"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_text_filter_data_injected(self):
        captured = {}

        async def h(event, text):
            captured["text"] = text

        handler = MessageHandler(h, [Text()])
        ctx = _make_context("hello world")
        check = await handler.check(ctx)
        assert check is not None
        await handler.handle(ctx, check)
        assert captured["text"] == "hello world"


# ─── BaseHandler.check() filter evaluation ───────────────────────────────────

class TestBaseHandlerCheck:

    @pytest.mark.asyncio
    async def test_no_filters_passes(self):
        async def h(event): pass
        handler = MessageHandler(h, [])
        ctx = _make_context()
        result = await handler.check(ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_single_filter_passes(self):
        async def h(event): pass
        handler = MessageHandler(h, [Command("start")])
        ctx = _make_context("/start")
        result = await handler.check(ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_single_filter_fails(self):
        async def h(event): pass
        handler = MessageHandler(h, [Command("start")])
        ctx = _make_context("hello")
        result = await handler.check(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_filters_all_must_pass(self):
        async def h(event): pass
        from aioscam.filters.builtin import Text
        handler = MessageHandler(h, [Text(startswith="hello"), Text(endswith="world")])
        ctx = _make_context("hello world")
        result = await handler.check(ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_filters_one_fails(self):
        async def h(event): pass
        from aioscam.filters.builtin import Text
        handler = MessageHandler(h, [Text(startswith="hello"), Text(endswith="there")])
        ctx = _make_context("hello world")
        result = await handler.check(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_filter_data_merged(self):
        async def h(event): pass
        handler = MessageHandler(h, [Command("start")])
        ctx = _make_context("/start ref_42")
        result = await handler.check(ctx)
        assert result is not None
        assert result.get("command") == "start"
        assert result.get("command_args") == "ref_42"

    @pytest.mark.asyncio
    async def test_fsm_state_used_directly_as_filter(self):
        """State object (not StateFilter) used directly as filter."""
        class MyStates(StatesGroup):
            step1 = State()

        storage = MemoryStorage()
        await storage.set_state(10, "MyStates:step1", user_id=1)

        ctx = _make_context("data")
        state_ctx = StateContext(storage, chat_id=10, user_id=1)
        ctx.data["state"] = state_ctx

        async def h(event): pass
        handler = MessageHandler(h, [MyStates.step1])
        result = await handler.check(ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_all_filter_always_passes(self):
        async def h(event): pass
        handler = MessageHandler(h, [AllFilter()])
        ctx = _make_context()
        result = await handler.check(ctx)
        assert result is not None


# ─── Bot._send_with_media retry logic ────────────────────────────────────────

class TestSendWithMediaRetry:

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}
        bot.send_message = AsyncMock(return_value={"id": 1})

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await bot._send_with_media(att, chat_id=1, text="hi")

        assert result == {"id": 1}
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_not_ready_error(self):
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}

        call_count = 0

        async def flaky_send(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ApiError("attachment.not.ready")
            return {"id": 1}

        bot.send_message = flaky_send

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await bot._send_with_media(att, chat_id=1)

        assert result == {"id": 1}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_ready_error_reraises_immediately(self):
        """Errors not related to attachment.not.ready should propagate immediately."""
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}

        call_count = 0

        async def failing(**kwargs):
            nonlocal call_count
            call_count += 1
            raise ApiError("Some other error")

        bot.send_message = failing

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ApiError):
                await bot._send_with_media(att, chat_id=1)

        assert call_count == 1  # No retry for unrelated errors

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_raises_last_exception(self):
        """After 5 attempts, raises the last exception."""
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}

        async def always_not_ready(**kwargs):
            raise ApiError("attachment.not.ready")

        bot.send_message = always_not_ready

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ApiError, match="not.ready"):
                await bot._send_with_media(att, chat_id=1)

    @pytest.mark.asyncio
    async def test_passes_text_and_kwargs(self):
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}
        captured = {}

        async def mock_send(**kwargs):
            captured.update(kwargs)
            return {"id": 1}

        bot.send_message = mock_send

        with patch("asyncio.sleep", new=AsyncMock()):
            await bot._send_with_media(att, chat_id=5, user_id=42, text="caption", notify=True)

        assert captured["chat_id"] == 5
        assert captured["user_id"] == 42
        assert captured["text"] == "caption"
        assert captured["notify"] is True


# ─── StateContext chat_id=0 bug fix ──────────────────────────────────────────

class TestStateContextChatIdZero:
    """Bug fix: `if not self._chat_id:` was treating chat_id=0 as None."""

    @pytest.mark.asyncio
    async def test_get_state_with_chat_id_zero(self):
        storage = MemoryStorage()
        await storage.set_state(0, "some_state", user_id=1)
        ctx = StateContext(storage, chat_id=0, user_id=1)
        result = await ctx.get_state()
        assert result == "some_state"

    @pytest.mark.asyncio
    async def test_set_state_with_chat_id_zero(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=0, user_id=1)
        await ctx.set_state("zero_chat_state")
        result = await storage.get_state(0, user_id=1)
        assert result == "zero_chat_state"

    @pytest.mark.asyncio
    async def test_get_data_with_chat_id_zero(self):
        storage = MemoryStorage()
        await storage.set_data(0, {"key": "val"}, user_id=1)
        ctx = StateContext(storage, chat_id=0, user_id=1)
        data = await ctx.get_data()
        assert data["key"] == "val"

    @pytest.mark.asyncio
    async def test_set_data_with_chat_id_zero(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=0, user_id=1)
        await ctx.set_data({"x": 42})
        data = await storage.get_data(0, user_id=1)
        assert data["x"] == 42

    @pytest.mark.asyncio
    async def test_update_data_with_chat_id_zero(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=0, user_id=1)
        result = await ctx.update_data(name="Alice")
        assert result.get("name") == "Alice"

    @pytest.mark.asyncio
    async def test_none_chat_id_still_returns_none(self):
        """None chat_id must still return None (not crash)."""
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=None, user_id=1)
        result = await ctx.get_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_none_chat_id_set_state_no_crash(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=None, user_id=1)
        await ctx.set_state("something")  # must not raise

    @pytest.mark.asyncio
    async def test_none_chat_id_get_data_returns_empty(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=None, user_id=1)
        result = await ctx.get_data()
        assert result == {}

    @pytest.mark.asyncio
    async def test_none_chat_id_update_data_returns_empty(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=None, user_id=1)
        result = await ctx.update_data(x=1)
        assert result == {}

    @pytest.mark.asyncio
    async def test_zero_differs_from_none(self):
        """chat_id=0 and chat_id=None must be completely independent."""
        storage = MemoryStorage()
        ctx_zero = StateContext(storage, chat_id=0, user_id=1)
        ctx_none = StateContext(storage, chat_id=None, user_id=1)

        await ctx_zero.set_state("zero_state")
        assert await ctx_zero.get_state() == "zero_state"
        assert await ctx_none.get_state() is None
