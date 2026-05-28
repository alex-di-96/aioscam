"""
Parse mode enum
"""

from enum import Enum


class ParseMode(str, Enum):
    """Text parsing modes"""
    
    NONE = "none"
    MARKDOWN = "markdown"
    HTML = "html"
