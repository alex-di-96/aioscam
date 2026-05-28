"""
Text style enum
"""

from enum import Enum


class TextStyle(str, Enum):
    """Text formatting styles"""
    
    NONE = "none"
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    CODE = "code"
    PRE = "pre"
    MENTION = "mention"
