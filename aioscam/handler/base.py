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
        from aioscam.fsm.state import State as FsmState
        from aioscam.filters.builtin import StateFilter

        data: Dict = {}

        for f in self.filters:
            # Handle MagicFilter objects
            if isinstance(f, MagicFilter):
                try:
                    result = f.resolve(event)
                    if not result:
                        return None
                except Exception:
                    return None
            # Handle FSM State objects used directly as filters
            elif isinstance(f, FsmState):
                sf = StateFilter(f)
                result = await sf(event)
                if not result.passed:
                    return None
                data.update(result.data or {})
            # Handle regular BaseFilter objects
            elif isinstance(f, BaseFilter):
                result = await f(event)
                if not result.passed:
                    return None
                data.update(result.data or {})
            else:
                # Unknown filter type, skip it
                continue

        return data
