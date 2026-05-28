"""
AioScam - Async framework for Max messenger bots (aiogram-style)
"""

__version__ = "0.1.6.2"
__author__ = "AioScam Contributors"

from aioscam.bot import Bot
from aioscam.dispatcher import Dispatcher, Router
from aioscam.filters import Command, StartCommand, F, StateFilter
from aioscam.types.command import BotCommand
from aioscam.config import Config, get_config, EnvMode
from aioscam.methods import BaseMethod, SendMessage, GetMe, GetUpdates

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
    "GetMe",
    "GetUpdates",
]
