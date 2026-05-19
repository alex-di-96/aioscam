"""
Button types enum
"""

from enum import Enum


class ButtonType(str, Enum):
    """Types of buttons in keyboards"""
    
    CALLBACK = "callback"
    LINK = "link"
    MESSAGE = "message"
    CHAT = "chat"
    CLIPBOARD = "clipboard"
    OPEN_APP = "open_app"
    REQUEST_CONTACT = "request_contact"
    REQUEST_GEO_LOCATION = "request_geo_location"
    ATTACHMENT = "attachment"
