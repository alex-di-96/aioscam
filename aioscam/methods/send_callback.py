"""
SendCallback API method
"""

from typing import Any, Dict, Optional

from aioscam.enums import HttpMethod
from aioscam.methods.base import BaseMethod


class SendCallback(BaseMethod):
    """
    Send callback answer method

    Uses https://botapi.max.ru/answers as required by Max API
    """

    def __init__(
        self,
        callback_id: str,
        message: Optional[str] = None,
        notification: Optional[str] = None,
        format: Optional[str] = None,
        keyboard: Optional[Any] = None,
        parse_mode: Optional[Any] = None,
    ):
        # Use absolute URL to bypass base_url in AioScamClient
        super().__init__("https://botapi.max.ru/answers", method=HttpMethod.POST)
        self.callback_id = callback_id
        self.message = message
        self.notification = notification
        self.format = format
        self.keyboard = keyboard
        self.parse_mode = parse_mode

    @property
    def params(self) -> Optional[Dict[str, Any]]:
        return {"callback_id": self.callback_id}

    @property
    def body(self) -> Optional[Dict[str, Any]]:
        body: Dict[str, Any] = {}

        if self.message is not None:
            msg_body: Dict[str, Any] = {"text": self.message}
            if self.format:
                msg_body["format"] = self.format
            elif self.parse_mode:
                msg_body["format"] = self.parse_mode.value
            body["message"] = msg_body

        # Keyboard goes to TOP level of body (not inside message)
        if self.keyboard is not None:
            if hasattr(self.keyboard, 'to_dict'):
                body["keyboard"] = self.keyboard.to_dict()
            elif isinstance(self.keyboard, dict):
                body["keyboard"] = self.keyboard

        if self.notification is not None:
            body["notification"] = self.notification

        # Max API requires at least message or notification — send empty notification to dismiss
        if not body:
            body["notification"] = ""

        return body
