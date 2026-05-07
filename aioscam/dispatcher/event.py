"""
Event context wrapper
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from aioscam.bot import Bot

if TYPE_CHECKING:
    from aioscam.types.keyboard import InlineKeyboard
    from aioscam.types.user import User
    from aioscam.types.chat import Chat
    from aioscam.types.message import Message


class EventContext:
    """
    Context wrapper for events

    Provides convenient access to event data and bot methods
    """

    def __init__(self, event: Any, bot: Bot, data: Optional[Dict[str, Any]] = None):
        self.event = event
        self.bot = bot
        self.data: Dict[str, Any] = data or {}
        self._state_data: Dict[str, Any] = {}

        # Don't modify incoming objects, use delegation instead
        self._message = getattr(event, 'message', None)

    @property
    def message(self) -> Optional[Message]:
        """Get message from event"""
        if hasattr(self.event, 'message'):
            return self.event.message
        return self._message

    @property
    def text(self) -> Optional[str]:
        """Get text from event"""
        if hasattr(self.event, 'text'):
            return self.event.text
        if self.message:
            msg = self.message
            if hasattr(msg, 'body') and msg.body:
                return getattr(msg.body, 'text', None)
            elif isinstance(msg, dict):
                return msg.get('body', {}).get('text')
        return None

    @property
    def chat(self) -> Optional[Chat]:
        """Get chat from event"""
        # Direct recipient attribute
        if hasattr(self.event, 'recipient'):
            return self.event.recipient
        # Via message.recipient
        if hasattr(self.event, 'message') and self.event.message:
            msg = self.event.message
            if hasattr(msg, 'recipient'):
                return msg.recipient
            elif isinstance(msg, dict):
                return msg.get('recipient')
        # For callback: event.message may be a dict with recipient
        if isinstance(self.event, dict):
            msg = self.event.get('message', {})
            if isinstance(msg, dict):
                return msg.get('recipient')
        return None

    @property
    def from_user(self) -> Optional[User]:
        """Get user from event"""
        # Direct sender attribute
        if hasattr(self.event, 'sender'):
            return self.event.sender
        # Via message.sender
        if hasattr(self.event, 'message') and self.event.message:
            msg = self.event.message
            if hasattr(msg, 'sender'):
                return msg.sender
            elif isinstance(msg, dict):
                return msg.get('sender')
        # For callback: event may have sender or callback.user
        if isinstance(self.event, dict):
            if 'sender' in self.event:
                return self.event['sender']
            # Check callback.user for callback events
            cb = self.event.get('callback', {})
            if isinstance(cb, dict) and 'user' in cb:
                return cb['user']
            msg = self.event.get('message', {})
            if isinstance(msg, dict):
                return msg.get('sender')
        return None

    @property
    def callback(self) -> Optional[Any]:
        """Get callback data from event"""
        if hasattr(self.event, 'callback'):
            return self.event.callback
        return None

    @property
    def callback_data(self) -> Optional[str]:
        """
        Get callback data string from button click.

        Handles both typed Callback objects (with .data attribute)
        and raw dict from API (with payload containing buttons).
        """
        cb = self.callback
        if cb is None:
            return None

        # Typed Callback object with .data attribute
        if hasattr(cb, 'data'):
            return cb.data

        # Dict from API
        if isinstance(cb, dict):
            # Could have 'data' key directly
            if 'data' in cb:
                return cb['data']
            # Or 'payload' with the button's callback_data
            if 'payload' in cb:
                payload = cb['payload']
                # If payload is a string, it's the callback data
                if isinstance(payload, str):
                    return payload
                # If payload is a dict with buttons, we need the clicked button's data
                if isinstance(payload, dict):
                    buttons = payload.get('buttons', [])
                    # Return the first button's payload (callback_data)
                    # In real API the clicked button's data is sent separately
                    clicked_payload = payload.get('payload') or payload.get('callback_data')
                    if clicked_payload:
                        return clicked_payload
                # payload could be a list of button rows
                if isinstance(payload, list):
                    for row in payload:
                        if isinstance(row, list):
                            for btn in row:
                                if isinstance(btn, dict) and 'payload' in btn:
                                    return btn['payload']

        # Fallback: try 'payload' attribute on object
        if hasattr(cb, 'payload'):
            return getattr(cb, 'payload', None)

        return None

    async def answer(self, text: str, **kwargs: Any) -> Any:
        """
        Answer to event message

        Args:
            text: Message text
            **kwargs: Additional send_message parameters

        Returns:
            Sent message
        """
        # Get recipient chat_id and sender user_id
        chat_id: Optional[int] = None
        user_id: Optional[int] = None

        if self.from_user:
            user = self.from_user
            if hasattr(user, 'user_id'):
                user_id = user.user_id
            elif isinstance(user, dict):
                user_id = user.get('user_id')

        if self.chat:
            chat = self.chat
            if hasattr(chat, 'chat_id'):
                chat_id = chat.chat_id
            elif isinstance(chat, dict):
                chat_id = chat.get('chat_id')

        if not user_id or not chat_id:
            raise ValueError(f"Cannot determine chat/user ID: chat_id={chat_id}, user_id={user_id}")

        return await self.bot.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=text,
            **kwargs
        )
