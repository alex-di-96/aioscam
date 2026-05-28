"""
Base middleware class
"""

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseMiddleware(ABC):
    """
    Base class for all middleware
    
    Middleware wraps around handler execution
    
    Usage:
        class LoggingMiddleware(BaseMiddleware):
            async def __call__(self, event, handler):
                print(f"Received: {event}")
                result = await handler(event)
                print(f"Done: {result}")
                return result
    """
    
    @abstractmethod
    async def __call__(self, event: Any, handler: Callable) -> Any:
        """
        Process event through middleware
        
        Args:
            event: Event object
            handler: Next handler in chain
        
        Returns:
            Handler result
        """
        ...
