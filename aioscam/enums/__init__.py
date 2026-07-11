"""
Enums for Max API
"""

from aioscam.enums.api_path import ApiPath
from aioscam.enums.attachment import AttachmentType
from aioscam.enums.button import ButtonType
from aioscam.enums.chat import ChatAdminPermission, ChatStatus, ChatType, ChatPermission
from aioscam.enums.http_method import HttpMethod
from aioscam.enums.intent import Intent
from aioscam.enums.message_link import MessageLinkType
from aioscam.enums.parse_mode import ParseMode
from aioscam.enums.sender_action import SenderAction
from aioscam.enums.text_style import TextStyle
from aioscam.enums.update import UpdateType
from aioscam.enums.upload import UploadType

__all__ = [
    "ApiPath",
    "AttachmentType",
    "ButtonType",
    "ChatAdminPermission",
    "ChatStatus",
    "ChatType",
    "ChatPermission",
    "HttpMethod",
    "Intent",
    "MessageLinkType",
    "ParseMode",
    "SenderAction",
    "TextStyle",
    "UpdateType",
    "UploadType",
]
