"""
Chat related enums
"""

from enum import Enum


class ChatType(str, Enum):
    """Types of chats"""
    
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class ChatStatus(str, Enum):
    """Chat status"""
    
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ChatPermission(str, Enum):
    """Chat permissions"""
    
    ADMIN = "admin"
    MEMBER = "member"
    OWNER = "owner"
    RESTRICTED = "restricted"
