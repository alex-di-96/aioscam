"""
Message types
"""

from typing import List, Optional
from datetime import datetime

from aioscam.types.base import MaxObject
from aioscam.types.user import User
from aioscam.types.chat import Chat
from aioscam.types.attachment import Attachment
from aioscam.enums import ParseMode, MessageLinkType


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
    """
    
    text: Optional[str] = None
    entities: Optional[List[MessageEntity]] = None
    parse_mode: Optional[ParseMode] = None
    
    @property
    def has_text(self) -> bool:
        """Check if message has text"""
        return bool(self.text and self.text.strip())


class Message(MaxObject):
    """
    Represents a Max message
    
    Attributes:
        id: Message ID
        chat: Chat where message was sent
        from_user: Message sender
        date: Message date
        body: Message body
        reply_to_message: Replied message
        forward_from: Forward source
        link_type: Message link type
        attachments: Message attachments
        keyboard: Message keyboard
        is_pinned: Whether message is pinned
        edit_date: Message edit date
    """
    
    id: int
    chat: Chat
    from_user: Optional[User] = None
    date: Optional[datetime] = None
    body: Optional[MessageBody] = None
    reply_to_message: Optional["Message"] = None
    forward_from: Optional["Message"] = None
    link_type: Optional[MessageLinkType] = None
    attachments: Optional[List[Attachment]] = None
    keyboard: Optional[dict] = None
    is_pinned: bool = False
    edit_date: Optional[datetime] = None
    
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
