"""
Update types - All possible events (based on real Max API format)
"""

from typing import Optional, Dict, Any
from datetime import datetime
from aioscam.types.base import MaxObject


class MessageBody(MaxObject):
    """Message body"""
    mid: Optional[str] = None
    seq: Optional[int] = None
    text: Optional[str] = None


class User(MaxObject):
    """User information"""
    user_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    is_bot: bool = False
    last_activity_time: Optional[int] = None


class Recipient(MaxObject):
    """Message recipient"""
    chat_id: Optional[int] = None
    chat_type: Optional[str] = None
    user_id: Optional[int] = None


class Message(MaxObject):
    """Message from update"""
    recipient: Optional[Recipient] = None
    sender: Optional[User] = None
    body: Optional[MessageBody] = None
    timestamp: Optional[int] = None


class MessageCreated(MaxObject):
    """Message created event"""
    message: Optional[Message] = None
    timestamp: Optional[int] = None
    user_locale: Optional[str] = None


class BotStarted(MaxObject):
    """Bot started event"""
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
        if self.update_type in ("message_created", "message_callback"):
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
        """Get message sender"""
        if self.message:
            return self.message.sender
        return None
    
    @property
    def recipient(self) -> Optional[Recipient]:
        """Get message recipient"""
        if self.message:
            return self.message.recipient
        return None
