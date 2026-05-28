"""
Sender action enum
"""

from enum import Enum


class SenderAction(str, Enum):
    """Actions that can be sent as typing indicators"""
    
    TYPING = "typing"
    UPLOAD_PHOTO = "upload_photo"
    RECORD_VIDEO = "record_video"
    UPLOAD_VIDEO = "upload_video"
    RECORD_AUDIO = "record_audio"
    UPLOAD_AUDIO = "upload_audio"
    UPLOAD_DOCUMENT = "upload_document"
    FINDING_LOCATION = "finding_location"
    CHOOSING_STICKER = "choosing_sticker"
