"""
Upload type enum
"""

from enum import Enum


class UploadType(str, Enum):
    """Types of file uploads — values must match Max API `type` param"""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
