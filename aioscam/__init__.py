"""
AioScam - Async framework for Max messenger bots (aiogram-style)
"""

__version__ = "0.1.5.1"
__author__ = "AioScam Contributors"

from aioscam.bot import Bot
from aioscam.dispatcher import Dispatcher, Router
from aioscam.filters import Command, F, StateFilter
from aioscam.types.command import BotCommand
from aioscam.config import Config, get_config, EnvMode

__all__ = [
    "Bot",
    "Dispatcher",
    "Router",
    "Command",
    "BotCommand",
    "F",
    "StateFilter",
    "Config",
    "get_config",
    "EnvMode",
]
