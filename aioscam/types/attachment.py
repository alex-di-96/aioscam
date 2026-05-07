"""
Attachment types
"""

from typing import Optional
from aioscam.types.base import MaxObject
from aioscam.enums import AttachmentType


class Attachment(MaxObject):
    """
    Base attachment class
    
    Attributes:
        type: Attachment type
        file_id: File ID
        file_size: File size in bytes
        file_name: File name
        mime_type: MIME type
    """
    
    type: AttachmentType
    file_id: Optional[str] = None
    file_size: Optional[int] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None


class Image(Attachment):
    """
    Image attachment
    
    Attributes:
        width: Image width
        height: Image height
        duration: Animation duration (for GIF)
    """
    
    type: AttachmentType = AttachmentType.IMAGE
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None


class Video(Attachment):
    """
    Video attachment
    
    Attributes:
        width: Video width
        height: Video height
        duration: Video duration
        thumbnail: Video thumbnail
    """
    
    type: AttachmentType = AttachmentType.VIDEO
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None


class Audio(Attachment):
    """
    Audio attachment
    
    Attributes:
        duration: Audio duration
        title: Audio title
        performer: Performer name
    """
    
    type: AttachmentType = AttachmentType.AUDIO
    duration: Optional[int] = None
    title: Optional[str] = None
    performer: Optional[str] = None


class File(Attachment):
    """
    Document/file attachment
    """
    
    type: AttachmentType = AttachmentType.FILE


class Sticker(Attachment):
    """
    Sticker attachment
    
    Attributes:
        emoji: Sticker emoji
        set_name: Sticker set name
    """
    
    type: AttachmentType = AttachmentType.STICKER
    emoji: Optional[str] = None
    set_name: Optional[str] = None


class Contact(Attachment):
    """
    Contact attachment
    
    Attributes:
        phone_number: Contact phone
        first_name: Contact first name
        last_name: Contact last name
        user_id: Contact user ID
    """
    
    type: AttachmentType = AttachmentType.CONTACT
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_id: Optional[int] = None


class Location(Attachment):
    """
    Location attachment
    
    Attributes:
        latitude: Latitude
        longitude: Longitude
    """
    
    type: AttachmentType = AttachmentType.LOCATION
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Share(Attachment):
    """
    Share attachment (forwarded message link)
    """
    
    type: AttachmentType = AttachmentType.SHARE


class Upload(MaxObject):
    """
    File upload result
    
    Attributes:
        file_id: Uploaded file ID
        file_size: File size
        file_name: File name
        url: File URL
    """
    
    file_id: Optional[str] = None
    file_size: Optional[int] = None
    file_name: Optional[str] = None
    url: Optional[str] = None


class InputMedia(MaxObject):
    """
    Input media for sending/editing
    
    Attributes:
        type: Media type
        media: Media content (file path, URL, or file_id)
        caption: Media caption
        parse_mode: Parse mode for caption
    """
    
    type: AttachmentType
    media: str
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
