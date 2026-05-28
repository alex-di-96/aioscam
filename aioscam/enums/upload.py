"""
Upload type enum
"""

from enum import Enum


class UploadType(str, Enum):
    """Types of file uploads"""
    
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
