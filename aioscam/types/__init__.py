"""
Types module - All data structures for Max API
"""

from aioscam.types.base import MaxObject
from aioscam.types.user import User
from aioscam.types.chat import Chat
from aioscam.types.message import Message, MessageBody, MessageEntity
from aioscam.types.update import Update
from aioscam.types.keyboard import (
    Keyboard,
    InlineKeyboard,
    Button,
    CallbackButton,
    LinkButton,
    ChatButton,
    MessageButton,
    ClipboardButton,
    OpenAppButton,
    RequestContactButton,
    RequestGeoLocationButton,
)
from aioscam.types.attachment import (
    Attachment,
    Audio,
    Contact,
    File,
    Image,
    Location,
    Share,
    Sticker,
    Upload,
    InputMedia,
)
from aioscam.types.callback import Callback
from aioscam.types.chats import Chats
from aioscam.types.subscription import Subscription
from aioscam.types.command import Command, BotCommand

__all__ = [
    "MaxObject",
    "User",
    "Chat",
    "Message",
    "MessageBody",
    "MessageEntity",
    "Update",
    "Keyboard",
    "InlineKeyboard",
    "Button",
    "CallbackButton",
    "LinkButton",
    "ChatButton",
    "MessageButton",
    "ClipboardButton",
    "OpenAppButton",
    "RequestContactButton",
    "RequestGeoLocationButton",
    "Attachment",
    "Audio",
    "Contact",
    "File",
    "Image",
    "Location",
    "Share",
    "Sticker",
    "Upload",
    "InputMedia",
    "Callback",
    "Chats",
    "Subscription",
    "Command",
    "BotCommand",
]
