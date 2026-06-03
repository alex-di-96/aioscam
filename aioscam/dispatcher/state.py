"""
State context for FSM
"""

from typing import Any, Dict, Optional

from aioscam.fsm.state import State
from aioscam.fsm.storage import BaseStorage


class StateContext:
    """
    State context for handlers
    
    Provides convenient interface for FSM operations
    """
    
    def __init__(self, storage: BaseStorage, chat_id: Optional[int], user_id: Optional[int]):
        self._storage = storage
        self._chat_id = chat_id
        self._user_id = user_id
    
    async def get_state(self) -> Optional[str]:
        """Get current state"""
        if self._chat_id is None:
            return None
        return await self._storage.get_state(self._chat_id, self._user_id)

    async def set_state(self, state: Optional[Any]) -> None:
        """
        Set current state

        Args:
            state: State object or string or None to clear
        """
        if self._chat_id is None:
            return

        if isinstance(state, State):
            state = state.full_name

        await self._storage.set_state(self._chat_id, state, self._user_id)

    async def get_data(self) -> Dict[str, Any]:
        """Get stored data"""
        if self._chat_id is None:
            return {}
        return await self._storage.get_data(self._chat_id, self._user_id)

    async def set_data(self, data: Dict[str, Any]) -> None:
        """Set stored data"""
        if self._chat_id is None:
            return
        await self._storage.set_data(self._chat_id, data, self._user_id)

    async def update_data(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Update stored data"""
        if self._chat_id is None:
            return {}
        
        update_data = data or {}
        update_data.update(kwargs)
        return await self._storage.update_data(self._chat_id, update_data, self._user_id)
