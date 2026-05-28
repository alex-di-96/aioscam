"""
Filters module
"""

from aioscam.filters.base import BaseFilter, FilterResult
from aioscam.filters.builtin import (
    Command,
    StartCommand,
    Text,
    ContentType,
    ChatType,
    State,
    StateFilter,
    AllFilter,
)
from magic_filter import F

__all__ = [
    "BaseFilter",
    "FilterResult",
    "Command",
    "StartCommand",
    "Text",
    "ContentType",
    "ChatType",
    "State",
    "StateFilter",
    "AllFilter",
    "F",
]
