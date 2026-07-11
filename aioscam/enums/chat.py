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


class ChatAdminPermission(str, Enum):
    """Admin permission values accepted by POST /chats/{id}/members/admins"""

    READ_ALL_MESSAGES = "read_all_messages"
    ADD_REMOVE_MEMBERS = "add_remove_members"
    ADD_ADMINS = "add_admins"
    CHANGE_CHAT_INFO = "change_chat_info"
    PIN_MESSAGE = "pin_message"
    EDIT_LINK = "edit_link"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    CAN_CALL = "can_call"
    VIEW_STATS = "view_stats"
