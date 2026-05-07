"""
Router (Blueprint) for event handling
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from aioscam.handler.message import MessageHandler
from aioscam.handler.callback import CallbackHandler
from aioscam.handler.event import EventHandler
from aioscam.filters.base import BaseFilter
from aioscam.middleware.base import BaseMiddleware
from aioscam.middleware.manager import MiddlewareManager

logger = logging.getLogger(__name__)


class Router:
    """
    Router (Blueprint) for organizing handlers
    
    Routers can be nested and included in dispatcher
    
    Usage:
        router = Router()
        
        @router.message_created(Command("start"))
        async def cmd_start(event):
            await event.message.answer("Hello!")
    """
    
    def __init__(self, name: Optional[str] = None):
        self.name = name or f"Router#{id(self)}"
        self._message_handlers: List[MessageHandler] = []
        self._callback_handlers: List[CallbackHandler] = []
        self._event_handlers: Dict[str, List[EventHandler]] = {}
        self._middlewares: List[BaseMiddleware] = []
        self._middleware_manager = MiddlewareManager()
        self._parent: Optional['Router'] = None
        self._children: List['Router'] = []
    
    def include_router(self, router: 'Router') -> None:
        """
        Include another router into this one

        Args:
            router: Router to include
        
        Raises:
            ValueError: If circular inclusion detected
        """
        # Check for circular inclusion
        if self._is_child_of(router):
            raise ValueError(
                f"Circular router inclusion detected: "
                f"cannot include {router.name} into {self.name}"
            )
        
        router._parent = self
        self._children.append(router)
        logger.debug(f"Router {router.name} included into {self.name}")
    
    def _is_child_of(self, router: 'Router') -> bool:
        """Check if router is already an ancestor (prevents cycles)"""
        current = self._parent
        while current:
            if current == router:
                return True
            current = current._parent
        return False
    
    # ==================== Middleware ====================
    
    def add_middleware(self, middleware):
        """Add middleware instance directly (not decorator)"""
        self._middleware_manager.register(middleware)
    
    def middleware(self) -> Callable:
        """
        Decorator for middleware registration
        
        Usage:
            @router.middleware()
            async def logging_middleware(event, handler):
                return await handler(event)
        """
        def decorator(func: Callable) -> Callable:
            from aioscam.middleware.base import BaseMiddleware
            
            class FuncMiddleware(BaseMiddleware):
                async def __call__(self, event, handler):
                    return await func(event, handler)
            
            self._middlewares.append(FuncMiddleware())
            self._middleware_manager.add(FuncMiddleware())
            return func
        return decorator
    
    # ==================== Message Handlers ====================
    
    def message_created(self, *filters: BaseFilter) -> Callable:
        """
        Decorator for message created events
        
        Usage:
            @router.message_created(Command("start"))
            async def cmd_start(event):
                await event.message.answer("Hello!")
        """
        def decorator(func: Callable) -> Callable:
            handler = MessageHandler(func, list(filters))
            self._message_handlers.append(handler)
            logger.debug(f"Added message handler to {self.name}")
            return func
        return decorator
    
    def message_edited(self, *filters: BaseFilter) -> Callable:
        """
        Decorator for message edited events
        """
        def decorator(func: Callable) -> Callable:
            handler = MessageHandler(func, list(filters))
            # Store separately for event type routing
            if 'message_edited' not in self._event_handlers:
                self._event_handlers['message_edited'] = []
            self._event_handlers['message_edited'].append(
                EventHandler(func, 'message_edited', list(filters))
            )
            return func
        return decorator
    
    def message_removed(self, *filters: BaseFilter) -> Callable:
        """
        Decorator for message removed events
        """
        def decorator(func: Callable) -> Callable:
            if 'message_removed' not in self._event_handlers:
                self._event_handlers['message_removed'] = []
            self._event_handlers['message_removed'].append(
                EventHandler(func, 'message_removed', list(filters))
            )
            return func
        return decorator
    
    # ==================== Callback Handlers ====================
    
    def callback_query(self, *filters: BaseFilter) -> Callable:
        """
        Decorator for callback query events
        
        Usage:
            @router.callback_query(F.callback.data.startswith("action:"))
            async def handle_callback(event):
                await event.answer("Clicked!")
        """
        def decorator(func: Callable) -> Callable:
            handler = CallbackHandler(func, list(filters))
            self._callback_handlers.append(handler)
            logger.debug(f"Added callback handler to {self.name}")
            return func
        return decorator
    
    # ==================== Event Handlers ====================
    
    def on_event(self, event_type: str, *filters: BaseFilter) -> Callable:
        """
        Decorator for generic events
        
        Usage:
            @router.on_event("bot_started")
            async def on_bot_started(event):
        """
        def decorator(func: Callable) -> Callable:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            handler = EventHandler(func, event_type, list(filters))
            self._event_handlers[event_type].append(handler)
            logger.debug(f"Added event handler for {event_type} to {self.name}")
            return func
        return decorator
    
    def bot_started(self, *filters: BaseFilter) -> Callable:
        """Decorator for bot_started event"""
        return self.on_event('bot_started', *filters)
    
    def bot_stopped(self, *filters: BaseFilter) -> Callable:
        """Decorator for bot_stopped event"""
        return self.on_event('bot_stopped', *filters)
    
    # ==================== Event Processing ====================
    
    async def process_message(self, event, data: Optional[Dict] = None) -> Any:
        """
        Process message event
        
        Args:
            event: Event object
            data: Filter data
        
        Returns:
            Handler result
        """
        for handler in self._message_handlers:
            check_result = await handler.check(event)
            if check_result is not None:
                # Merge with provided data
                merged_data = {**(data or {}), **check_result}
                return await self._middleware_manager.execute(
                    event,
                    lambda e: handler.handle(e, merged_data)
                )
        
        # Try children routers
        for child in self._children:
            result = await child.process_message(event, data)
            if result is not None:
                return result
        
        return None
    
    async def process_callback(self, event, data: Optional[Dict] = None) -> Any:
        """
        Process callback event
        
        Args:
            event: Event object
            data: Filter data
        
        Returns:
            Handler result
        """
        for handler in self._callback_handlers:
            check_result = await handler.check(event)
            if check_result is not None:
                merged_data = {**(data or {}), **check_result}
                return await self._middleware_manager.execute(
                    event,
                    lambda e: handler.handle(e, merged_data)
                )
        
        for child in self._children:
            result = await child.process_callback(event, data)
            if result is not None:
                return result
        
        return None
    
    async def process_event(self, event_type: str, event, data: Optional[Dict] = None) -> Any:
        """
        Process generic event
        
        Args:
            event_type: Event type
            event: Event object
            data: Filter data
        
        Returns:
            Handler result
        """
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            check_result = await handler.check(event)
            if check_result is not None:
                merged_data = {**(data or {}), **check_result}
                return await self._middleware_manager.execute(
                    event,
                    lambda e: handler.handle(e, merged_data)
                )
        
        for child in self._children:
            result = await child.process_event(event_type, event, data)
            if result is not None:
                return result
        
        return None
