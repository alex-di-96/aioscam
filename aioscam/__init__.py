"""
AioScam - Async framework for Max messenger bots (aiogram-style)
"""

__version__ = "0.1.8"
__author__ = "AioScam Contributors"

from aioscam.bot import Bot
from aioscam.dispatcher import Dispatcher, Router
from aioscam.filters import Command, StartCommand, F, StateFilter
from aioscam.types.command import BotCommand
from aioscam.types.attachment import InputMedia, InputMediaBuffer
from aioscam.enums.upload import UploadType
from aioscam.config import Config, get_config, EnvMode
from aioscam.methods import BaseMethod, SendMessage, GetMe, GetUpdates, SendCallback
from aioscam.i18n import I18n

__all__ = [
    "Bot",
    "Dispatcher",
    "Router",
    "Command",
    "StartCommand",
    "BotCommand",
    "F",
    "StateFilter",
    "Config",
    "get_config",
    "EnvMode",
    "BaseMethod",
    "SendMessage",
    "SendCallback",
    "GetMe",
    "GetUpdates",
    "I18n",
    "InputMedia",
    "InputMediaBuffer",
    "UploadType",
]
