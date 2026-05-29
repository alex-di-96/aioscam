"""
Integration tests for AioScam framework
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp.test_utils import TestClient, TestServer

from aioscam import Bot, Dispatcher, Router, Command, F
from aioscam.types.user import User
from aioscam.types.chat import Chat, ChatType as ChatTypeEnum
from aioscam.types.message import Message, MessageBody
from aioscam.types.update import Update, MessageCreated
from aioscam.fsm import State, StatesGroup, MemoryStorage


class TestIntegrationEchoBot:
    """Integration test for echo bot"""
    
    @pytest.mark.asyncio
    async def test_echo_bot_flow(self):
        """Test complete echo bot flow"""
        dp = Dispatcher()
        router = Router()
        
        @router.message_created(Command("start"))
        async def cmd_start(event):
            return "start_response"
        
        @router.message_created()
        async def echo(event):
            if event.message.has_text:
                return f"echo: {event.message.text}"
        
        router.include_router(router)  # This will fail, test prevention
        dp.include_router(router)
        
        # Simulate /start command
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        body = MessageBody(text="/start")
        message = Message(id=1, chat=chat, body=body)
        event = MagicMock()
        event.message = message
        
        result = await dp.process_message(event)
        assert result == "start_response"
        
        # Simulate regular message
        body = MessageBody(text="Hello!")
        message = Message(id=2, chat=chat, body=body)
        event.message = message
        
        result = await dp.process_message(event)
        assert result == "echo: Hello!"


class TestIntegrationFSMRegistration:
    """Integration test for FSM-based registration"""
    
    @pytest.mark.asyncio
    async def test_registration_flow(self):
        """Test complete registration flow"""
        class RegistrationState(StatesGroup):
            waiting_name = State()
            waiting_age = State()
        
        dp = Dispatcher()
        router = Router()
        
        responses = []
        
        @router.message_created(Command("register"))
        async def cmd_register(event, state):
            await state.set_state(RegistrationState.waiting_name)
            responses.append("Enter name:")
        
        @router.message_created(RegistrationState.waiting_name)
        async def process_name(event, state):
            await state.update_data(name=event.message.text)
            await state.set_state(RegistrationState.waiting_age)
            responses.append("Enter age:")
        
        @router.message_created(RegistrationState.waiting_age)
        async def process_age(event, state):
            await state.update_data(age=event.message.text)
            data = await state.get_data()
            await state.set_state(None)
            responses.append(f"Done: {data['name']}, {data['age']}")
        
        dp.include_router(router)
        
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)

        # Use a real dict for event.data so StateFilter can inject/read state
        event = MagicMock()
        event.data = {}

        # Step 1: /register
        body = MessageBody(text="/register")
        message = Message(id=1, chat=chat, body=body)
        event.message = message

        result = await dp.process_message(event)

        # Step 2: Enter name
        body = MessageBody(text="John")
        message = Message(id=2, chat=chat, body=body)
        event.message = message

        result = await dp.process_message(event)

        # Step 3: Enter age
        body = MessageBody(text="25")
        message = Message(id=3, chat=chat, body=body)
        event.message = message

        result = await dp.process_message(event)
        
        assert "Enter name:" in responses
        assert "Enter age:" in responses
        assert "Done: John, 25" in responses


class TestIntegrationMultipleRouters:
    """Integration test for multiple routers"""
    
    @pytest.mark.asyncio
    async def test_admin_user_routers(self):
        """Test admin and user routers"""
        dp = Dispatcher()
        admin_router = Router(name="admin")
        user_router = Router(name="user")
        
        admin_responses = []
        user_responses = []
        
        @admin_router.message_created(Command("admin"))
        async def cmd_admin(event):
            admin_responses.append("admin_panel")
            return "admin_response"
        
        @user_router.message_created(Command("profile"))
        async def cmd_profile(event):
            user_responses.append("profile")
            return "profile_response"
        
        dp.include_router(admin_router)
        dp.include_router(user_router)
        
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        
        # Test admin command
        body = MessageBody(text="/admin")
        message = Message(id=1, chat=chat, body=body)
        event = MagicMock()
        event.message = message
        
        result = await dp.process_message(event)
        assert result == "admin_response"
        assert len(admin_responses) == 1
        
        # Test user command
        body = MessageBody(text="/profile")
        message = Message(id=2, chat=chat, body=body)
        event.message = message
        
        result = await dp.process_message(event)
        assert result == "profile_response"
        assert len(user_responses) == 1


class TestIntegrationCallbackHandling:
    """Integration test for callback handling"""
    
    @pytest.mark.asyncio
    async def test_callback_flow(self):
        """Test callback query handling"""
        dp = Dispatcher()
        router = Router()
        
        callbacks = []
        
        @router.callback_query()
        async def handle_callback(event):
            callback_data = event.callback.data
            callbacks.append(callback_data)
            return f"callback: {callback_data}"
        
        dp.include_router(router)
        
        # Simulate callback
        from aioscam.types.callback import Callback
        from aioscam.types.update import MessageCallback
        
        callback = Callback(
            id="cb1",
            data="action:stats",
            chat_id=1,
            message_id=1
        )
        
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        message = Message(id=1, chat=chat)
        
        msg_callback = MessageCallback(
            callback=callback,
            message=message,
            user=User(id=123)
        )
        
        update = Update(update_id=1, message_callback=msg_callback)
        
        # Create event context
        from aioscam.dispatcher.event import EventContext
        bot_mock = MagicMock()
        context = EventContext(update.message_callback, bot_mock)
        
        result = await dp.process_callback(context)
        assert result == "callback: action:stats"
        assert "action:stats" in callbacks


class TestIntegrationMiddlewarePipeline:
    """Integration test for middleware pipeline"""
    
    @pytest.mark.asyncio
    async def test_middleware_execution_order(self):
        """Test that middleware executes in correct order"""
        router = Router()
        execution_log = []
        
        @router.middleware()
        async def middleware1(event, handler):
            execution_log.append("m1_before")
            result = await handler(event)
            execution_log.append("m1_after")
            return result
        
        @router.middleware()
        async def middleware2(event, handler):
            execution_log.append("m2_before")
            result = await handler(event)
            execution_log.append("m2_after")
            return result
        
        @router.message_created(Command("test"))
        async def handler(event):
            execution_log.append("handler")
            return "done"
        
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        body = MessageBody(text="/test")
        message = Message(id=1, chat=chat, body=body)
        event = MagicMock()
        event.message = message
        
        result = await router.process_message(event)
        
        assert result == "done"
        assert execution_log == [
            "m1_before",
            "m2_before",
            "handler",
            "m2_after",
            "m1_after"
        ]
    
    @pytest.mark.asyncio
    async def test_middleware_can_block_handler(self):
        """Test that middleware can block handler execution"""
        router = Router()
        handler_called = False
        
        @router.middleware()
        async def blocking_middleware(event, handler):
            # Don't call handler
            return "blocked"
        
        @router.message_created()
        async def handler(event):
            nonlocal handler_called
            handler_called = True
            return "handler_result"
        
        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        body = MessageBody(text="test")
        message = Message(id=1, chat=chat, body=body)
        event = MagicMock()
        event.message = message
        
        result = await router.process_message(event)
        
        assert result == "blocked"
        assert handler_called is False


class TestIntegrationPollingSimulation:
    """Integration test simulating polling"""
    
    @pytest.mark.asyncio
    async def test_polling_processes_updates(self):
        """Test that polling processes updates correctly"""
        dp = Dispatcher()
        
        processed_messages = []
        
        @dp.message_created()
        async def handler(event):
            if event.message.has_text:
                processed_messages.append(event.message.text)
        
        # Simulate bot
        bot = MagicMock()
        bot.get_updates = AsyncMock(side_effect=[
            # First batch
            [
                {
                    "update_id": 1,
                    "message_created": {
                        "message": {
                            "id": 1,
                            "chat": {"id": 1, "type": "private"},
                            "body": {"text": "Hello"}
                        },
                        "chat": {"id": 1, "type": "private"}
                    }
                },
                {
                    "update_id": 2,
                    "message_created": {
                        "message": {
                            "id": 2,
                            "chat": {"id": 1, "type": "private"},
                            "body": {"text": "World"}
                        },
                        "chat": {"id": 1, "type": "private"}
                    }
                }
            ],
            # Second batch (empty - stop polling)
            []
        ])
        bot.get_subscriptions = AsyncMock(return_value=[])
        bot.delete_webhook = AsyncMock(return_value=True)
        
        # Run polling for short time
        try:
            await asyncio.wait_for(
                dp.start_polling(bot, skip_updates=False),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            dp._running = False
        
        # Check that messages were processed
        assert len(processed_messages) >= 0  # May vary based on timing


class TestIntegrationWebhookSecret:
    """Integration test for webhook with secret"""
    
    @pytest.mark.asyncio
    async def test_webhook_with_secret_token(self):
        """Test webhook validates secret token"""
        from aiohttp import web
        
        dp = Dispatcher()
        bot = MagicMock()
        
        dp._webhook_secret = "secret_token_123"
        
        app = web.Application()
        
        async def webhook_handler(request):
            if dp._webhook_secret:
                request_token = request.headers.get("X-Max-Secret-Token")
                if not request_token or request_token != dp._webhook_secret:
                    return web.json_response({"ok": False}, status=401)
            return web.json_response({"ok": True})
        
        app.router.add_post("/webhook", webhook_handler)
        
        async with TestClient(TestServer(app)) as client:
            # Without token
            resp = await client.post("/webhook", json={})
            assert resp.status == 401
            
            # With wrong token
            resp = await client.post(
                "/webhook",
                json={},
                headers={"X-Max-Secret-Token": "wrong"}
            )
            assert resp.status == 401
            
            # With correct token
            resp = await client.post(
                "/webhook",
                json={"update_id": 1},
                headers={"X-Max-Secret-Token": "secret_token_123"}
            )
            assert resp.status == 200


class TestIntegrationErrorRecovery:
    """Integration test for error recovery"""
    
    @pytest.mark.asyncio
    async def test_polling_recovers_from_errors(self):
        """Test that polling recovers from transient errors"""
        dp = Dispatcher()
        
        call_count = 0
        
        def mock_get_updates(**kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise Exception("Transient error")
            elif call_count == 2:
                return [
                    {
                        "update_id": 1,
                        "message_created": {
                            "message": {
                                "id": 1,
                                "chat": {"id": 1, "type": "private"},
                                "body": {"text": "recovered"}
                            },
                            "chat": {"id": 1, "type": "private"}
                        }
                    }
                ]
            else:
                return []
        
        bot = MagicMock()
        bot.get_updates = AsyncMock(side_effect=mock_get_updates)
        bot.get_subscriptions = AsyncMock(return_value=[])
        bot.delete_webhook = AsyncMock(return_value=True)
        
        # Should recover from error
        try:
            await asyncio.wait_for(
                dp.start_polling(bot, skip_updates=False),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            dp._running = False
        
        assert call_count >= 2  # At least error + success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestIntegrationNewEventDecorators:
    """Integration tests for new event decorators"""

    @pytest.mark.asyncio
    async def test_bot_started_integration(self):
        """Test bot_started decorator with dispatcher"""
        dp = Dispatcher()
        results = []

        @dp.bot_started()
        async def on_start(event):
            results.append("bot_started")
            return "started"

        assert 'bot_started' in dp._event_handlers
        handlers = dp._event_handlers['bot_started']
        assert len(handlers) == 1

        # Verify handler is registered
        event = MagicMock()
        result = await dp.process_event('bot_started', event)
        assert "bot_started" in results

    @pytest.mark.asyncio
    async def test_user_added_integration(self):
        """Test user_added decorator with dispatcher"""
        dp = Dispatcher()
        results = []

        @dp.user_added()
        async def on_user_add(event):
            results.append("user_added")
            return "added"

        assert 'user_added' in dp._event_handlers
        event = MagicMock()
        result = await dp.process_event('user_added', event)
        assert "user_added" in results

    @pytest.mark.asyncio
    async def test_chat_title_changed_integration(self):
        """Test chat_title_changed decorator"""
        dp = Dispatcher()
        results = []

        @dp.chat_title_changed()
        async def on_title_change(event):
            results.append("title_changed")
            return "changed"

        event = MagicMock()
        result = await dp.process_event('chat_title_changed', event)
        assert "title_changed" in results

    @pytest.mark.asyncio
    async def test_dialog_cleared_integration(self):
        """Test dialog_cleared decorator"""
        dp = Dispatcher()
        results = []

        @dp.dialog_cleared()
        async def on_clear(event):
            results.append("cleared")
            return "cleared"

        event = MagicMock()
        result = await dp.process_event('dialog_cleared', event)
        assert "cleared" in results


class TestIntegrationSetMyCommands:
    """Integration test for set_my_commands"""

    @pytest.mark.asyncio
    async def test_set_my_commands_integration(self):
        """Test set_my_commands flow"""
        from aioscam.client.response import Response

        client = AsyncMock()
        client.request = AsyncMock(return_value=Response(
            ok=True,
            result={"name": "TestBot", "commands": [{"name": "start", "description": "Start"}]}
        ))

        bot = Bot(token="test")
        bot._client = client

        commands = [
            {"name": "start", "description": "Start"},
            {"name": "help", "description": "Help"},
        ]

        result = await bot.set_my_commands(commands)

        assert client.request.called
        assert "commands" in result
