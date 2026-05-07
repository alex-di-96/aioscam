"""
SendMessage API method
"""

from typing import Any, Dict, Optional

from aioscam.methods.base import BaseMethod
from aioscam.enums import ApiPath, ParseMode


class SendMessage(BaseMethod):
    """
    Send message method
    
    Usage:
        method = SendMessage(chat_id=123, text="Hello!")
        result = await method.execute(bot)
    """
    
    def __init__(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[ParseMode] = None,
        reply_to_message_id: Optional[int] = None,
        keyboard: Optional[Dict] = None,
    ):
        super().__init__(ApiPath.SEND_MESSAGE.value)
        self.chat_id = chat_id
        self.text = text
        self.parse_mode = parse_mode
        self.reply_to_message_id = reply_to_message_id
        self.keyboard = keyboard
    
    def build_request(self) -> Dict[str, Any]:
        body = {
            "chat_id": self.chat_id,
            "text": self.text,
        }
        
        if self.parse_mode:
            body["parse_mode"] = self.parse_mode.value
        
        if self.reply_to_message_id:
            body["reply_to_message_id"] = self.reply_to_message_id
        
        if self.keyboard:
            body["keyboard"] = self.keyboard
        
        return body
