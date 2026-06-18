"""
Bot class for interacting with Max API
"""

import os
from typing import Any, Dict, List, Optional, Union

import aiohttp

from aioscam.client import AioScamClient
from aioscam.client.response import Response
from aioscam.limiter import RateLimitConfig
from aioscam.methods.base import BaseMethod
from aioscam.methods import GetMe, SendMessage, GetUpdates, SendCallback
from aioscam.enums import (
    ApiPath,
    ChatPermission,
    ChatType,
    HttpMethod,
    ParseMode,
    SenderAction,
)
from aioscam.exceptions import BotTokenError
from aioscam.types.command import BotCommand

MAX_TEXT_LENGTH = 4000


class Bot:
    """
    Main bot class for interacting with Max API
    
    Usage:
        bot = Bot(token="your_token")
        # or from environment variable MAX_BOT_TOKEN
        bot = Bot()
        
        user = await bot.get_me()
        await bot.send_message(chat_id=123, text="Hello!")
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://platform-api.max.ru",
        timeout: int = 30,
        parse_mode: Optional[ParseMode] = None,
        client: Optional[AioScamClient] = None,
        rate_limit: Optional[RateLimitConfig] = None,
        auto_brand: bool = True,
        auto_telemetry: bool = True,
    ):
        """
        Initialize bot

        Args:
            token: Bot token (or from MAX_BOT_TOKEN env)
            base_url: Max API base URL
            timeout: Request timeout in seconds
            parse_mode: Default parse mode for messages
            client: Custom AioScamClient instance
            rate_limit: Rate limiter configuration (ignored if client is provided)
            auto_brand: Append "[Powered by AioScam vX.Y.Z]" to bot description
                        on startup. Pass False to opt out.
            auto_telemetry: Send a fire-and-forget anonymous usage ping
                            (version + bot_id) to the AioScam telemetry endpoint
                            on startup. Independent of auto_brand. Pass False to opt out.
        """
        self.token = token or os.getenv("MAX_BOT_TOKEN")
        if not self.token:
            raise BotTokenError(
                "Bot token is not provided. "
                "Pass it explicitly or set MAX_BOT_TOKEN environment variable."
            )

        self.parse_mode = parse_mode
        self.auto_brand = auto_brand
        self.auto_telemetry = auto_telemetry
        self._client = client or AioScamClient(
            token=self.token,
            base_url=base_url,
            timeout=timeout,
            rate_limit=rate_limit,
        )
        self._me: Optional[Dict[str, Any]] = None
    
    @property
    def client(self) -> AioScamClient:
        """Get underlying HTTP client"""
        return self._client

    async def execute(self, method: BaseMethod) -> Any:
        """
        Execute an API method object

        Args:
            method: BaseMethod instance (e.g. GetMe(), SendMessage(...))

        Returns:
            API response result
        """
        return await method.execute(self)

    async def close(self) -> None:
        """Close HTTP session"""
        await self._client.close()
    
    async def __aenter__(self) -> "Bot":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    # ==================== Bot Info ====================
    
    async def get_me(self) -> Dict[str, Any]:
        """
        Get bot information

        Returns:
            Dict with bot info
        """
        if self._me is None:
            self._me = await self.execute(GetMe())

        return self._me
    
    async def get_me_from_chat(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        """
        Get bot info in context of specific chat
        
        Args:
            chat_id: Chat ID or username
        
        Returns:
            Dict with bot info in chat
        """
        response = await self._client.request(
            ApiPath.GET_ME_FROM_CHAT.value,
            method=HttpMethod.GET,
            params={"chat_id": chat_id},
        )
        return response.result
    
    # ==================== Messages ====================
    
    async def send_message(
        self,
        chat_id: Optional[Union[int, str]] = None,
        text: str = "",
        user_id: Optional[int] = None,
        reply_to_mid: Optional[str] = None,
        keyboard: Optional[Any] = None,
        inline_keyboard: Optional[Any] = None,
        format: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        autosplit: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send text message

        Args:
            chat_id: Chat ID
            text: Message text
            user_id: User ID for private message
            reply_to_mid: Message ID to reply to
            keyboard: Inline keyboard (will be added to attachments)
            format: Text format — "markdown" or "html" (per official SDK)
            attachments: Extra attachment dicts (e.g. from process_input_media)
            autosplit: If True, split messages longer than 4000 chars into multiple
                       parts and place keyboard/attachments on the last part only.
                       If False (default), send text as-is (API may reject if >4000).
            **kwargs: Additional parameters

        Returns:
            Sent message data
        """
        # inline_keyboard= is an alias for keyboard=
        if inline_keyboard is not None and keyboard is None:
            keyboard = inline_keyboard

        # Normalize keyboard model to dict (InlineKeyboard/Keyboard have to_dict())
        if keyboard is not None and hasattr(keyboard, "to_dict"):
            keyboard = keyboard.to_dict()

        # autosplit=True: split long text into 4000-char chunks,
        # keyboard and attachments go to the last chunk only
        if autosplit and text and len(text) > MAX_TEXT_LENGTH:
            chunks = [text[i:i + MAX_TEXT_LENGTH] for i in range(0, len(text), MAX_TEXT_LENGTH)]
            result: Dict[str, Any] = {}
            for i, chunk in enumerate(chunks):
                is_last = i == len(chunks) - 1
                result = await self.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    user_id=user_id,
                    reply_to_mid=reply_to_mid if i == 0 else None,
                    keyboard=keyboard if is_last else None,
                    format=format,
                    attachments=attachments if is_last else None,
                    autosplit=False,  # chunks are already within limit
                    **(kwargs if is_last else {}),
                )
            return result

        # Use method object when no extra kwargs and no attachments
        if not kwargs and not attachments:
            return await self.execute(SendMessage(
                chat_id=int(chat_id) if chat_id is not None else None,
                text=text,
                user_id=user_id,
                parse_mode=self.parse_mode,
                reply_to_mid=reply_to_mid,
                keyboard=keyboard,
                format=format,
            ))

        # Fallback to direct request for extra kwargs
        params: Dict[str, Any] = {}
        if chat_id is not None:
            params["chat_id"] = int(chat_id)
        if user_id is not None:
            params["user_id"] = user_id

        body: Dict[str, Any] = {"text": text, "attachments": []}
        if format:
            body["format"] = format
        elif self.parse_mode:
            body["format"] = self.parse_mode.value

        if keyboard:
            if keyboard.get("type") == "inline_keyboard":
                body["attachments"].append(keyboard)
            else:
                body["attachments"].append({
                    "type": "inline_keyboard",
                    "payload": keyboard,
                })

        if reply_to_mid:
            body["link"] = {"mid": reply_to_mid, "type": "reply"}

        if attachments:
            body["attachments"].extend(attachments)

        for key, value in kwargs.items():
            if key == "attachments":
                body["attachments"].extend(value)
            else:
                body[key] = value

        response = await self._client.request(
            ApiPath.SEND_MESSAGE.value,
            method=HttpMethod.POST,
            params=params,
            body=body,
        )
        return response.result

    async def request_contact(
        self,
        chat_id: Union[int, str],
        text: str = "Please share your contact:",
        user_id: Optional[int] = None,
        button_text: str = "📱 Share Contact",
    ) -> Dict[str, Any]:
        """
        Send message with inline keyboard requesting contact

        Args:
            chat_id: Chat ID
            text: Message text
            user_id: User ID
            button_text: Text for the contact button

        Returns:
            Sent message data
        """
        from aioscam.utils.keyboard import KeyboardBuilder

        builder = KeyboardBuilder()
        builder.request_contact(button_text)
        kb = builder.build()

        return await self.send_message(
            chat_id=chat_id,
            text=text,
            user_id=user_id,
            keyboard=kb.to_dict(),
        )

    async def request_location(
        self,
        chat_id: Union[int, str],
        text: str = "Please share your location:",
        user_id: Optional[int] = None,
        button_text: str = "📍 Share Location",
    ) -> Dict[str, Any]:
        """
        Send message with inline keyboard requesting location

        Args:
            chat_id: Chat ID
            text: Message text
            user_id: User ID
            button_text: Text for the location button

        Returns:
            Sent message data
        """
        from aioscam.utils.keyboard import KeyboardBuilder

        builder = KeyboardBuilder()
        builder.request_location(button_text)
        kb = builder.build()

        return await self.send_message(
            chat_id=chat_id,
            text=text,
            user_id=user_id,
            keyboard=kb.to_dict(),
        )

    async def edit_message(
        self,
        message_id: str,
        chat_id: Optional[Union[int, str]] = None,
        text: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        format: Optional[str] = None,
        keyboard: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Edit message (matches official Python SDK: message_id in query params)

        Args:
            message_id: Message ID
            chat_id: Chat ID (optional)
            text: New text
            attachments: List of attachments
            format: Message format
            keyboard: New keyboard
            **kwargs: Additional parameters

        Returns:
            Edited message data
        """
        # message_id goes to query params (official SDK behavior)
        params: Dict[str, Any] = {"message_id": message_id}
        if chat_id is not None:
            params["chat_id"] = chat_id

        body: Dict[str, Any] = {"attachments": []}

        if text:
            if len(text) > MAX_TEXT_LENGTH:
                text = text[:MAX_TEXT_LENGTH - 1] + "…"
            body["text"] = text

        if attachments:
            body["attachments"] = attachments

        if format:
            body["format"] = format
        elif self.parse_mode:
            body["format"] = self.parse_mode.value

        # keyboard=None means "remove keyboard" (send empty inline_keyboard)
        # keyboard={} means "keep existing"
        # keyboard=dict means "set new keyboard"
        if keyboard is not None:
            if keyboard.get("type") == "inline_keyboard":
                body["attachments"].append(keyboard)
            else:
                body["attachments"].append({
                    "type": "inline_keyboard",
                    "payload": keyboard
                })

        body.update(kwargs)

        response = await self._client.request(
            ApiPath.EDIT_MESSAGE.value,
            method=HttpMethod.PUT,
            params=params,
            body=body if body else None,
        )
        return response.result
    
    async def delete_message(
        self,
        message_id: str,
    ) -> bool:
        """
        Delete message by ID (matches Go SDK signature)

        Args:
            message_id: Message ID to delete

        Returns:
            True if deleted
        """
        response = await self._client.request(
            ApiPath.DELETE_MESSAGE.value,
            method=HttpMethod.DELETE,
            params={
                "message_id": message_id,
            },
        )
        return response.ok
    
    async def get_message(
        self,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Get single message

        Args:
            message_id: Message ID

        Returns:
            Message data
        """
        response = await self._client.request(
            ApiPath.GET_MESSAGE.value,
            method=HttpMethod.GET,
            params={
                "message_id": message_id,
            },
        )
        return response.result
    
    async def get_messages(
        self,
        chat_id: Union[int, str],
        limit: int = 100,
        offset: int = 0,
        types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages from chat

        Args:
            chat_id: Chat ID
            limit: Messages limit
            offset: Offset
            types: Message types filter

        Returns:
            List of messages
        """
        params: Dict[str, Any] = {
            "chat_id": chat_id,
            "limit": limit,
            "offset": offset,
        }

        if types:
            params["types"] = types

        response = await self._client.request(
            ApiPath.GET_MESSAGES.value,
            method=HttpMethod.GET,
            params=params,
        )
        return response.result or []
    
    # ==================== Pin/Unpin ====================
    
    async def pin_message(
        self,
        chat_id: Union[int, str],
        message_id: str,
        notify: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Pin message in chat

        Args:
            chat_id: Chat ID
            message_id: Message ID
            notify: Send notification about pin

        Returns:
            Pinned message data
        """
        body: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        if notify is not None:
            body["notify"] = notify

        response = await self._client.request(
            ApiPath.PIN_MESSAGE.value,
            body=body,
        )
        return response.result
    
    async def delete_pin_message(
        self,
        chat_id: Union[int, str],
    ) -> bool:
        """
        Unpin message in chat (matches official Python SDK)

        Args:
            chat_id: Chat ID

        Returns:
            True if unpinned
        """
        response = await self._client.request(
            ApiPath.DELETE_PIN_MESSAGE.value,
            method=HttpMethod.DELETE,
            params={"chat_id": chat_id},
        )
        return response.ok
    
    async def get_pin_message(
        self,
        chat_id: Union[int, str],
    ) -> Optional[Dict[str, Any]]:
        """
        Get pinned message

        Args:
            chat_id: Chat ID

        Returns:
            Pinned message data or None
        """
        response = await self._client.request(
            ApiPath.GET_PINNED_MESSAGE.value,
            method=HttpMethod.GET,
            params={"chat_id": chat_id},
        )
        return response.result

    # Alias for backward compatibility
    get_pinned_message = get_pin_message
    
    # ==================== Callback ====================
    
    async def send_callback(
        self,
        callback_id: str,
        message: Optional[str] = None,
        notification: Optional[str] = None,
        format: Optional[str] = None,
        keyboard: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Send callback answer

        Matches official Max SDK (Python, Go, TypeScript):
        - URL: https://botapi.max.ru/answers
        - Auth: Authorization header (access_token query param deprecated by Max API)
        - Body: JSON {"message": NewMessageBody, "notification": string}

        Args:
            callback_id: Callback ID (required by Max API)
            message: Answer text (optional)
            notification: Notification popup text (optional)
            format: Text format — "markdown" or "html" (optional)
            keyboard: InlineKeyboard or dict (optional)

        Returns:
            Callback response data
        """
        return await self.execute(SendCallback(
            callback_id=callback_id,
            message=message,
            notification=notification,
            format=format,
            keyboard=keyboard,
            parse_mode=self.parse_mode,
        ))
    
    # ==================== Actions ====================
    
    async def send_action(
        self,
        chat_id: Union[int, str],
        action: SenderAction,
    ) -> Dict[str, Any]:
        """
        Send chat action (typing indicator)
        
        Args:
            chat_id: Chat ID
            action: Action type
        
        Returns:
            Action response data
        """
        # Path: /chats/{chat_id}/actions  (official Max SDK pattern)
        response = await self._client.request(
            f"{ApiPath.GET_CHATS.value}/{chat_id}{ApiPath.ACTIONS.value}",
            body={"action": action.value},
        )
        return response.result
    
    # ==================== Chats ====================
    
    async def get_chats(self) -> List[Dict[str, Any]]:
        """
        Get all chats where bot participates
        
        Returns:
            List of chats
        """
        response = await self._client.request(
            ApiPath.GET_CHATS.value,
            method=HttpMethod.GET,
        )
        return response.result or []
    
    async def get_chat_by_id(
        self,
        id: int,
    ) -> Dict[str, Any]:
        """
        Get chat by ID

        Args:
            id: Chat ID

        Returns:
            Chat data
        """
        response = await self._client.request(
            ApiPath.GET_CHAT_BY_ID.value,
            method=HttpMethod.GET,
            params={"id": id},
        )
        return response.result
    
    async def get_chat_by_link(
        self,
        link: str,
    ) -> Dict[str, Any]:
        """
        Get chat by invite link
        
        Args:
            link: Chat invite link
        
        Returns:
            Chat data
        """
        response = await self._client.request(
            ApiPath.GET_CHAT_BY_LINK.value,
            method=HttpMethod.GET,
            params={"link": link},
        )
        return response.result
    
    async def edit_chat(
        self,
        chat_id: Union[int, str],
        title: Optional[str] = None,
        description: Optional[str] = None,
        avatar: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Edit chat info

        Args:
            chat_id: Chat ID
            title: New title
            description: New description
            avatar: Avatar file path or URL
            **kwargs: Additional parameters

        Returns:
            Edited chat data
        """
        body: Dict[str, Any] = {"chat_id": chat_id}

        if title:
            body["title"] = title

        if description:
            body["description"] = description

        if avatar:
            body["avatar"] = avatar

        body.update(kwargs)

        response = await self._client.request(
            ApiPath.EDIT_CHAT.value,
            body=body,
        )
        return response.result
    
    async def delete_chat(
        self,
        chat_id: Union[int, str],
    ) -> bool:
        """
        Delete chat
        
        Args:
            chat_id: Chat ID
        
        Returns:
            True if deleted
        """
        response = await self._client.request(
            ApiPath.DELETE_CHAT.value,
            body={"chat_id": chat_id},
        )
        return response.ok
    
    # ==================== Chat Members ====================
    
    async def add_chat_members(
        self,
        chat_id: Union[int, str],
        user_ids: List[Union[int, str]],
    ) -> Dict[str, Any]:
        """
        Add members to chat

        Args:
            chat_id: Chat ID
            user_ids: List of user IDs

        Returns:
            Operation result
        """
        response = await self._client.request(
            ApiPath.ADD_MEMBERS_CHAT.value,
            body={
                "chat_id": chat_id,
                "user_ids": user_ids,
            },
        )
        return response.result

    # Alias for backward compatibility
    add_members_chat = add_chat_members
    
    async def remove_member_chat(
        self,
        chat_id: Union[int, str],
        user_id: Union[int, str],
    ) -> bool:
        """
        Remove member from chat

        Args:
            chat_id: Chat ID
            user_id: User ID

        Returns:
            True if removed
        """
        response = await self._client.request(
            ApiPath.REMOVE_MEMBER_CHAT.value,
            body={
                "chat_id": chat_id,
                "user_id": user_id,
            },
        )
        return response.ok

    # Alias matching official API name
    kick_chat_member = remove_member_chat
    
    async def add_list_admin_chat(
        self,
        chat_id: Union[int, str],
        user_id: Union[int, str],
        can_change_info: Optional[bool] = None,
        can_invite: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Add admin to chat

        Args:
            chat_id: Chat ID
            user_id: User ID
            can_change_info: Allow changing chat info
            can_invite: Allow inviting members
            **kwargs: Additional parameters

        Returns:
            Operation result
        """
        body: Dict[str, Any] = {
            "chat_id": chat_id,
            "user_id": user_id,
        }

        if can_change_info is not None:
            body["can_change_info"] = can_change_info

        if can_invite is not None:
            body["can_invite"] = can_invite

        body.update(kwargs)

        response = await self._client.request(
            ApiPath.ADD_ADMIN_CHAT.value,
            body=body,
        )
        return response.result

    # Alias for backward compatibility
    add_admin_chat = add_list_admin_chat
    
    async def remove_admin(
        self,
        chat_id: Union[int, str],
        user_id: Union[int, str],
    ) -> bool:
        """
        Remove admin from chat
        
        Args:
            chat_id: Chat ID
            user_id: User ID
        
        Returns:
            True if removed
        """
        response = await self._client.request(
            ApiPath.REMOVE_ADMIN.value,
            body={
                "chat_id": chat_id,
                "user_id": user_id,
            },
        )
        return response.ok
    
    async def get_chat_members(
        self,
        chat_id: Union[int, str],
        types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get chat members

        Args:
            chat_id: Chat ID
            types: Member types filter
            limit: Members limit
            offset: Offset

        Returns:
            List of members
        """
        params: Dict[str, Any] = {
            "chat_id": chat_id,
            "limit": limit,
            "offset": offset,
        }

        if types:
            params["types"] = types

        response = await self._client.request(
            ApiPath.GET_MEMBERS_CHAT.value,
            method=HttpMethod.GET,
            params=params,
        )
        return response.result or []

    # Alias for backward compatibility
    get_members_chat = get_chat_members

    async def get_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: Union[int, str],
    ) -> Dict[str, Any]:
        """
        Get chat member

        Args:
            chat_id: Chat ID
            user_id: User ID

        Returns:
            Member data
        """
        response = await self._client.request(
            ApiPath.GET_MEMBERS_CHAT.value,
            method=HttpMethod.GET,
            params={
                "chat_id": chat_id,
                "user_id": user_id,
            },
        )
        return response.result

    async def get_list_admin_chat(
        self,
        chat_id: Union[int, str],
    ) -> List[Dict[str, Any]]:
        """
        Get chat admins
        
        Args:
            chat_id: Chat ID
        
        Returns:
            List of admins
        """
        response = await self._client.request(
            ApiPath.GET_LIST_ADMIN_CHAT.value,
            method=HttpMethod.GET,
            params={"chat_id": chat_id},
        )
        return response.result or []
    
    async def delete_me_from_chat(
        self,
        chat_id: Union[int, str],
    ) -> bool:
        """
        Remove bot from chat

        Args:
            chat_id: Chat ID

        Returns:
            True if removed
        """
        response = await self._client.request(
            ApiPath.DELETE_BOT_FROM_CHAT.value,
            body={"chat_id": chat_id},
        )
        return response.ok

    # Alias for backward compatibility
    delete_bot_from_chat = delete_me_from_chat
    
    async def change_info(
        self,
        chat_id: Union[int, str],
        title: Optional[str] = None,
        description: Optional[str] = None,
        avatar: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Change chat info

        Args:
            chat_id: Chat ID
            title: New title
            description: New description
            avatar: Avatar file path or URL
            **kwargs: Additional parameters

        Returns:
            Updated chat data
        """
        body: Dict[str, Any] = {"chat_id": chat_id}

        if title:
            body["title"] = title

        if description:
            body["description"] = description

        if avatar:
            body["avatar"] = avatar

        body.update(kwargs)

        response = await self._client.request(
            ApiPath.CHANGE_INFO.value,
            body=body,
        )
        return response.result

    async def set_my_commands(
        self,
        commands: List["BotCommand"],
    ) -> Dict[str, Any]:
        """
        Register bot commands (shown in command menu / button)

        Args:
            commands: List of BotCommand objects.
                      Example: [BotCommand(name="start", description="Запуск бота")]
                      Pass empty list [] to remove all commands.

        Returns:
            Updated bot info
        """
        body = {"commands": [cmd if isinstance(cmd, dict) else cmd.to_dict() for cmd in commands]}
        response = await self._client.request(
            ApiPath.GET_ME.value,  # PATCH /me
            method=HttpMethod.PATCH,
            body=body,
        )
        return response.result
    
    async def set_bot_info(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Change bot name, description and/or username (shown in bot profile)

        Args:
            name: New bot display name (max 59 chars)
            description: New bot description (max 16000 chars)
            username: New bot @username (4-64 chars, must start with a letter)

        Returns:
            Updated bot info
        """
        body = {}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        if username:
            body["username"] = username
        if not body:
            return await self.get_me()
        response = await self._client.request(
            ApiPath.GET_ME.value,  # PATCH /me
            method=HttpMethod.PATCH,
            body=body,
        )
        return response.result

    async def _ensure_branding(self, force: bool = False) -> bool:
        """
        Append "[Powered by AioScam vX.Y.Z]" to bot description if absent or outdated.

        Reads current description via get_me(), checks for the tag, and patches only
        when the tag is missing or the version has changed.

        Args:
            force: Always update even if current version tag is present

        Returns:
            True if description was updated, False if already up-to-date
        """
        from aioscam import __version__

        tag = f"[Powered by AioScam v{__version__}]"
        tag_prefix = "[Powered by AioScam"

        me = await self.get_me()
        current_desc = me.get("description", "") or ""

        # Check if already branded with this exact version
        if not force and tag in current_desc:
            return False

        # Remove any old AioScam branding tag first
        lines = current_desc.split("\n")
        lines = [l for l in lines if not l.strip().startswith(tag_prefix)]
        base_desc = "\n".join(lines).rstrip()

        new_desc = f"{base_desc}\n\n{tag}".strip() if base_desc else tag

        await self.set_bot_info(description=new_desc)
        # Invalidate cached me so next get_me() reflects update
        self._me = None
        return True

    async def _remove_branding(self) -> bool:
        """
        Remove "[Powered by AioScam...]" tag from bot description.

        Useful for users who want to fully opt-out of branding.

        Returns:
            True if description was updated, False if no branding found
        """
        tag_prefix = "[Powered by AioScam"

        me = await self.get_me()
        current_desc = me.get("description", "") or ""

        # Check if any branding exists
        lines = current_desc.split("\n")
        clean_lines = [l for l in lines if not l.strip().startswith(tag_prefix)]

        if len(clean_lines) == len(lines):
            return False  # No branding found

        new_desc = "\n".join(clean_lines).rstrip()
        await self.set_bot_info(description=new_desc)
        self._me = None
        return True

    async def _send_telemetry(self, event: str) -> None:
        """
        Fire-and-forget anonymous usage ping to the AioScam telemetry endpoint.

        Sends only the framework version and bot_id. Failures, timeouts and
        connection errors are silently ignored — telemetry never affects bot
        operation. Controlled independently via `auto_telemetry`.
        """
        if not self.auto_telemetry:
            return

        from aioscam import __version__

        payload = {"event": event, "version": __version__}
        if self._me:
            payload["bot_id"] = self._me.get("user_id")

        try:
            session = await self._client._get_session()
            await session.post(
                "https://yasvc.ru/cgi-bin/botlog",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=False,
            )
        except Exception:
            pass  # telemetry must never affect bot operation

    # ==================== Updates ====================

    async def get_updates(
        self,
        limit: int = 100,
        timeout: int = 30,
        marker: Optional[int] = None,
        types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get updates (for polling mode)

        Args:
            limit: Updates limit
            timeout: Long polling timeout
            marker: Last update marker
            types: Update types filter

        Returns:
            Dict with "updates" (list) and "marker" (int)
        """
        result = await self.execute(GetUpdates(
            marker=marker,
            limit=limit,
            timeout=timeout,
            types=types,
        ))

        # Response format: {"updates": [...], "marker": 123}
        result = result or {}
        if isinstance(result, dict):
            return {"updates": result.get("updates", []), "marker": result.get("marker")}
        return {"updates": result if isinstance(result, list) else [], "marker": None}
    
    async def get_last_marker(self) -> Optional[int]:
        """
        Get last update marker
        
        Returns:
            Last marker value or None
        """
        params = {"limit": 1, "timeout": 0}
        response = await self._client.request(
            ApiPath.GET_UPDATES.value,
            method=HttpMethod.GET,
            params=params,
        )
        result = response.result or {}
        return result.get("marker") if isinstance(result, dict) else None
    
    # ==================== Webhooks ====================
    
    async def subscribe_webhook(
        self,
        url: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Subscribe to webhook
        
        Args:
            url: Webhook URL
            **kwargs: Additional parameters
        
        Returns:
            Subscription data
        """
        body: Dict[str, Any] = {"url": url}
        body.update(kwargs)
        
        response = await self._client.request(
            ApiPath.SUBSCRIBE_WEBHOOK.value,
            body=body,
        )
        return response.result
    
    async def unsubscribe_webhook(self, url: str) -> bool:
        """
        Unsubscribe from webhook

        Args:
            url: Webhook URL to unsubscribe (required by Max API)

        Returns:
            True if unsubscribed
        """
        response = await self._client.request(
            ApiPath.UNSUBSCRIBE_WEBHOOK.value,
            body={"url": url},
        )
        return response.ok
    
    def delete_webhook(self) -> None:
        """
        Deprecated: Use unsubscribe_webhook(url=...) instead.

        Max API requires url parameter for webhook deletion.
        This method is kept for backward compatibility but does nothing.
        """
        import warnings
        warnings.warn(
            "delete_webhook() is deprecated. "
            "Use unsubscribe_webhook(url=...) with explicit URL.",
            DeprecationWarning,
            stacklevel=2
        )
    
    # ==================== Media ====================

    async def get_upload_url(self, upload_type) -> Dict[str, Any]:
        """
        Get upload URL for a given media type.

        Args:
            upload_type: UploadType enum or string ("image", "video", "audio", "file")

        Returns:
            {"url": str, "token": str | None}
        """
        type_value = upload_type.value if hasattr(upload_type, "value") else str(upload_type)
        response = await self._client.request(
            ApiPath.GET_UPLOAD_URL.value,
            method=HttpMethod.POST,
            params={"type": type_value},
        )
        return response.result or {}

    async def download_file(self, path: str, url: str, token: str) -> int:
        """
        Download a media file from Max servers and save to disk.

        When you don't have a final filename yet, use make_temp_path() to get
        a unique datetime-stamped path:

            from aioscam import Bot
            path = Bot.make_temp_path(".jpg")          # "/tmp/aioscam_20260528_…jpg"
            status = await bot.download_file(path, url, token)

        Args:
            path: Local path to save the file
            url: Media URL (from attachment payload.url)
            token: Access token (from attachment payload.token)

        Returns:
            HTTP status code (200 = success)
        """
        return await self._client.download_file(path, url, token)

    async def download_file_bytes(self, url: str, token: str) -> Optional[bytes]:
        """
        Download a media file from Max servers into memory (no filesystem).

        Use this when you need to process the content immediately — resize,
        convert, analyse — without writing a temp file.  For large files or
        when persistence is needed, use download_file() instead.

        Example (in-memory processing):
            data = await bot.download_file_bytes(url, token)
            if data:
                # pass `data` to PIL, ffmpeg, etc.
                processed = my_transform(data)
                await bot.send_photo(chat_id, user_id, photo=processed)

        Example (temp-file fallback):
            path = Bot.make_temp_path(".jpg")
            await bot.download_file(path, url, token)

        Args:
            url: Media URL (from attachment payload.url)
            token: Access token (from attachment payload.token)

        Returns:
            File content as bytes, or None if download failed
        """
        return await self._client.download_file_bytes(url, token)

    @staticmethod
    def make_temp_path(ext: str = "", directory: str = "/tmp") -> str:
        """
        Generate a unique temp file path using datetime with microsecond precision.

        Args:
            ext: File extension including dot, e.g. ".jpg"
            directory: Target directory (default /tmp)

        Returns:
            Path string like "/tmp/aioscam_20260528_153042_847291.jpg"
        """
        from aioscam.client.client import AioScamClient
        return AioScamClient.make_temp_path(ext, directory)

    async def _send_with_media(
        self,
        attachment_dict: Dict[str, Any],
        chat_id=None,
        user_id=None,
        text: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a message with a pre-uploaded attachment dict.
        Handles attachment.not.ready retry (up to 5 attempts, 2s delay).
        """
        import asyncio
        from aioscam.exceptions import ApiError

        await asyncio.sleep(2)  # give Max servers time to process

        last_exc = None
        for attempt in range(5):
            try:
                return await self.send_message(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=text,
                    attachments=[attachment_dict],
                    **kwargs,
                )
            except (ApiError, Exception) as e:
                last_exc = e
                if "not.ready" in str(e).lower() or "attachment" in str(e).lower():
                    if attempt < 4:
                        await asyncio.sleep(2)
                        continue
                raise
        raise last_exc

    async def send_photo(
        self,
        chat_id=None,
        user_id=None,
        photo=None,
        caption: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Upload and send an image.

        Args:
            chat_id: Chat ID
            user_id: User ID (for private)
            photo: Path string, bytes, InputMedia, or InputMediaBuffer
            caption: Optional text caption

        Returns:
            Sent message data
        """
        from aioscam.types.attachment import InputMedia, InputMediaBuffer, UploadType
        from aioscam.utils.media import process_input_media

        if isinstance(photo, str):
            media = InputMedia(photo, UploadType.IMAGE)
        elif isinstance(photo, bytes):
            media = InputMediaBuffer(photo, "photo.jpg", UploadType.IMAGE)
        else:
            media = photo

        att = await process_input_media(self, media)
        return await self._send_with_media(att, chat_id=chat_id, user_id=user_id, text=caption, **kwargs)

    async def send_document(
        self,
        chat_id=None,
        user_id=None,
        document=None,
        caption: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Upload and send a file/document.

        Args:
            chat_id: Chat ID
            user_id: User ID (for private)
            document: Path string, bytes, InputMedia, or InputMediaBuffer
            caption: Optional text caption

        Returns:
            Sent message data
        """
        from aioscam.types.attachment import InputMedia, InputMediaBuffer, UploadType
        from aioscam.utils.media import process_input_media

        if isinstance(document, str):
            media = InputMedia(document, UploadType.FILE)
        elif isinstance(document, bytes):
            media = InputMediaBuffer(document, "document.bin", UploadType.FILE)
        else:
            media = document

        att = await process_input_media(self, media)
        return await self._send_with_media(att, chat_id=chat_id, user_id=user_id, text=caption, **kwargs)

    async def send_audio(
        self,
        chat_id=None,
        user_id=None,
        audio=None,
        caption: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Upload and send an audio file.

        Args:
            chat_id: Chat ID
            user_id: User ID (for private)
            audio: Path string, bytes, InputMedia, or InputMediaBuffer
            caption: Optional text caption

        Returns:
            Sent message data
        """
        from aioscam.types.attachment import InputMedia, InputMediaBuffer, UploadType
        from aioscam.utils.media import process_input_media

        if isinstance(audio, str):
            media = InputMedia(audio, UploadType.AUDIO)
        elif isinstance(audio, bytes):
            media = InputMediaBuffer(audio, "audio.mp3", UploadType.AUDIO)
        else:
            media = audio

        att = await process_input_media(self, media)
        return await self._send_with_media(att, chat_id=chat_id, user_id=user_id, text=caption, **kwargs)

    async def send_video(
        self,
        chat_id=None,
        user_id=None,
        video=None,
        caption: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Upload and send a video file.

        Args:
            chat_id: Chat ID
            user_id: User ID (for private)
            video: Path string, bytes, InputMedia, or InputMediaBuffer
            caption: Optional text caption

        Returns:
            Sent message data
        """
        from aioscam.types.attachment import InputMedia, InputMediaBuffer, UploadType
        from aioscam.utils.media import process_input_media

        if isinstance(video, str):
            media = InputMedia(video, UploadType.VIDEO)
        elif isinstance(video, bytes):
            media = InputMediaBuffer(video, "video.mp4", UploadType.VIDEO)
        else:
            media = video

        att = await process_input_media(self, media)
        return await self._send_with_media(att, chat_id=chat_id, user_id=user_id, text=caption, **kwargs)

    async def send_media(
        self,
        chat_id=None,
        user_id=None,
        media=None,
        caption: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Upload and send any media file — type is auto-detected.

        Args:
            chat_id: Chat ID
            user_id: User ID (for private)
            media: Path string, bytes, InputMedia, or InputMediaBuffer
            caption: Optional text caption

        Returns:
            Sent message data
        """
        from aioscam.types.attachment import InputMedia, InputMediaBuffer
        from aioscam.utils.media import process_input_media

        if isinstance(media, str):
            media_obj = InputMedia(media)
        elif isinstance(media, bytes):
            media_obj = InputMediaBuffer(media, "media")
        else:
            media_obj = media

        att = await process_input_media(self, media_obj)
        return await self._send_with_media(att, chat_id=chat_id, user_id=user_id, text=caption, **kwargs)

    async def get_video(self, video_token: str) -> Dict[str, Any]:
        """
        Get video file info by token.

        Args:
            video_token: Video token

        Returns:
            Video data with URLs for different resolutions
        """
        response = await self._client.request(
            ApiPath.GET_VIDEO.value,
            method=HttpMethod.GET,
            params={"video_token": video_token},
        )
        return response.result
    
    # ==================== Subscriptions ====================
    
    async def get_subscriptions(self) -> list:
        """
        Get webhook subscriptions

        Returns:
            List of subscription URLs
        """
        response = await self._client.request(
            ApiPath.GET_SUBSCRIPTIONS.value,
            method=HttpMethod.GET,
        )
        # API returns: {"subscriptions": ["url1", "url2", ...]}
        result = response.result or {}
        if isinstance(result, dict):
            return result.get("subscriptions", [])
        return result if isinstance(result, list) else []
