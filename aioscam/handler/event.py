"""
Generic event handler
"""

import inspect
from typing import Any, Callable, Dict, Optional

from aioscam.handler.base import BaseHandler


class EventHandler(BaseHandler):
    """
    Generic event handler for any event type
    
    Usage:
        @router.on_event("bot_started")
        async def on_bot_started(event):
            print("Bot started!")
    """
    
    def __init__(
        self,
        callback: Callable,
        event_type: Optional[str] = None,
        filters=None
    ):
        super().__init__(callback, filters)
        self.event_type = event_type
    
    async def handle(self, event: Any, data: Optional[Dict] = None) -> Any:
        """
        Handle event
        
        Args:
            event: Event object
            data: Filter data
        
        Returns:
            Handler result
        """
        if not self.callback:
            return None
        
        sig = inspect.signature(self.callback)
        params = list(sig.parameters.keys())
        
        kwargs = {}
        if 'event' in params:
            kwargs['event'] = event
        if 'data' in params and data:
            kwargs['data'] = data
        
        if data:
            for key, value in data.items():
                if key in params:
                    kwargs[key] = value
        
        if inspect.iscoroutinefunction(self.callback):
            return await self.callback(**kwargs)
        else:
            return self.callback(**kwargs)
