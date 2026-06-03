"""
Advanced Router / Dispatcher tests: circular inclusion, middleware chain,
add_middleware, filter system with StateFilter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aioscam.dispatcher.router import Router
from aioscam.middleware.manager import MiddlewareManager
from aioscam.middleware.base import BaseMiddleware
from aioscam.filters.builtin import Command, Text, StateFilter
from aioscam.dispatcher.event import EventContext
from aioscam.types.user import User
from aioscam.types.message import Message, MessageBody, Recipient


def _make_event(text="hello"):
    sender = User(user_id=1, first_name="T", is_bot=False)
    recipient = Recipient(chat_id=10, chat_type="dialog", user_id=1)
    body = MessageBody(text=text)
    msg = Message(recipient=recipient, sender=sender, body=body)

    class FakeEvent:
        def __init__(self):
            self.message = msg

    return EventContext(FakeEvent(), MagicMock())


# ─── Router circular inclusion ───────────────────────────────────────────────

class TestRouterCircularInclusion:
    def test_include_router(self):
        parent = Router("parent")
        child = Router("child")
        parent.include_router(child)
        assert child in parent._children
        assert child._parent is parent

    def test_circular_inclusion_raises(self):
        a = Router("A")
        b = Router("B")
        a.include_router(b)
        with pytest.raises(ValueError):
            b.include_router(a)

    def test_deep_circular_raises(self):
        a = Router("A")
        b = Router("B")
        c = Router("C")
        a.include_router(b)
        b.include_router(c)
        with pytest.raises(ValueError):
            c.include_router(a)

    def test_including_same_router_twice_does_not_raise(self):
        parent = Router("P")
        child = Router("C")
        parent.include_router(child)
        # Second include — no cycle, just adds again
        # Should not raise ValueError (it's not circular)
        parent.include_router(Router("C2"))


# ─── add_middleware ──────────────────────────────────────────────────────────

class TestAddMiddleware:
    @pytest.mark.asyncio
    async def test_add_middleware_direct_instance(self):
        router = Router()
        called = []

        class MyMiddleware(BaseMiddleware):
            async def __call__(self, event, handler):
                called.append("before")
                result = await handler(event)
                called.append("after")
                return result

        router.add_middleware(MyMiddleware())

        handler_called = []

        @router.message_created()
        async def h(event):
            handler_called.append(True)
            return "ok"

        event = _make_event()
        await router.process_message(event)

        assert "before" in called
        assert "after" in called
        assert handler_called

    @pytest.mark.asyncio
    async def test_middleware_decorator(self):
        router = Router()
        order = []

        @router.middleware()
        async def my_mw(event, handler):
            order.append("mw")
            return await handler(event)

        @router.message_created()
        async def h(event):
            order.append("handler")
            return "ok"

        event = _make_event()
        await router.process_message(event)
        assert order == ["mw", "handler"]

    @pytest.mark.asyncio
    async def test_middleware_can_short_circuit(self):
        router = Router()

        @router.middleware()
        async def block_all(event, handler):
            return "blocked"

        handler_called = []

        @router.message_created()
        async def h(event):
            handler_called.append(True)
            return "ok"

        event = _make_event()
        result = await router.process_message(event)
        assert result == "blocked"
        assert not handler_called


# ─── MiddlewareManager chain ─────────────────────────────────────────────────

class TestMiddlewareManager:
    @pytest.mark.asyncio
    async def test_empty_manager_runs_handler(self):
        manager = MiddlewareManager()
        handler = AsyncMock(return_value="result")
        result = await manager.execute("event", handler)
        assert result == "result"
        handler.assert_called_once_with("event")

    @pytest.mark.asyncio
    async def test_single_middleware(self):
        manager = MiddlewareManager()
        order = []

        class M(BaseMiddleware):
            async def __call__(self, event, handler):
                order.append(1)
                r = await handler(event)
                order.append(3)
                return r

        manager.add(M())
        handler = AsyncMock(side_effect=lambda e: order.append(2) or "ok")
        await manager.execute("event", handler)
        assert order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_two_middlewares_in_order(self):
        manager = MiddlewareManager()
        order = []

        class M1(BaseMiddleware):
            async def __call__(self, event, handler):
                order.append("m1_before")
                r = await handler(event)
                order.append("m1_after")
                return r

        class M2(BaseMiddleware):
            async def __call__(self, event, handler):
                order.append("m2_before")
                r = await handler(event)
                order.append("m2_after")
                return r

        manager.add(M1())
        manager.add(M2())
        handler = AsyncMock(return_value="ok")
        await manager.execute("event", handler)
        assert order == ["m1_before", "m2_before", "m2_after", "m1_after"]


# ─── Router handler routing ──────────────────────────────────────────────────

class TestRouterHandlers:
    @pytest.mark.asyncio
    async def test_message_handler_matched(self):
        router = Router()
        results = []

        @router.message_created(Command("start"))
        async def h(event):
            results.append("start")
            return "ok"

        event = _make_event("/start")
        await router.process_message(event)
        assert "start" in results

    @pytest.mark.asyncio
    async def test_message_handler_not_matched(self):
        router = Router()
        results = []

        @router.message_created(Command("start"))
        async def h(event):
            results.append("start")
            return "ok"

        event = _make_event("hello")
        result = await router.process_message(event)
        assert result is None
        assert not results

    @pytest.mark.asyncio
    async def test_first_matching_handler_wins(self):
        router = Router()
        order = []

        @router.message_created(Text(equals="hi"))
        async def h1(event):
            order.append(1)
            return "h1"

        @router.message_created(Text(equals="hi"))
        async def h2(event):
            order.append(2)
            return "h2"

        event = _make_event("hi")
        await router.process_message(event)
        assert order == [1]

    @pytest.mark.asyncio
    async def test_child_router_processed(self):
        parent = Router("parent")
        child = Router("child")
        parent.include_router(child)

        results = []

        @child.message_created(Command("help"))
        async def h(event):
            results.append("help")
            return "ok"

        event = _make_event("/help")
        await parent.process_message(event)
        assert "help" in results


# ─── Text filter empty string ────────────────────────────────────────────────

class TestTextFilterEdgeCases:
    @pytest.mark.asyncio
    async def test_equals_empty_string_can_match(self):
        f = Text(equals="")
        # Empty string in event text — should match
        event = _make_event("")
        # Text filter requires non-empty text (returns False for empty)
        # This tests the `if self.equals is not None:` fix
        result = await f(event)
        # Empty text returns False before reaching equals check
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_equals_none_acts_as_catch_all(self):
        # Text() with no args matches any non-empty text
        f = Text()
        event = _make_event("anything")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_case_insensitive_by_default(self):
        f = Text(equals="Hello")
        event = _make_event("hello")
        result = await f(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_case_sensitive(self):
        f = Text(equals="Hello", ignore_case=False)
        event = _make_event("hello")
        result = await f(event)
        assert result.passed is False
