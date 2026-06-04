"""
API paths for Max messenger
"""

from enum import Enum


class ApiPath(str, Enum):
    """Max API endpoint paths"""
    
    # Bot info
    GET_ME = "/me"
    GET_ME_FROM_CHAT = "/me"
    
    # Messages
    SEND_MESSAGE = "/messages"
    EDIT_MESSAGE = "/messages"
    DELETE_MESSAGE = "/messages"
    GET_MESSAGE = "/messages"
    GET_MESSAGES = "/messages"
    PIN_MESSAGE = "/pin"
    DELETE_PIN_MESSAGE = "/pin"
    GET_PINNED_MESSAGE = "/pin"
    
    # Callbacks
    SEND_CALLBACK = "/answers"
    
    # Actions — full path built dynamically: /chats/{chat_id}/actions
    ACTIONS = "/actions"
    
    # Chats
    GET_CHATS = "/chats"
    GET_CHAT_BY_ID = "/chats"
    GET_CHAT_BY_LINK = "/chats"
    EDIT_CHAT = "/chats"
    DELETE_CHAT = "/chats"
    ADD_MEMBERS_CHAT = "/members"
    REMOVE_MEMBER_CHAT = "/members"
    ADD_ADMIN_CHAT = "/admins"
    REMOVE_ADMIN = "/admins"
    GET_MEMBERS_CHAT = "/members"
    GET_LIST_ADMIN_CHAT = "/admins"
    DELETE_BOT_FROM_CHAT = "/members"
    CHANGE_INFO = "/chats"
    
    # Updates
    GET_UPDATES = "/updates"
    
    # Webhooks
    SUBSCRIBE_WEBHOOK = "/subscriptions"
    UNSUBSCRIBE_WEBHOOK = "/subscriptions"
    
    # Media
    GET_UPLOAD_URL = "/uploads"
    GET_VIDEO = "/videos"
    
    # Subscriptions
    GET_SUBSCRIPTIONS = "/subscriptions"
