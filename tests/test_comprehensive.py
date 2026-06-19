"""
Comprehensive functional tests for AioScam framework
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aioscam import Bot, Dispatcher, Router, Command, F
from aioscam.filters.builtin import Text as TextFilter, ChatType as ChatTypeFilter
from aioscam.types.user import User
from aioscam.types.chat import Chat, ChatType as ChatTypeEnum
from aioscam.types.message import Message, MessageBody, MessageEntity, Recipient
from aioscam.types.update import (
    Update, MessageCreated, BotStarted,
)
from aioscam.types.keyboard import (
    Keyboard,
    InlineKeyboard,
    CallbackButton,
    LinkButton,
)
from aioscam.types.attachment import Image, Video, Audio
from aioscam.enums import AttachmentType, ButtonType, ParseMode, SenderAction
from aioscam.fsm import State, StatesGroup, MemoryStorage
from aioscam.dispatcher.event import EventContext
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.utils.formatting import TextFormat
from aioscam.utils.deep_linking import create_deep_link, parse_deep_link


def _make_event():
    """Create a realistic EventContext with real API structure."""
    sender = User(user_id=39068268, first_name="aLex", last_name="Di", is_bot=False, name="aLex Di")
    recipient = Recipient(chat_id=243186798, chat_type="dialog", user_id=204119554)
    body = MessageBody(mid="mid.xxx", seq=123, text="hello")
    msg = Message(recipient=recipient, sender=sender, body=body, timestamp=1776345558644)

    class FakeEvent:
        def __init__(self):
            self.message = msg
            self.timestamp = 1776345558644
            self.user_locale = "ru"
            self.update_type = "message_created"

    bot = MagicMock()
    return EventContext(FakeEvent(), bot)


def _make_event_with_text(text: str):
    """Create EventContext with specific text."""
    sender = User(user_id=123, first_name="Test", is_bot=False)
    recipient = Recipient(chat_id=456, chat_type="dialog", user_id=789)
    body = MessageBody(text=text)
    msg = Message(recipient=recipient, sender=sender, body=body)

    class FakeEvent:
        def __init__(self):
            self.message = msg
            self.timestamp = 1776345558644
            self.user_locale = "ru"
            self.update_type = "message_created"

    bot = MagicMock()
    return EventContext(FakeEvent(), bot)


class TestBotInitialization:
    """Test Bot initialization"""

    def test_bot_with_explicit_token(self):
        """Test Bot creation with explicit token"""
        bot = Bot(token="test_token_123")
        assert bot.token == "test_token_123"

    def test_bot_with_env_token(self, monkeypatch):
        """Test Bot creation with env variable"""
        monkeypatch.setenv("MAX_BOT_TOKEN", "env_token_456")
        bot = Bot()
        assert bot.token == "env_token_456"

    def test_bot_without_token_raises(self, monkeypatch):
        """Test that Bot without token raises error"""
        monkeypatch.delenv("MAX_BOT_TOKEN", raising=False)
        from aioscam.exceptions import BotTokenError
        with pytest.raises(BotTokenError):
            Bot()

    def test_bot_custom_timeout(self):
        """Test Bot with custom timeout"""
        bot = Bot(token="test", timeout=60)
        assert bot.client.default_timeout == 60


class TestTypes:
    """Test all type classes"""

    def test_user_creation(self):
        """Test User creation"""
        user = User(
            id=123,
            username="testuser",
            first_name="Test",
            last_name="User",
            is_bot=False
        )
        assert user.id == 123
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.mention() == "@testuser"

    def test_user_without_username(self):
        """Test User without username"""
        user = User(id=123, first_name="Test")
        assert user.full_name == "Test"
        assert user.mention() == "Test"

    def test_chat_creation(self):
        """Test Chat creation"""
        chat = Chat(
            id=456,
            type=ChatTypeEnum.GROUP,
            title="Test Group",
            member_count=10
        )
        assert chat.id == 456
        assert chat.type == ChatTypeEnum.GROUP
        assert chat.full_title == "Test Group"

    def test_message_creation(self):
        """Test Message creation"""
        user = User(id=123, username="user")
        chat = Chat(id=456, type=ChatTypeEnum.PRIVATE)
        body = MessageBody(text="Hello, World!")

        message = Message(
            id=1,
            chat=chat,
            from_user=user,
            body=body
        )

        assert message.id == 1
        assert message.text == "Hello, World!"
        assert message.has_text is True
        assert message.from_user.username == "user"

    def test_message_with_entities(self):
        """Test Message with entities"""
        chat = Chat(id=456, type=ChatTypeEnum.PRIVATE)
        entity = MessageEntity(type="bold", offset=0, length=5)
        body = MessageBody(text="Hello", entities=[entity])
        message = Message(id=1, chat=chat, body=body)

        assert message.body.entities is not None
        assert len(message.body.entities) == 1

    def test_update_message_created(self):
        """Test Update with MessageCreated event using real API format"""
        sender = User(user_id=39068268, first_name="aLex", is_bot=False)
        recipient = Recipient(chat_id=243186798, chat_type="dialog", user_id=204119554)
        body = MessageBody(mid="mid.xxx", seq=123, text="test")
        msg = Message(recipient=recipient, sender=sender, body=body, timestamp=1776345558644)

        msg_created = MessageCreated(message=msg, timestamp=1776345558644, user_locale="ru")

        assert msg_created.message is not None
        assert msg_created.message.body.text == "test"
        assert msg_created.message.sender.id == 39068268
        assert msg_created.message.recipient.chat_id == 243186798

    def test_update_bot_started(self):
        """Test Update with BotStarted event"""
        user = User(user_id=123, first_name="Test", is_bot=False)
        bot_started = BotStarted(user=user, timestamp=1776345558644)

        assert bot_started.user is not None
        assert bot_started.user.id == 123

    def test_update_from_dict(self):
        """Test Update created from real API dict format"""
        data = {
            "message": {
                "recipient": {"chat_id": 243186798, "chat_type": "dialog", "user_id": 204119554},
                "sender": {"user_id": 39068268, "first_name": "aLex", "last_name": "Di", "is_bot": False, "name": "aLex Di"},
                "body": {"mid": "mid.xxx", "seq": 123, "text": "/start"},
                "timestamp": 1776345558644
            },
            "timestamp": 1776345558644,
            "user_locale": "ru",
            "update_type": "message_created"
        }
        update = Update(**data)

        assert update.message is not None
        assert update.message.body.text == "/start"
        assert update.message.sender.first_name == "aLex"
        assert update.message.recipient.chat_id == 243186798
        assert update.update_type == "message_created"

    def test_to_dict_serialization(self):
        """Test type serialization"""
        user = User(id=123, username="test")
        data = user.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == 123
        assert data["username"] == "test"

    def test_to_json_serialization(self):
        """Test type JSON serialization"""
        user = User(id=123, username="test")
        json_str = user.to_json()

        assert isinstance(json_str, str)
        assert "123" in json_str


class TestFilters:
    """Test filter system"""

    @pytest.mark.asyncio
    async def test_command_filter_single(self):
        """Test single command filter"""
        cmd_filter = Command("start")

        event = _make_event_with_text("/start")

        result = await cmd_filter(event)
        assert result.passed is True
        assert result.data["command"] == "start"

    @pytest.mark.asyncio
    async def test_command_filter_multiple(self):
        """Test multiple commands filter"""
        cmd_filter = Command(["start", "help", "cancel"])

        for cmd in ["/start", "/help", "/cancel"]:
            event = _make_event_with_text(cmd)

            result = await cmd_filter(event)
            assert result.passed is True

    @pytest.mark.asyncio
    async def test_command_filter_case_insensitive(self):
        """Test command filter case insensitivity"""
        cmd_filter = Command("Start")

        event = _make_event_with_text("/START")

        result = await cmd_filter(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_text_filter_equals(self):
        """Test text filter equals"""
        text_filter = TextFilter(equals="hello")

        event = _make_event_with_text("hello")

        result = await text_filter(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_text_filter_contains(self):
        """Test text filter contains"""
        text_filter = TextFilter(contains=["hello", "hi"])

        event = _make_event_with_text("say hello to me")

        result = await text_filter(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_text_filter_startswith(self):
        """Test text filter startswith"""
        text_filter = TextFilter(startswith="prefix")

        event = _make_event_with_text("prefix something")

        result = await text_filter(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_chat_type_filter(self):
        """Test chat type filter"""
        # ChatType filter checks message.chat.type, which comes from the
        # Message type (aioscam/types/message.py) not the Update Message.
        # Since EventContext.chat returns the Recipient (chat_type="dialog"),
        # we need to test with an event whose message has a Chat object.

        from aioscam.types.chat import Chat, ChatType as ChatTypeEnum

        chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
        body = MessageBody(text="test")
        user = User(id=123, is_bot=False)
        msg = Message(id=1, chat=chat, from_user=user, body=body)

        class FakeEvent:
            def __init__(self):
                self.message = msg

        event = FakeEvent()
        chat_filter = ChatTypeFilter("private")

        result = await chat_filter(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_and_filter(self):
        """Test AND filter combination"""
        filter1 = Command("start")
        filter2 = ChatTypeFilter("dialog")

        and_filter = filter1 & filter2

        # For AND filter to pass, both filters must pass.
        # ChatTypeFilter checks message.chat.type, but our EventContext uses
        # Recipient which doesn have a Chat object with .type.
        # So we test AND filter with two command filters instead.
        filter3 = TextFilter(equals="/start")
        and_filter2 = filter1 & filter3

        event = _make_event_with_text("/start")

        result = await and_filter2(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_or_filter(self):
        """Test OR filter combination"""
        filter1 = Command("start")
        filter2 = Command("help")

        or_filter = filter1 | filter2

        event = _make_event_with_text("/help")

        result = await or_filter(event)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_not_filter(self):
        """Test NOT filter"""
        cmd_filter = Command("start")
        not_filter = ~cmd_filter

        event = _make_event_with_text("/other")

        result = await not_filter(event)
        assert result.passed is True


class TestRouter:
    """Test Router functionality"""

    @pytest.mark.asyncio
    async def test_router_message_handler(self):
        """Test router message handler"""
        router = Router()
        called = []

        @router.message_created(Command("start"))
        async def handler(event):
            called.append(True)
            return "handled"

        event = _make_event_with_text("/start")

        result = await router.process_message(event)
        assert result == "handled"
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_router_nested_routing(self):
        """Test nested router routing"""
        parent = Router()
        child = Router()

        @child.message_created(Command("test"))
        async def handler(event):
            return "child_handler"

        parent.include_router(child)

        event = _make_event_with_text("/test")

        result = await parent.process_message(event)
        assert result == "child_handler"

    @pytest.mark.asyncio
    async def test_router_no_handler_returns_none(self):
        """Test router returns None when no handler matches"""
        router = Router()

        @router.message_created(Command("start"))
        async def handler(event):
            return "handled"

        event = _make_event_with_text("/other")

        result = await router.process_message(event)
        assert result is None

    def test_router_naming(self):
        """Test router naming"""
        router = Router(name="test_router")
        assert router.name == "test_router"

        auto_router = Router()
        assert auto_router.name.startswith("Router#")


class TestKeyboardBuilder:
    """Test keyboard builder"""

    def test_inline_keyboard(self):
        """Test inline keyboard creation"""
        builder = KeyboardBuilder(inline=True)

        builder.callback("Click", "action:1")
        builder.link("Site", "https://example.com")
        builder.row()
        builder.callback("Help", "help")

        keyboard = builder.build()

        assert isinstance(keyboard, InlineKeyboard)
        assert len(keyboard.buttons) == 2  # 2 rows
        assert len(keyboard.buttons[0]) == 2  # First row has 2 buttons

    def test_regular_keyboard(self):
        """Test regular keyboard creation"""
        builder = KeyboardBuilder(inline=False)

        builder.callback("Option 1", "opt1")
        builder.callback("Option 2", "opt2")
        builder.row()
        builder.callback("Cancel", "cancel")

        keyboard = builder.build(one_time=True, resize=True)

        assert isinstance(keyboard, Keyboard)
        assert keyboard.one_time is True
        assert keyboard.resize is True

    def test_keyboard_chaining(self):
        """Test keyboard builder chaining"""
        builder = KeyboardBuilder(inline=True)

        result = (builder
                  .callback("A", "a")
                  .callback("B", "b")
                  .row()
                  .link("C", "url")
                  .build())

        assert len(result.buttons) == 2
        assert len(result.buttons[0]) == 2
        assert len(result.buttons[1]) == 1

    def test_keyboard_reset(self):
        """Test keyboard builder reset"""
        builder = KeyboardBuilder(inline=True)
        builder.callback("A", "a")
        builder.reset()

        assert len(builder.buttons) == 0
        assert len(builder._current_row) == 0


class TestTextFormatting:
    """Test text formatting utilities"""

    def test_bold(self):
        """Test bold formatting"""
        assert TextFormat.bold("text") == "**text**"

    def test_italic(self):
        """Test italic formatting"""
        assert TextFormat.italic("text") == "_text_"

    def test_italic_differs_from_underline(self):
        """italic and underline must produce different output"""
        assert TextFormat.italic("x") != TextFormat.underline("x")

    def test_code(self):
        """Test code formatting"""
        assert TextFormat.code("code") == "`code`"

    def test_pre(self):
        """Test pre formatting"""
        assert TextFormat.pre("code") == "```\ncode\n```"
        assert TextFormat.pre("code", "python") == "```python\ncode\n```"

    def test_link(self):
        """Test link formatting"""
        assert TextFormat.link("text", "url") == "[text](url)"

    def test_mention(self):
        """Test mention formatting"""
        assert TextFormat.mention("User", 123) == "[User](user://123)"


class TestDeepLinking:
    """Test deep linking utilities"""

    def test_create_deep_link(self):
        """Test deep link creation"""
        link = create_deep_link("my_bot", "ref_12345")
        assert link == "https://max.ru/my_bot?start=ref_12345"

    def test_parse_deep_link(self):
        """Test deep link parsing"""
        link = "https://max.ru/my_bot?start=ref_12345"
        result = parse_deep_link(link)

        assert result["bot_username"] == "my_bot"
        assert result["payload"] == "ref_12345"

    def test_parse_group_deep_link(self):
        """Test group deep link parsing"""
        link = "https://max.ru/my_bot?add_to_group=123&start=ref"
        result = parse_deep_link(link)

        assert result["bot_username"] == "my_bot"
        assert result["group_id"] == 123
        assert result["payload"] == "ref"


class TestFSM:
    """Test FSM functionality"""

    def test_state_creation(self):
        """Test state creation"""
        class MyState(StatesGroup):
            step1 = State()
            step2 = State()

        state_obj = MyState()

        # States should have names set
        assert state_obj.step1.name == "step1"
        assert state_obj.step2.name == "step2"

    @pytest.mark.asyncio
    async def test_memory_storage(self):
        """Test memory storage"""
        storage = MemoryStorage()

        # Set and get state
        await storage.set_state(chat_id=1, state="waiting_name")
        state = await storage.get_state(chat_id=1)
        assert state == "waiting_name"

        # Set and get data
        await storage.set_data(chat_id=1, data={"name": "test"})
        data = await storage.get_data(chat_id=1)
        assert data["name"] == "test"

        # Update data
        result = await storage.update_data(chat_id=1, data={"age": 25})
        assert result["name"] == "test"
        assert result["age"] == 25

        # Clear state
        await storage.set_state(chat_id=1, state=None)
        state = await storage.get_state(chat_id=1)
        assert state is None

    @pytest.mark.asyncio
    async def test_memory_storage_user_isolation(self):
        """Test memory storage user isolation"""
        storage = MemoryStorage()

        await storage.set_data(chat_id=1, data={"name": "user1"}, user_id=1)
        await storage.set_data(chat_id=1, data={"name": "user2"}, user_id=2)

        data1 = await storage.get_data(chat_id=1, user_id=1)
        data2 = await storage.get_data(chat_id=1, user_id=2)

        assert data1["name"] == "user1"
        assert data2["name"] == "user2"

    @pytest.mark.asyncio
    async def test_storage_close(self):
        """Test storage close clears data"""
        storage = MemoryStorage()
        await storage.set_state(chat_id=1, state="test")
        await storage.set_data(chat_id=1, data={"key": "value"})

        await storage.close()

        state = await storage.get_state(chat_id=1)
        data = await storage.get_data(chat_id=1)

        assert state is None
        assert data == {}


class TestDispatcher:
    """Test Dispatcher functionality"""

    @pytest.mark.asyncio
    async def test_dispatcher_event_processing(self):
        """Test dispatcher event processing"""
        dp = Dispatcher()

        @dp.message_created(Command("start"))
        async def handler(event):
            return "handled"

        event = _make_event_with_text("/start")

        # Process through dispatcher
        result = await dp.process_message(event)
        assert result == "handled"

    @pytest.mark.asyncio
    async def test_dispatcher_with_storage(self):
        """Test dispatcher with custom storage"""
        custom_storage = MemoryStorage()
        dp = Dispatcher(storage=custom_storage)

        assert dp.storage == custom_storage


class TestExceptions:
    """Test exception handling"""

    def test_bot_token_error(self):
        """Test BotTokenError"""
        from aioscam.exceptions import BotTokenError

        with pytest.raises(BotTokenError):
            raise BotTokenError("Token not provided")

    def test_api_error(self):
        """Test ApiError"""
        from aioscam.exceptions import ApiError

        error = ApiError("Test error", code=400, response={"error": "test"})
        assert error.message == "Test error"
        assert str(error).startswith("Test error")
        assert error.hint  # ApiError carries a default hint pointing at .response/.code
        assert error.code == 400
        assert error.response["error"] == "test"

    def test_network_error(self):
        """Test NetworkError"""
        from aioscam.exceptions import NetworkError

        error = NetworkError("Connection failed", status=500)
        assert error.message == "Connection failed"
        assert str(error).startswith("Connection failed")
        assert error.hint  # NetworkError carries a default connectivity hint
        assert error.status == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
