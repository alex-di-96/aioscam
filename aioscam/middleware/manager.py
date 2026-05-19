"""
Middleware manager
"""

from typing import Any, Callable, List

from aioscam.middleware.base import BaseMiddleware


class MiddlewareManager:
    """
    Manages middleware chain
    
    Executes middleware in order, wrapping around handler
    """
    
    def __init__(self):
        self.middlewares: List[BaseMiddleware] = []
    
    def add(self, middleware: BaseMiddleware) -> None:
        """
        Add middleware
        
        Args:
            middleware: Middleware instance
        """
        self.middlewares.append(middleware)
    
    async def execute(self, event: Any, handler: Callable) -> Any:
        """
        Execute handler through middleware chain
        
        Args:
            event: Event object
            handler: Handler to execute
        
        Returns:
            Handler result
        """
        if not self.middlewares:
            return await handler(event)
        
        # Build middleware chain
        def build_chain(index: int) -> Callable:
            if index >= len(self.middlewares):
                return handler
            else:
                next_handler = build_chain(index + 1)
                middleware = self.middlewares[index]
                
                async def chain(event):
                    return await middleware(event, next_handler)
                
                return chain
        
        chain = build_chain(0)
        return await chain(event)


class StateGuardMiddleware:
    """
    Blocks commands during active FSM state.
    Allows only /cancel and /start.
    Shows hint about expected input.
    """
    
    ALLOWED_COMMANDS = {'/cancel', '/start', '/commands'}
    
    def __init__(self, hints: dict = None):
        self.hints = hints or {}
    
    async def __call__(self, handler, event):
        text = getattr(event, 'text', '') or ''
        
        if not text.startswith('/'):
            return await handler(event)
        
        command = text.split()[0].lower()
        if command in self.ALLOWED_COMMANDS:
            return await handler(event)
        
        # Check if there's active FSM state
        event_data = getattr(event, 'data', {})
        state = event_data.get('state') if isinstance(event_data, dict) else None
        
        # Block command, send hint
        if state:
            current = await state.get_state()
            if current:
                hint = self.hints.get(current, "Введите ожидаемые данные")
                await event.answer(
                    f"⏳ Сейчас бот ждёт: {hint}\n\n"
                    f"Для отмены: /cancel\n"
                    f"Для перезапуска: /start"
                )
                return None  # Block handler
        
        return await handler(event)
