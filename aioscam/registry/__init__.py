"""
Chat registry — bot-side replacement for the removed GET /chats listing
"""

from aioscam.registry.registry import ChatRegistry, REGISTRY_UPDATE_TYPES

__all__ = ["ChatRegistry", "REGISTRY_UPDATE_TYPES"]
