"""
Update types - All possible events (based on real Max API format)

Uses rich types from types/user.py, types/message.py for consistency.
Raw API field names (user_id, mid, seq) are supported via aliases.
"""

from typing import Optional, Dict, Any
from aioscam.types.base import MaxObject
from aioscam.types.user import User
from aioscam.types.message import Message, MessageBody, Recipient


class MessageCreated(MaxObject):
    """Message created event"""
    message: Optional[Message] = None
    timestamp: Optional[int] = None
    user_locale: Optional[str] = None


class BotStarted(MaxObject):
    """Bot started event"""
    user: Optional[User] = None
    timestamp: Optional[int] = None


class MessageCallback(MaxObject):
    """Callback event"""
    id: Optional[str] = None
    data: Optional[str] = None
    chat_id: Optional[int] = None
    message_id: Optional[int] = None
    user: Optional[User] = None
    timestamp: Optional[int] = None


class Update(MaxObject):
    """
    Update from Max API

    Real format:
    {
        "message": {...},
        "callback": {...},
        "timestamp": 1776344472771,
        "user_locale": "ru",
        "update_type": "message_created"
    }
    """

    # Real fields from API
    message: Optional[Message] = None
    callback: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None
    user_locale: Optional[str] = None
    update_type: Optional[str] = None

    # bot_started fields
    payload: Optional[str] = None
    user_id: Optional[int] = None
    chat_id: Optional[int] = None
    user: Optional[User] = None

    # Compatibility field
    update_id: Optional[int] = None

    def __init__(self, **data):
        # Generate update_id from timestamp if not present
        if 'update_id' not in data:
            data['update_id'] = data.get('timestamp')
        super().__init__(**data)

    @property
    def event_type(self) -> Optional[str]:
        """Get update type"""
        return self.update_type

    @property
    def event(self) -> Optional["Update"]:
        """Get event object (returns self for direct access)"""
        if self.update_type:
            return self
        return None

    @property
    def text(self) -> Optional[str]:
        """Get message text if present"""
        if self.message and self.message.body:
            return self.message.body.text
        return None

    @property
    def sender(self) -> Optional[User]:
        """Get message sender or bot_started user"""
        if self.message:
            return self.message.sender
        # bot_started: user is the one who started the bot
        return self.user

    @property
    def recipient(self) -> Optional[Recipient]:
        """Get message recipient or bot_started chat"""
        if self.message:
            return self.message.recipient
        # bot_started: create recipient from chat_id
        if self.chat_id:
            return Recipient(chat_id=self.chat_id, chat_type="dialog", user_id=self.user_id)
        return None
