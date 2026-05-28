"""
Message handler
"""

import inspect
from typing import Any, Callable, Dict, List, Optional

from aioscam.handler.base import BaseHandler
from aioscam.filters.base import BaseFilter


class MessageHandler(BaseHandler):
    """
    Handler for message events
    
    Usage:
        @router.message_created(Command("start"))
        async def cmd_start(event):
            await event.message.answer("Hello!")
    """
    
    async def handle(self, event: Any, data: Optional[Dict] = None) -> Any:
        """
        Handle message event
        
        Args:
            event: Event object
            data: Filter data
        
        Returns:
            Handler result
        """
        if not self.callback:
            return None
        
        # Get callback signature
        sig = inspect.signature(self.callback)
        params = list(sig.parameters.keys())
        
        # Build kwargs for callback
        kwargs = {}
        if 'event' in params:
            kwargs['event'] = event
        if 'data' in params and data:
            kwargs['data'] = data
        
        # Add filter data as kwargs
        if data:
            for key, value in data.items():
                if key in params:
                    kwargs[key] = value
        
        # Call handler
        if inspect.iscoroutinefunction(self.callback):
            return await self.callback(**kwargs)
        else:
            return self.callback(**kwargs)
