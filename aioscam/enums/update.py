"""
Update type enum
"""

from enum import Enum


class UpdateType(str, Enum):
    """Types of updates that can be received"""
    
    # Bot events
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_ADDED = "bot_added"
    BOT_REMOVED = "bot_removed"
    
    # Message events
    MESSAGE_CREATED = "message_created"
    MESSAGE_EDITED = "message_edited"
    MESSAGE_REMOVED = "message_removed"
    MESSAGE_CALLBACK = "message_callback"
    
    # Chat events
    MESSAGE_CHAT_CREATED = "message_chat_created"
    CHAT_TITLE_CHANGED = "chat_title_changed"
    DIALOG_CLEARED = "dialog_cleared"
    DIALOG_MUTED = "dialog_muted"
    DIALOG_UNMUTED = "dialog_unmuted"
    DIALOG_REMOVED = "dialog_removed"
    
    # User events
    USER_ADDED = "user_added"
    USER_REMOVED = "user_removed"
