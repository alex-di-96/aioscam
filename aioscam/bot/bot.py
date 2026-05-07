"""
Bot class for interacting with Max API
"""

import os
from typing import Any, Dict, List, Optional, Union

from aioscam.client import AioScamClient
from aioscam.client.response import Response
from aioscam.enums import (
    ApiPath,
    ChatPermission,
    ChatType,
    HttpMethod,
    ParseMode,
    SenderAction,
)
from aioscam.exceptions import BotTokenError


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
    ):
        """
        Initialize bot
        
        Args:
            token: Bot token (or from MAX_BOT_TOKEN env)
            base_url: Max API base URL
            timeout: Request timeout in seconds
            parse_mode: Default parse mode for messages
            client: Custom AioScamClient instance
        """
        self.token = token or os.getenv("MAX_BOT_TOKEN")
        if not self.token:
            raise BotTokenError(
                "Bot token is not provided. "
                "Pass it explicitly or set MAX_BOT_TOKEN environment variable."
            )
        
        self.parse_mode = parse_mode
        self._client = client or AioScamClient(
            token=self.token,
            base_url=base_url,
            timeout=timeout,
        )
        self._me: Optional[Dict[str, Any]] = None
    
    @property
    def client(self) -> AioScamClient:
        """Get underlying HTTP client"""
        return self._client
    
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
            response = await self._client.request(
                ApiPath.GET_ME.value,
                method=HttpMethod.GET,
            )
            self._me = response.result
        
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
        keyboard: Optional[Dict[str, Any]] = None,
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
            **kwargs: Additional parameters

        Returns:
            Sent message data
        """
        # Query params
        params: Dict[str, Any] = {}

        if chat_id is not None:
            params["chat_id"] = int(chat_id)

        if user_id is not None:
            params["user_id"] = user_id

        # Request body
        body: Dict[str, Any] = {
            "text": text,
            "attachments": [],
        }

        # Add inline keyboard to attachments if provided
        if keyboard:
            # Check if it's an InlineKeyboard dict (has 'type': 'inline_keyboard')
            if keyboard.get("type") == "inline_keyboard":
                body["attachments"].append(keyboard)
            else:
                # Assume it's a regular keyboard dict with 'buttons'
                body["attachments"].append({
                    "type": "inline_keyboard",
                    "payload": keyboard
                })

        if reply_to_mid:
            body["link"] = {"mid": reply_to_mid, "type": "reply"}

        # Merge other kwargs
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
        chat_id: Union[int, str],
        message_id: str,
        text: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        format: Optional[str] = None,
        keyboard: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Edit message

        Args:
            chat_id: Chat ID
            message_id: Message ID
            text: New text
            attachments: List of attachments
            format: Message format
            keyboard: New keyboard
            **kwargs: Additional parameters

        Returns:
            Edited message data
        """
        body: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        if text:
            body["text"] = text

        if attachments:
            body["attachments"] = attachments

        if format:
            body["format"] = format

        if keyboard:
            body["keyboard"] = keyboard

        body.update(kwargs)

        response = await self._client.request(
            ApiPath.EDIT_MESSAGE.value,
            body=body,
        )
        return response.result
    
    async def delete_message(
        self,
        chat_id: int,
        user_id: int,
        message_id: str,
    ) -> bool:
        """
        Delete message

        Args:
            chat_id: Chat ID
            user_id: User ID
            message_id: Message ID

        Returns:
            True if deleted
        """
        response = await self._client.request(
            ApiPath.DELETE_MESSAGE.value,
            method=HttpMethod.DELETE,
            params={
                "chat_id": chat_id,
                "user_id": user_id,
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
        message_id: str,
    ) -> bool:
        """
        Unpin message

        Args:
            message_id: Message ID

        Returns:
            True if unpinned
        """
        response = await self._client.request(
            ApiPath.DELETE_PIN_MESSAGE.value,
            body={
                "message_id": message_id,
            },
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
        answer: str,
        message_id: str,
        show_alert: bool = False,
    ) -> Dict[str, Any]:
        """
        Send callback answer

        Args:
            answer: Answer text
            message_id: Message ID
            show_alert: Show alert

        Returns:
            Callback response data
        """
        body: Dict[str, Any] = {
            "answer": answer,
            "message_id": message_id,
            "show_alert": show_alert,
        }

        response = await self._client.request(
            ApiPath.SEND_CALLBACK.value,
            body=body,
        )
        return response.result
    
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
        response = await self._client.request(
            ApiPath.SEND_ACTION.value,
            body={
                "chat_id": chat_id,
                "action": action.value,
            },
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
            params={},
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
    
    # ==================== Updates ====================
    
    async def get_updates(
        self,
        limit: int = 100,
        timeout: int = 30,
        marker: Optional[int] = None,
        types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get updates (for polling mode)

        Args:
            limit: Updates limit
            timeout: Long polling timeout
            marker: Last update marker
            types: Update types filter

        Returns:
            List of updates
        """
        params: Dict[str, Any] = {
            "limit": min(limit, 1000),
            "timeout": min(timeout, 90),
        }

        if marker is not None:
            params["marker"] = marker

        if types:
            params["types"] = types

        response = await self._client.request(
            ApiPath.GET_UPDATES.value,
            method=HttpMethod.GET,
            params=params,
        )

        # Response format: {"updates": [...], "marker": 123}
        result = response.result or {}
        if isinstance(result, dict):
            return result.get("updates", [])
        return result if isinstance(result, list) else []
    
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
    
    async def unsubscribe_webhook(self) -> bool:
        """
        Unsubscribe from webhook
        
        Returns:
            True if unsubscribed
        """
        response = await self._client.request(
            ApiPath.UNSUBSCRIBE_WEBHOOK.value,
            body={},
        )
        return response.ok
    
    async def delete_webhook(self) -> bool:
        """
        Delete webhook (alias for unsubscribe)
        
        Returns:
            True if deleted
        """
        return await self.unsubscribe_webhook()
    
    # ==================== Media ====================

    async def get_upload_url(self) -> str:
        """
        Get URL for file upload

        Returns:
            Upload URL
        """
        response = await self._client.request(
            ApiPath.GET_UPLOAD_URL.value,
            body={},
        )
        return response.result.get("url", "")

    async def upload_attachment(
        self,
        upload_type: str,
        file: Any,
    ) -> Dict[str, Any]:
        """
        Upload attachment file

        Args:
            upload_type: Upload type (e.g. 'photo', 'document', 'video')
            file: File object or path to upload

        Returns:
            Upload result with file info
        """
        response = await self._client.request(
            ApiPath.GET_UPLOAD_URL.value,
            body={
                "upload_type": upload_type,
                "file": file,
            },
        )
        return response.result

    async def get_video(self, video_token: str) -> Dict[str, Any]:
        """
        Get video file info

        Args:
            video_token: Video token

        Returns:
            Video file data
        """
        response = await self._client.request(
            ApiPath.GET_VIDEO.value,
            method=HttpMethod.GET,
            params={"video_token": video_token},
        )
        return response.result
    
    # ==================== Subscriptions ====================
    
    async def get_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Get webhook subscriptions
        
        Returns:
            List of subscriptions
        """
        response = await self._client.request(
            ApiPath.GET_SUBSCRIPTIONS.value,
            method=HttpMethod.GET,
            params={},
        )
        return response.result or []
