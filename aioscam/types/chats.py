"""
Chats type
"""

from typing import List, Optional
from aioscam.types.base import MaxObject
from aioscam.types.chat import Chat


class Chats(MaxObject):
    """
    List of chats
    
    Attributes:
        chats: List of chat objects
        total_count: Total number of chats
    """
    
    chats: List[Chat] = []
    total_count: Optional[int] = None
