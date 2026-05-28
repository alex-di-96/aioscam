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
    def payload(self) -> Optional[str]:
        """Get deep link payload (bot_started ?start= parameter)"""
        if hasattr(self.event, 'payload'):
            return self.event.payload
        if isinstance(self.event, dict):
            return self.event.get('payload')
        return None

    @property
    def user_id(self) -> Optional[int]:
        """Get user ID from event (convenience property)"""
        user = self.from_user
        if user is None:
            # Fallback: check event.user_id (for bot_started)
            if hasattr(self.event, 'user_id'):
                return self.event.user_id
            if isinstance(self.event, dict):
                return self.event.get('user_id')
            return None
        if hasattr(user, 'id') and user.id is not None:
            return user.id
        if hasattr(user, 'user_id') and user.user_id is not None:
            return user.user_id
        if isinstance(user, dict):
            return user.get('id') or user.get('user_id')
        return None

    @property
    def chat_id(self) -> Optional[int]:
        """Get chat ID from event (convenience property)"""
        chat = self.chat
        if chat is None:
            # Fallback: check event.chat_id (for bot_started/callback)
            if hasattr(self.event, 'chat_id'):
                return self.event.chat_id
            if isinstance(self.event, dict):
                return self.event.get('chat_id')
            return None
        if hasattr(chat, 'chat_id') and chat.chat_id is not None:
            return chat.chat_id
        if hasattr(chat, 'id') and chat.id is not None:
            return chat.id
        if isinstance(chat, dict):
            return chat.get('chat_id') or chat.get('id')
        return None

    @property
    def locale(self) -> Optional[str]:
        """
        Get user locale from event (IETF BCP 47, e.g. "ru", "en")

        Priority:
        1. data['locale'] (manually set via i18n or FSM)
        2. event.user_locale (from Max API update)
        """
        # Check if locale was manually set (e.g., via language selection)
        if self.data.get('locale'):
            return self.data['locale']
        # Get from Max API update
        if hasattr(self.event, 'user_locale'):
            return self.event.user_locale
        return None

    @property
    def callback(self) -> Optional[Any]:
        """Get callback data from event"""
        if hasattr(self.event, 'callback'):
            return self.event.callback
        return None

    @property
    def callback_id(self) -> Optional[str]:
        """Get callback ID from event (required for send_callback)"""
        cb = self.callback
        if cb is None:
            return None
        if isinstance(cb, dict):
            return cb.get('callback_id')
        if hasattr(cb, 'callback_id'):
            return cb.callback_id
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
        # Use properties that already handle all fallback cases (incl. bot_started)
        user_id = self.user_id
        chat_id = self.chat_id

        if not user_id or not chat_id:
            raise ValueError(f"Cannot determine chat/user ID: chat_id={chat_id}, user_id={user_id}")

        return await self.bot.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=text,
            **kwargs
        )

    async def answer_and_hide_keyboard(
        self,
        text: Optional[str] = None,
        keyboard: Optional[Any] = None,
    ) -> Any:
        """
        Answer callback and hide keyboard (one_time_keyboard behavior)

        Edits the message removing the keyboard, similar to Telegram's
        one_time_keyboard=True but for inline keyboards.

        Args:
            text: New text (keeps original if None)
            keyboard: New keyboard (None = remove keyboard)

        Returns:
            Edit result
        """
        # Get message_id from event
        message_id = None
        if self.message:
            msg = self.message
            if hasattr(msg, 'body') and msg.body:
                message_id = getattr(msg.body, 'mid', None)
            elif isinstance(msg, dict):
                message_id = msg.get('body', {}).get('mid')

        if not message_id:
            raise ValueError("Cannot determine message_id to edit")

        # Get original text if not provided
        if text is None:
            if self.message:
                msg = self.message
                if hasattr(msg, 'body') and msg.body:
                    text = getattr(msg.body, 'text', '')
                elif isinstance(msg, dict):
                    text = msg.get('body', {}).get('text', '')
            if not text:
                text = "✅"

        # Edit message without keyboard
        return await self.bot.edit_message(
            message_id=message_id,
            text=text,
            keyboard=keyboard,
        )

    async def hide_keyboard(self, text: Optional[str] = None) -> Any:
        """
        Hide inline keyboard from message (one_time_keyboard behavior)

        Like Telegram's one_time_keyboard=True — keyboard disappears after click.

        Args:
            text: New text (keeps original if None)

        Returns:
            Edit result
        """
        return await self.answer_and_hide_keyboard(text=text, keyboard=None)
