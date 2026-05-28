"""
Intent enum
"""

from enum import Enum


class Intent(str, Enum):
    """Message intents/purposes"""
    
    NONE = "none"
    SUPPORT = "support"
    FEEDBACK = "feedback"
    QUESTION = "question"
