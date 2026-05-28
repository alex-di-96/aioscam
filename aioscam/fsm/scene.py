"""
Scene (wizard) for FSM
"""

from typing import Any, Callable, Dict, List, Optional

from aioscam.fsm.state import State


class Scene:
    """
    Scene (wizard) for multi-step conversations
    
    Usage:
        class RegistrationScene(Scene):
            async def start(self):
                await self.event.message.answer("Введите имя:")
            
            @Scene.handler()
            async def get_name(self, event):
                await self.update_data(name=event.message.text)
                await self.next()
                await event.message.answer("Введите возраст:")
    """
    
    def __init__(self, name: str):
        self.name = name
        self.handlers: List[Callable] = []
        self.event = None
        self._data = {}
    
    def handler(self, state: Optional[State] = None):
        """
        Decorator for scene step handlers
        
        Args:
            state: State to handle
        """
        def decorator(func: Callable) -> Callable:
            self.handlers.append(func)
            return func
        return decorator
    
    async def start(self, event, data: Optional[Dict] = None) -> None:
        """
        Start scene
        
        Args:
            event: Event object
            data: Initial data
        """
        self.event = event
        self._data = data or {}
    
    async def next(self) -> None:
        """Go to next step"""
        # Implementation will be in dispatcher
        pass
    
    async def update_data(self, **kwargs) -> None:
        """Update scene data"""
        self._data.update(kwargs)
    
    def get_data(self) -> Dict[str, Any]:
        """Get scene data"""
        return self._data.copy()
