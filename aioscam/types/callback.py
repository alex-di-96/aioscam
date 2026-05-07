"""
Callback type
"""

from typing import Optional
from aioscam.types.base import MaxObject


class Callback(MaxObject):
    """
    Callback query data
    
    Attributes:
        id: Callback ID
        data: Callback data
        chat_id: Chat ID
        message_id: Message ID
        from_user: User who triggered callback
    """
    
    id: str
    data: str
    chat_id: int
    message_id: int
    from_user: Optional[dict] = None
