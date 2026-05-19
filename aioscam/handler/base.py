"""
Base handler class
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from aioscam.filters.base import BaseFilter


class BaseHandler(ABC):
    """
    Base class for all event handlers
    
    Handlers process events that pass filters
    """
    
    def __init__(self, callback: Callable, filters: Optional[List[BaseFilter]] = None):
        self.callback = callback
        self.filters = filters or []
    
    @abstractmethod
    async def handle(self, event: Any, data: Optional[Dict] = None) -> Any:
        """
        Handle event
        
        Args:
            event: Event object
            data: Filter data
        
        Returns:
            Handler result
        """
        ...
    
    async def check(self, event: Any) -> Optional[Dict]:
        """
        Check if event passes all filters
        
        Args:
            event: Event object
        
        Returns:
            Filter data if passed, None otherwise
        """
        from magic_filter import MagicFilter
        
        for f in self.filters:
            # Handle MagicFilter objects
            if isinstance(f, MagicFilter):
                try:
                    # MagicFilter.resolve() returns the result or raises exception
                    result = f.resolve(event)
                    # If result is falsy, filter didn't pass
                    if not result:
                        return None
                except Exception:
                    # If resolve raises exception, filter doesn't pass
                    return None
            # Handle regular BaseFilter objects
            elif isinstance(f, BaseFilter):
                result = await f(event)
                if not result.passed:
                    return None
            else:
                # Unknown filter type, skip it
                continue
        
        return {}
