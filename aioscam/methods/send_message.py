"""
SendMessage API method
"""

from typing import Any, Dict, Optional

from aioscam.enums import ApiPath, HttpMethod, ParseMode
from aioscam.methods.base import BaseMethod


class SendMessage(BaseMethod):
    """
    Send message method

    Usage:
        method = SendMessage(chat_id=123, text="Hello!")
        result = await method.execute(bot)
    """

    def __init__(
        self,
        chat_id: Optional[int] = None,
        text: str = "",
        user_id: Optional[int] = None,
        parse_mode: Optional[ParseMode] = None,
        reply_to_mid: Optional[str] = None,
        keyboard: Optional[Dict] = None,
        format: Optional[str] = None,
        attachments: Optional[list] = None,
    ):
        super().__init__(ApiPath.SEND_MESSAGE.value, method=HttpMethod.POST)
        self.chat_id = chat_id
        self.text = text
        self.user_id = user_id
        self.parse_mode = parse_mode
        self.reply_to_mid = reply_to_mid
        self.keyboard = keyboard
        self.format = format
        self.attachments = attachments

    @property
    def params(self) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if self.chat_id is not None:
            params["chat_id"] = self.chat_id
        if self.user_id is not None:
            params["user_id"] = self.user_id
        return params if params else None

    @property
    def body(self) -> Optional[Dict[str, Any]]:
        body: Dict[str, Any] = {
            "text": self.text,
            "attachments": [],
        }

        if self.format:
            body["format"] = self.format
        elif self.parse_mode:
            body["format"] = self.parse_mode.value

        if self.keyboard:
            if self.keyboard.get("type") == "inline_keyboard":
                body["attachments"].append(self.keyboard)
            else:
                body["attachments"].append({
                    "type": "inline_keyboard",
                    "payload": self.keyboard,
                })

        if self.reply_to_mid:
            body["link"] = {"mid": self.reply_to_mid, "type": "reply"}

        if self.attachments:
            body["attachments"].extend(self.attachments)

        return body
