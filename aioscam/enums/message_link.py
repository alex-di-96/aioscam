"""
Message link type enum
"""

from enum import Enum


class MessageLinkType(str, Enum):
    """Types of message links"""
    
    DIRECT = "direct"
    FORWARD = "forward"
    REPLY = "reply"
