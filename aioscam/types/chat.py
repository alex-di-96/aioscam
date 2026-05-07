"""
Chat type
"""

from typing import Optional
from aioscam.types.base import MaxObject
from aioscam.enums import ChatType, ChatStatus


class Chat(MaxObject):
    """
    Represents a Max chat
    
    Attributes:
        id: Chat ID
        type: Chat type
        title: Chat title
        username: Chat username
        status: Chat status
        description: Chat description
        member_count: Number of members
        is_forum: Whether chat is a forum
    """
    
    id: int
    type: ChatType = ChatType.PRIVATE
    title: Optional[str] = None
    username: Optional[str] = None
    status: ChatStatus = ChatStatus.ACTIVE
    description: Optional[str] = None
    member_count: Optional[int] = None
    is_forum: Optional[bool] = None
    
    @property
    def full_title(self) -> str:
        """Get chat title or fallback to ID"""
        return self.title or f"Chat#{self.id}"
    
    @property
    def link(self) -> Optional[str]:
        """Get chat invite link"""
        if self.username:
            return f"https://max.ru/{self.username}"
        return None
