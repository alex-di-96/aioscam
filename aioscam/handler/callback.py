"""
Callback handler
"""

import inspect
from typing import Any, Callable, Dict, Optional

from aioscam.handler.base import BaseHandler


class CallbackHandler(BaseHandler):
    """
    Handler for callback events (button clicks)
    
    Usage:
        @router.callback_query(F.callback.data.startswith("action:"))
        async def handle_callback(event):
            await event.answer("Button clicked!")
    """
    
    async def handle(self, event: Any, data: Optional[Dict] = None) -> Any:
        """
        Handle callback event
        
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
