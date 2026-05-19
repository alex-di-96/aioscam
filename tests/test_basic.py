"""
Test basic functionality
"""

import pytest
from aioscam.types.user import User
from aioscam.types.chat import Chat
from aioscam.types.message import Message, MessageBody
from aioscam.enums import ChatType, UpdateType


class TestTypes:
    """Test type classes"""
    
    def test_user_creation(self):
        """Test User object creation"""
        user = User(
            id=12345,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        assert user.id == 12345
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.mention() == "@testuser"
    
    def test_user_without_username(self):
        """Test User without username"""
        user = User(id=12345, first_name="Test")
        assert user.mention() == "Test"
    
    def test_chat_creation(self):
        """Test Chat object creation"""
        chat = Chat(
            id=67890,
            type=ChatType.PRIVATE,
            title="Test Chat"
        )
        assert chat.id == 67890
        assert chat.type == ChatType.PRIVATE
        assert chat.full_title == "Test Chat"
    
    def test_message_creation(self):
        """Test Message object creation"""
        user = User(id=12345, username="testuser")
        chat = Chat(id=67890, type=ChatType.PRIVATE)
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
        assert message.from_user.username == "testuser"
    
    def test_message_without_text(self):
        """Test Message without text"""
        chat = Chat(id=67890, type=ChatType.PRIVATE)
        message = Message(id=1, chat=chat)
        
        assert message.has_text is False


class TestEnums:
    """Test enum classes"""
    
    def test_chat_type(self):
        """Test ChatType enum"""
        assert ChatType.PRIVATE.value == "private"
        assert ChatType.GROUP.value == "group"
    
    def test_update_type(self):
        """Test UpdateType enum"""
        assert UpdateType.MESSAGE_CREATED.value == "message_created"
        assert UpdateType.BOT_STARTED.value == "bot_started"


class TestBotToken:
    """Test Bot token handling"""
    
    def test_missing_token(self):
        """Test Bot raises error without token"""
        import os
        old_token = os.environ.get("MAX_BOT_TOKEN")
        if "MAX_BOT_TOKEN" in os.environ:
            del os.environ["MAX_BOT_TOKEN"]
        
        from aioscam.bot import Bot
        from aioscam.exceptions import BotTokenError
        
        with pytest.raises(BotTokenError):
            Bot()
        
        if old_token:
            os.environ["MAX_BOT_TOKEN"] = old_token


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
