"""
Methods module - API method wrappers
"""

from aioscam.methods.base import BaseMethod
from aioscam.methods.send_message import SendMessage
from aioscam.methods.get_me import GetMe
from aioscam.methods.get_updates import GetUpdates

__all__ = [
    "BaseMethod",
    "SendMessage",
    "GetMe",
    "GetUpdates",
]
