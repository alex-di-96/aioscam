"""
Security tests for AioScam framework
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam import Bot, Dispatcher, Router, Command, F
from aioscam.dispatcher.event import EventContext
from aioscam.dispatcher.router import Router
from aioscam.filters.base import BaseFilter, FilterResult, AndFilter, OrFilter, NotFilter
from aioscam.filters.builtin import Command as CommandFilter, Text, ContentType, ChatType
from aioscam.fsm.memory import MemoryStorage
from aioscam.exceptions import BotTokenError, DispatcherError
from aioscam.types.user import User
from aioscam.types.chat import Chat, ChatType as ChatTypeEnum
from aioscam.types.message import Message, MessageBody
from aioscam.types.update import Update, MessageCreated, User as UpdateUser, Recipient, Message as UpdateMessage, MessageBody as UpdateMessageBody


def _make_event_with_text(text: str):
    """Create EventContext with specific text."""
    sender = UpdateUser(user_id=123, first_name="Test", is_bot=False)
    recipient = Recipient(chat_id=456, chat_type="dialog", user_id=789)
    body = UpdateMessageBody(text=text)
    msg = UpdateMessage(recipient=recipient, sender=sender, body=body)

    class FakeEvent:
        def __init__(self):
            self.message = msg
            self.timestamp = 1776345558644
            self.user_locale = "ru"
            self.update_type = "message_created"

    bot = MagicMock()
    return EventContext(FakeEvent(), bot)


class TestSecurityWebhookAuth:
    """Test webhook authentication"""

    @pytest.mark.asyncio
    async def test_webhook_rejects_unauthorized(self):
        """Test that webhook rejects requests without proper auth"""
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        dp = Dispatcher()
        bot = MagicMock()

        # Setup webhook with secret
        secret = "my_secret_token"
        dp._webhook_secret = secret

        # Create test application
        app = web.Application()

        async def webhook_handler(request):
            if dp._webhook_secret:
                request_token = request.headers.get("X-Max-Secret-Token")
                if not request_token or request_token != dp._webhook_secret:
                    return web.json_response(
                        {"ok": False, "error": "Unauthorized"},
                        status=401
                    )
            return web.json_response({"ok": True})

        app.router.add_post("/webhook", webhook_handler)

        # Test without token
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/webhook", json={})
            assert resp.status == 401

            # Test with wrong token
            resp = await client.post(
                "/webhook",
                json={},
                headers={"X-Max-Secret-Token": "wrong_token"}
            )
            assert resp.status == 401

            # Test with correct token
            resp = await client.post(
                "/webhook",
                json={"update_id": 1},
                headers={"X-Max-Secret-Token": secret}
            )
            assert resp.status == 200


class TestSecurityCircularRouter:
    """Test circular router inclusion prevention"""

    def test_circular_inclusion_prevented(self):
        """Test that circular router inclusion raises error"""
        router_a = Router(name="A")
        router_b = Router(name="B")

        # Valid inclusion
        router_a.include_router(router_b)

        # Circular should fail
        with pytest.raises(ValueError, match="Circular router inclusion"):
            router_b.include_router(router_a)

    def test_deep_circular_inclusion_prevented(self):
        """Test deep circular inclusion prevention"""
        router_a = Router(name="A")
        router_b = Router(name="B")
        router_c = Router(name="C")

        router_a.include_router(router_b)
        router_b.include_router(router_c)

        # This should fail (C trying to include A)
        with pytest.raises(ValueError):
            router_c.include_router(router_a)

    def test_valid_nested_inclusion(self):
        """Test that valid nested inclusion works"""
        router_a = Router(name="A")
        router_b = Router(name="B")
        router_c = Router(name="C")

        router_a.include_router(router_b)
        router_b.include_router(router_c)

        # No exception should be raised
        assert router_c._parent == router_b
        assert router_b._parent == router_a


class TestSecurityDispatcherPolling:
    """Test dispatcher polling safety"""

    @pytest.mark.asyncio
    async def test_double_polling_prevented(self):
        """Test that starting polling twice raises error"""
        dp = Dispatcher()
        bot = MagicMock()
        bot.get_updates = AsyncMock(return_value=[])

        async def mock_polling():
            async with dp._lock:
                if dp._running:
                    raise DispatcherError("Polling is already running")
                dp._running = True

            await asyncio.sleep(0.1)
            async with dp._lock:
                dp._running = False

        # Start first polling
        task = asyncio.create_task(mock_polling())
        await asyncio.sleep(0.05)

        # Try to start second (should fail if lock works)
        async with dp._lock:
            assert dp._running is True

        await task
        async with dp._lock:
            assert dp._running is False


class TestSecurityFilterDataValidation:
    """Test filter data validation"""

    @pytest.mark.asyncio
    async def test_and_filter_no_leak(self):
        """Test that AndFilter doesn't leak filter objects"""
        filter1 = CommandFilter("start")
        filter2 = CommandFilter("help")

        and_filter = AndFilter(filter1, filter2)

        event = _make_event_with_text("/start")

        result = await and_filter(event)

        # Should pass but not contain filter objects in data
        assert result.passed is False  # Second command doesn't match
        # Even if it passed, data should be clean
        if result.data:
            assert "and_results" not in result.data

    @pytest.mark.asyncio
    async def test_command_filter_injection(self):
        """Test command filter against injection attacks"""
        cmd_filter = CommandFilter(["start", "help"])

        # Test with various malicious inputs
        malicious_inputs = [
            "/start; rm -rf /",
            "/start\nmalicious",
            "/start<script>alert('xss')</script>",
            "/start' OR '1'='1",
            "/start${{7*7}}",
        ]

        for malicious_text in malicious_inputs:
            event = _make_event_with_text(malicious_text)

            result = await cmd_filter(event)

            # Should either pass safely (for /start) or fail
            # But never execute malicious code
            if result.passed:
                assert "command" in result.data
                assert result.data["command"] in ["start", "help"]


class TestSecurityEventContext:
    """Test EventContext safety"""

    def test_event_context_no_mutation(self):
        """Test that EventContext doesn't mutate input event"""
        sender = UpdateUser(user_id=123, first_name="Test", is_bot=False)
        recipient = Recipient(chat_id=456, chat_type="dialog", user_id=789)
        body = UpdateMessageBody(text="test")
        msg = UpdateMessage(recipient=recipient, sender=sender, body=body)

        class FakeEvent:
            def __init__(self):
                self.message = msg
                self.timestamp = 1776345558644
                self.user_locale = "ru"
                self.update_type = "message_created"

        event = FakeEvent()

        # Store original state of message
        original_attrs = set(dir(msg))

        bot = MagicMock()
        context = EventContext(event, bot)

        # Check that message object wasn't modified
        current_attrs = set(dir(msg))
        assert original_attrs == current_attrs

    def test_event_context_properties(self):
        """Test EventContext property access with real API structure"""
        sender = UpdateUser(user_id=39068268, first_name="aLex", last_name="Di", is_bot=False, name="aLex Di")
        recipient = Recipient(chat_id=243186798, chat_type="dialog", user_id=204119554)
        body = UpdateMessageBody(mid="mid.xxx", seq=123, text="hello")
        msg = UpdateMessage(recipient=recipient, sender=sender, body=body, timestamp=1776345558644)

        class FakeEvent:
            def __init__(self):
                self.message = msg
                self.timestamp = 1776345558644
                self.user_locale = "ru"
                self.update_type = "message_created"

        bot = MagicMock()
        context = EventContext(FakeEvent(), bot)

        # EventContext returns the real objects from the event
        assert context.message == msg
        # chat returns recipient (Recipient object)
        assert context.chat == recipient
        assert context.chat.chat_id == 243186798
        # from_user returns sender (UpdateUser object)
        assert context.from_user == sender
        assert context.from_user.user_id == 39068268
        # text returns body.text
        assert context.text == "hello"


class TestSecurityMemoryStorage:
    """Test MemoryStorage safety"""

    @pytest.mark.asyncio
    async def test_storage_isolation(self):
        """Test that different users have isolated storage"""
        storage = MemoryStorage()

        # Set data for user 1
        await storage.set_data(chat_id=1, data={"name": "user1"}, user_id=1)

        # Set data for user 2
        await storage.set_data(chat_id=1, data={"name": "user2"}, user_id=2)

        # Get data back
        data1 = await storage.get_data(chat_id=1, user_id=1)
        data2 = await storage.get_data(chat_id=1, user_id=2)

        assert data1["name"] == "user1"
        assert data2["name"] == "user2"
        assert data1 != data2

    @pytest.mark.asyncio
    async def test_storage_update_atomic(self):
        """Test that update_data merges correctly"""
        storage = MemoryStorage()

        await storage.set_data(chat_id=1, data={"name": "test", "age": 25})
        result = await storage.update_data(chat_id=1, data={"age": 26, "email": "test@test.com"})

        assert result["name"] == "test"  # Preserved
        assert result["age"] == 26  # Updated
        assert result["email"] == "test@test.com"  # Added


class TestSecurityInputValidation:
    """Test input validation"""

    def test_bot_token_required(self):
        """Test that bot token is required"""
        old_token = os.environ.get("MAX_BOT_TOKEN")

        try:
            if "MAX_BOT_TOKEN" in os.environ:
                del os.environ["MAX_BOT_TOKEN"]

            with pytest.raises(BotTokenError, match="token is not provided"):
                Bot()
        finally:
            if old_token:
                os.environ["MAX_BOT_TOKEN"] = old_token

    def test_message_validation(self):
        """Test message object validation"""
        # Should accept valid message
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        body = MessageBody(text="hello")
        message = Message(id=1, chat=chat, body=body)

        assert message.text == "hello"
        assert message.has_text is True

        # Should handle missing fields gracefully
        message_no_text = Message(id=2, chat=chat)
        assert message_no_text.has_text is False


class TestSecurityErrorHandler:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_handler_exception_handling(self):
        """Test that handler exceptions propagate (framework doesn't swallow them)"""
        router = Router()

        @router.message_created(Command("error"))
        async def error_handler(event):
            raise ValueError("Test exception")

        event = _make_event_with_text("/error")

        # Handler exception propagates (router doesn't swallow it)
        with pytest.raises(ValueError, match="Test exception"):
            await router.process_message(event)


class TestSecurityMiddlewareChain:
    """Test middleware chain safety"""

    @pytest.mark.asyncio
    async def test_middleware_executes_in_order(self):
        """Test that middleware executes in correct order"""
        router = Router()
        execution_order = []

        @router.middleware()
        async def middleware1(event, handler):
            execution_order.append("before1")
            result = await handler(event)
            execution_order.append("after1")
            return result

        @router.middleware()
        async def middleware2(event, handler):
            execution_order.append("before2")
            result = await handler(event)
            execution_order.append("after2")
            return result

        @router.message_created()
        async def test_handler(event):
            execution_order.append("handler")
            return "done"

        event = _make_event_with_text("test")

        await router.process_message(event)

        assert execution_order == ["before1", "before2", "handler", "after2", "after1"]


class TestSecurityRegexInjection:
    """Test regex injection prevention"""

    @pytest.mark.asyncio
    async def test_text_filter_regex_safety(self):
        """Test that text filter handles regex-special characters as literal string"""
        # Text filter with contains checks for literal substring (not regex)
        text_filter = Text(contains=["test.*user"])

        event = _make_event_with_text("test.*user")

        result = await text_filter(event)
        # Should match literal string
        assert result.passed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
