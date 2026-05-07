"""
Base API method class
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from aioscam.bot import Bot
from aioscam.client.response import Response


class BaseMethod(ABC):
    """
    Base class for API methods
    
    Provides a structured way to call API methods
    """
    
    def __init__(self, method_name: str):
        self.method_name = method_name
    
    @abstractmethod
    def build_request(self) -> Dict[str, Any]:
        """
        Build request body
        
        Returns:
            Request body dictionary
        """
        ...
    
    async def execute(self, bot: Bot) -> Any:
        """
        Execute API method
        
        Args:
            bot: Bot instance
        
        Returns:
            API response result
        """
        request_body = self.build_request()
        response = await bot.client.request(
            self.method_name,
            body=request_body,
        )
        return response.result
