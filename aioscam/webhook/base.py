"""
Base webhook handler
"""

from abc import ABC, abstractmethod
from typing import Any

from aioscam.bot import Bot
from aioscam.dispatcher import Dispatcher


class BaseWebhookHandler(ABC):
    """
    Base class for webhook handlers
    
    Subclasses should implement framework-specific webhook handling
    """
    
    def __init__(self, bot: Bot, dispatcher: Dispatcher, path: str = "/webhook"):
        self.bot = bot
        self.dispatcher = dispatcher
        self.path = path
    
    @abstractmethod
    async def handle_request(self, request_data: Any) -> Any:
        """
        Handle incoming webhook request
        
        Args:
            request_data: Framework-specific request object
        
        Returns:
            Framework-specific response object
        """
        ...
