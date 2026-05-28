"""
Attachment types
"""

import os
from typing import Optional
from aioscam.types.base import MaxObject
from aioscam.enums import AttachmentType
from aioscam.enums.upload import UploadType


# ── Outgoing attachment types (for sending) ──────────────────────────────────

class AttachmentPayload(MaxObject):
    """Upload token wrapper — used in outgoing attachments after file upload"""
    token: str


class AttachmentUpload(MaxObject):
    """
    Outgoing attachment ready for sending via send_message attachments list.

    Usage:
        att = AttachmentUpload(type=UploadType.IMAGE, payload=AttachmentPayload(token="..."))
        await bot.send_message(chat_id=..., text="", attachments=[att.to_dict()])
    """
    type: str
    payload: AttachmentPayload

    def to_dict(self) -> dict:
        return {"type": self.type, "payload": {"token": self.payload.token}}


# ── InputMedia classes (local files / buffers) ────────────────────────────────

_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.heic'}
_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.flv', '.ts'}
_AUDIO_EXTS = {'.mp3', '.ogg', '.wav', '.m4a', '.flac', '.aac', '.opus', '.wma'}


def _detect_type_by_ext(filename: str) -> UploadType:
    ext = os.path.splitext(filename)[1].lower()
    if ext in _IMAGE_EXTS:
        return UploadType.IMAGE
    if ext in _VIDEO_EXTS:
        return UploadType.VIDEO
    if ext in _AUDIO_EXTS:
        return UploadType.AUDIO
    return UploadType.FILE


class InputMedia:
    """
    Local file for sending as attachment.

    Automatically detects upload type by file extension.

    Usage:
        media = InputMedia("photo.jpg")            # IMAGE
        media = InputMedia("video.mp4")            # VIDEO
        media = InputMedia("doc.pdf")              # FILE
        media = InputMedia("photo.jpg", UploadType.IMAGE)  # explicit
    """

    def __init__(self, path: str, upload_type: Optional[UploadType] = None):
        self.path = path
        self.type: UploadType = upload_type or _detect_type_by_ext(path)


class InputMediaBuffer:
    """
    In-memory bytes buffer for sending as attachment.

    Usage:
        data = open("photo.jpg", "rb").read()
        media = InputMediaBuffer(data, "photo.jpg")
        media = InputMediaBuffer(data, "report.pdf", UploadType.FILE)
    """

    def __init__(
        self,
        buffer: bytes,
        filename: str = "file",
        upload_type: Optional[UploadType] = None,
    ):
        self.buffer = buffer
        self.filename = filename
        self.type: UploadType = upload_type or _detect_type_by_ext(filename)


# ── Incoming attachment types (from events) ───────────────────────────────────

class Attachment(MaxObject):
    """
    Base attachment class (incoming from events)
    """

    type: AttachmentType
    payload: Optional[dict] = None

    def get_url(self) -> Optional[str]:
        """URL for download (from attachment payload)"""
        if isinstance(self.payload, dict):
            return self.payload.get("url")
        return None

    def get_token(self) -> Optional[str]:
        """Auth token for download"""
        if isinstance(self.payload, dict):
            return self.payload.get("token")
        return None


class Image(Attachment):
    """Image attachment (incoming)"""
    type: AttachmentType = AttachmentType.IMAGE

    def get_photo_token(self) -> Optional[str]:
        """For image, token may be nested: payload.photos[key].token"""
        if isinstance(self.payload, dict):
            photos = self.payload.get("photos", {})
            if isinstance(photos, dict) and photos:
                key = next(iter(photos))
                photo = photos[key]
                if isinstance(photo, dict):
                    return photo.get("token")
            return self.payload.get("token")
        return None


class Video(Attachment):
    """Video attachment (incoming)"""
    type: AttachmentType = AttachmentType.VIDEO
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None

    def get_best_url(self) -> Optional[str]:
        """Return highest resolution URL available"""
        if isinstance(self.payload, dict):
            urls = self.payload.get("urls", {})
            if isinstance(urls, dict):
                for quality in ("mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240", "mp4_144"):
                    if urls.get(quality):
                        return urls[quality]
        return self.get_url()


class Audio(Attachment):
    """Audio attachment (incoming)"""
    type: AttachmentType = AttachmentType.AUDIO
    duration: Optional[int] = None
    transcription: Optional[str] = None


class File(Attachment):
    """File/document attachment (incoming)"""
    type: AttachmentType = AttachmentType.FILE
    filename: Optional[str] = None
    size: Optional[int] = None


class Sticker(Attachment):
    """
    Sticker attachment (incoming only — bots cannot send stickers).

    Payload: {url: str, code: str}
    """
    type: AttachmentType = AttachmentType.STICKER
    width: Optional[int] = None
    height: Optional[int] = None

    def get_code(self) -> Optional[str]:
        if isinstance(self.payload, dict):
            return self.payload.get("code")
        return None


class Contact(Attachment):
    """Contact attachment (incoming)"""
    type: AttachmentType = AttachmentType.CONTACT


class Location(Attachment):
    """Location attachment (incoming)"""
    type: AttachmentType = AttachmentType.LOCATION
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Share(Attachment):
    """Share attachment — forwarded message link (incoming)"""
    type: AttachmentType = AttachmentType.SHARE


# ── Upload result (legacy / low-level) ───────────────────────────────────────

class Upload(MaxObject):
    """Raw upload URL result from /uploads endpoint"""
    url: Optional[str] = None
    token: Optional[str] = None
