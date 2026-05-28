"""
Attachment types enum
"""

from enum import Enum


class AttachmentType(str, Enum):
    """Types of attachments in messages"""
    
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    STICKER = "sticker"
    CONTACT = "contact"
    LOCATION = "location"
    SHARE = "share"
