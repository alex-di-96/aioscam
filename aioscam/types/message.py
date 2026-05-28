"""
Message types
"""

from typing import List, Optional
from datetime import datetime

from pydantic import Field

from aioscam.types.base import MaxObject
from aioscam.types.user import User
from aioscam.types.chat import Chat
from aioscam.types.attachment import Attachment
from aioscam.enums import ParseMode, MessageLinkType


class Recipient(MaxObject):
    """Message recipient — used in raw API updates"""
    chat_id: Optional[int] = None
    chat_type: Optional[str] = None
    user_id: Optional[int] = None


class MessageEntity(MaxObject):
    """
    Represents a special entity in a message text
    
    Attributes:
        type: Entity type
        offset: Offset in text
        length: Entity length
        url: URL for link entity
        user: User for mention entity
        language: Language for code entity
    """
    
    type: str
    offset: int
    length: int
    url: Optional[str] = None
    user: Optional[User] = None
    language: Optional[str] = None


class MessageBody(MaxObject):
    """
    Represents message body/content

    Attributes:
        text: Message text
        entities: Message entities (formatting)
        parse_mode: Text parse mode
        mid: Message ID from API (raw field)
        seq: Sequence number from API (raw field)
    """

    text: Optional[str] = None
    entities: Optional[List[MessageEntity]] = None
    parse_mode: Optional[ParseMode] = None
    # Raw API fields (present in polling/webhook updates)
    mid: Optional[str] = None
    seq: Optional[int] = None
    
    @property
    def has_text(self) -> bool:
        """Check if message has text"""
        return bool(self.text and self.text.strip())


class Message(MaxObject):
    """
    Represents a Max message

    Attributes:
        id: Message ID (optional for raw API parsing)
        chat: Chat where message was sent
        from_user: Message sender (alias: 'sender' for raw API)
        date: Message date
        body: Message body
        reply_to_message: Replied message
        forward_from: Forward source
        link_type: Message link type
        attachments: Message attachments
        keyboard: Message keyboard
        is_pinned: Whether message is pinned
        edit_date: Message edit date
        recipient: Message recipient (raw API field)
        sender: Alias for from_user (raw API compat)
        timestamp: Message timestamp (raw API compat)
    """

    id: Optional[int] = None
    chat: Optional[Chat] = None
    from_user: Optional[User] = Field(default=None, alias="sender")
    date: Optional[datetime] = None
    body: Optional[MessageBody] = None
    reply_to_message: Optional["Message"] = None
    forward_from: Optional["Message"] = None
    link_type: Optional[MessageLinkType] = None
    attachments: Optional[List[Attachment]] = None
    keyboard: Optional[dict] = None
    is_pinned: bool = False
    edit_date: Optional[datetime] = None
    # Raw API compat fields
    recipient: Optional[Recipient] = None
    timestamp: Optional[int] = None

    @property
    def sender(self) -> Optional[User]:
        """Alias for from_user (raw API compat)"""
        return self.from_user
    
    @property
    def text(self) -> Optional[str]:
        """Get message text"""
        return self.body.text if self.body else None
    
    @property
    def has_text(self) -> bool:
        """Check if message has text"""
        return self.body.has_text if self.body else False
    
    @property
    def has_attachments(self) -> bool:
        """Check if message has attachments"""
        return bool(self.attachments)
    
    async def answer(
        self,
        text: str,
        reply_to_message_id: Optional[int] = None,
        **kwargs,
    ) -> "Message":
        """
        Reply to this message
        
        Args:
            text: Reply text
            reply_to_message_id: Reply to message ID
            **kwargs: Additional send_message parameters
        
        Returns:
            Sent message
        """
        # This method will be injected by Bot class
        raise NotImplementedError(
            "Use Bot.send_message() with reply_to_message_id parameter"
        )
