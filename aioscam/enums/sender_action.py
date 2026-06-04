"""
Sender action enum
"""

from enum import Enum


class SenderAction(str, Enum):
    """
    Typing/activity indicators shown to the chat recipient.

    Values match the official Max API (max-sdk/py/maxapi/enums/sender_action.py).
    """

    TYPING_ON     = "typing_on"
    SENDING_PHOTO = "sending_photo"
    SENDING_VIDEO = "sending_video"
    SENDING_AUDIO = "sending_audio"
    SENDING_FILE  = "sending_file"
    MARK_SEEN     = "mark_seen"
