"""
Keyboard and button types
"""

from typing import List, Optional
from aioscam.types.base import MaxObject
from aioscam.enums import ButtonType


class Button(MaxObject):
    """
    Base button class
    
    Attributes:
        text: Button text
        type: Button type
    """
    
    text: str
    type: ButtonType
    
    def to_dict(self) -> dict:
        """Convert button to API dictionary"""
        result = {
            "text": self.text,
            "type": self.type.value if hasattr(self.type, 'value') else str(self.type),
        }
        
        # Add type-specific fields
        if hasattr(self, 'callback_data'):
            result["callback_data"] = self.callback_data
        if hasattr(self, 'url'):
            result["url"] = self.url
        if hasattr(self, 'chat_id'):
            result["chat_id"] = self.chat_id
        if hasattr(self, 'query'):
            result["query"] = self.query
        if hasattr(self, 'web_app') and self.web_app is not None:
            result["web_app"] = self.web_app
        if hasattr(self, 'contact_id') and self.contact_id is not None:
            result["contact_id"] = self.contact_id
        if hasattr(self, 'payload') and getattr(self, 'type', None) and \
                self.type == ButtonType.OPEN_APP and self.payload is not None:
            result["payload"] = self.payload
        
        return result


class CallbackButton(Button):
    """
    Callback button (triggers callback)
    
    Attributes:
        callback_data: Callback data
    """
    
    type: ButtonType = ButtonType.CALLBACK
    callback_data: str


class LinkButton(Button):
    """
    Link button (opens URL)
    
    Attributes:
        url: URL to open
    """
    
    type: ButtonType = ButtonType.LINK
    url: str


class ChatButton(Button):
    """
    Chat button (opens chat)
    
    Attributes:
        chat_id: Chat ID or username
    """
    
    type: ButtonType = ButtonType.CHAT
    chat_id: str


class MessageButton(Button):
    """
    Message button (switches to inline mode)
    
    Attributes:
        query: Inline query
    """
    
    type: ButtonType = ButtonType.MESSAGE
    query: str


class ClipboardButton(Button):
    """
    Clipboard button (copies text)

    Attributes:
        text: Button text
        payload: Text to copy to clipboard
    """

    type: ButtonType = ButtonType.CLIPBOARD
    text: str
    payload: str = ""


class OpenAppButton(Button):
    """
    Open app button — opens the bot's mini-app in Max WebView.

    Attributes:
        web_app: Bot username whose mini-app to open
        contact_id: Bot user_id whose mini-app to open
        payload: Optional data passed to the mini-app as start_param (max 512 chars)
    """

    type: ButtonType = ButtonType.OPEN_APP
    web_app: Optional[str] = None
    contact_id: Optional[int] = None
    payload: Optional[str] = None


class RequestContactButton(Button):
    """
    Request contact button
    """
    
    type: ButtonType = ButtonType.REQUEST_CONTACT


class RequestGeoLocationButton(Button):
    """
    Request geo location button
    """
    
    type: ButtonType = ButtonType.REQUEST_GEO_LOCATION


class Keyboard(MaxObject):
    """
    Base keyboard class
    
    Attributes:
        buttons: List of button rows
        one_time: Close keyboard after click
        resize: Resize keyboard
    """
    
    buttons: List[List[Button]] = []
    one_time: Optional[bool] = None
    resize: Optional[bool] = None
    
    def add_button(self, button: Button, row: int = 0) -> "Keyboard":
        """
        Add button to keyboard
        
        Args:
            button: Button to add
            row: Row index
        
        Returns:
            Self for chaining
        """
        while len(self.buttons) <= row:
            self.buttons.append([])
        self.buttons[row].append(button)
        return self
    
    def add_row(self, buttons: List[Button]) -> "Keyboard":
        """
        Add button row
        
        Args:
            buttons: List of buttons
        
        Returns:
            Self for chaining
        """
        self.buttons.append(buttons)
        return self
    
    def to_dict(self) -> dict:
        """Convert to API dictionary"""
        result = {
            "buttons": [
                [btn.to_dict() for btn in row]
                for row in self.buttons
            ]
        }
        
        if self.one_time is not None:
            result["one_time"] = self.one_time
        
        if self.resize is not None:
            result["resize"] = self.resize
        
        return result


class InlineKeyboard(MaxObject):
    """
    Inline keyboard (buttons in message)

    Uses 'attachments' format for Max API
    """

    buttons: List[List[Button]] = []

    def to_dict(self) -> dict:
        """Convert to API attachment format"""
        def serialize_button(btn: Button) -> dict:
            """Serialize button according to its type"""
            btn_type = btn.type.value if hasattr(btn.type, 'value') else str(btn.type)
            result = {
                "text": btn.text,
                "type": btn_type,
            }

            # Callback buttons need payload and intent
            if btn_type in ('callback',):
                result["payload"] = getattr(btn, 'callback_data', '')
                result["intent"] = getattr(btn, 'intent', 'default')

            # Link buttons need url
            if btn_type == 'link':
                result["url"] = getattr(btn, 'url', '')

            # Message buttons need query
            if btn_type == 'message':
                result["query"] = getattr(btn, 'query', '')

            # Open app buttons need web_app and contact_id
            if btn_type == 'open_app':
                result["web_app"] = getattr(btn, 'web_app', '')
                result["contact_id"] = getattr(btn, 'contact_id', 0)
                result["payload"] = getattr(btn, 'payload', '')

            # Chat buttons need chat_title and chat_description
            if btn_type == 'chat':
                result["chat_title"] = getattr(btn, 'chat_title', '')
                result["chat_description"] = getattr(btn, 'chat_description', '')

            # Clipboard buttons need payload
            if btn_type == 'clipboard':
                result["payload"] = getattr(btn, 'payload', '')

            # request_contact and request_geo_location don't need extra fields
            # (they work with just text and type)

            return result

        return {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [serialize_button(btn) for btn in row]
                    for row in self.buttons
                ]
            }
        }
