"""
Keyboard builder utility
"""

from typing import List
from aioscam.types.keyboard import (
    Keyboard,
    InlineKeyboard,
    CallbackButton,
    LinkButton,
    ChatButton,
    MessageButton,
    ClipboardButton,
    OpenAppButton,
    RequestContactButton,
    RequestGeoLocationButton,
)


class KeyboardBuilder:
    """
    Utility for building keyboards
    
    Usage:
        builder = KeyboardBuilder()
        builder.callback("Click me", "action:1")
        builder.link("Open site", "https://example.com")
        keyboard = builder.build()
    """
    
    def __init__(self, inline: bool = False):
        self.inline = inline
        self.buttons: List[List] = []
        self._current_row: List = []
    
    def callback(self, text: str, callback_data: str) -> "KeyboardBuilder":
        """
        Add callback button
        
        Args:
            text: Button text
            callback_data: Callback data
        
        Returns:
            Self for chaining
        """
        btn = CallbackButton(text=text, callback_data=callback_data)
        self._current_row.append(btn)
        return self
    
    def link(self, text: str, url: str) -> "KeyboardBuilder":
        """
        Add link button
        
        Args:
            text: Button text
            url: URL to open
        
        Returns:
            Self for chaining
        """
        btn = LinkButton(text=text, url=url)
        self._current_row.append(btn)
        return self
    
    def chat(self, text: str, chat_id: str) -> "KeyboardBuilder":
        """
        Add chat button
        
        Args:
            text: Button text
            chat_id: Chat ID or username
        
        Returns:
            Self for chaining
        """
        btn = ChatButton(text=text, chat_id=chat_id)
        self._current_row.append(btn)
        return self
    
    def switch(self, text: str, query: str) -> "KeyboardBuilder":
        """
        Add switch to inline button
        
        Args:
            text: Button text
            query: Inline query
        
        Returns:
            Self for chaining
        """
        btn = MessageButton(text=text, query=query)
        self._current_row.append(btn)
        return self
    
    def clipboard(self, text: str, copy_text: str) -> "KeyboardBuilder":
        """
        Add clipboard button
        
        Args:
            text: Button text
            copy_text: Text to copy
        
        Returns:
            Self for chaining
        """
        btn = ClipboardButton(text=text)
        self._current_row.append(btn)
        return self
    
    def open_app(self, text: str, app_id: str) -> "KeyboardBuilder":
        """
        Add open app button
        
        Args:
            text: Button text
            app_id: App ID
        
        Returns:
            Self for chaining
        """
        btn = OpenAppButton(text=text, app_id=app_id)
        self._current_row.append(btn)
        return self
    
    def request_contact(self, text: str = "Share Contact") -> "KeyboardBuilder":
        """
        Add request contact button
        
        Args:
            text: Button text
        
        Returns:
            Self for chaining
        """
        btn = RequestContactButton(text=text)
        self._current_row.append(btn)
        return self
    
    def request_location(self, text: str = "Share Location") -> "KeyboardBuilder":
        """
        Add request geo location button
        
        Args:
            text: Button text
        
        Returns:
            Self for chaining
        """
        btn = RequestGeoLocationButton(text=text)
        self._current_row.append(btn)
        return self
    
    def row(self) -> "KeyboardBuilder":
        """
        Start new row
        
        Returns:
            Self for chaining
        """
        if self._current_row:
            self.buttons.append(self._current_row.copy())
            self._current_row.clear()
        return self
    
    def build(self, one_time: bool = False, resize: bool = False):
        """
        Build keyboard

        Args:
            one_time: Close after click (for regular keyboards)
            resize: Resize keyboard (for regular keyboards)

        Returns:
            Keyboard or InlineKeyboard
        """
        if self._current_row:
            self.buttons.append(self._current_row.copy())

        if self.inline:
            keyboard = InlineKeyboard(buttons=self.buttons.copy())
        else:
            keyboard = Keyboard(buttons=self.buttons.copy())
            keyboard.one_time = one_time
            keyboard.resize = resize

        return keyboard

    def reset(self) -> None:
        """Reset builder"""
        self.buttons.clear()
        self._current_row.clear()
