"""
In-memory storage for FSM
"""

from typing import Any, Dict, Optional

from aioscam.fsm.storage import BaseStorage


class MemoryStorage(BaseStorage):
    """
    In-memory storage for FSM data
    
    Data is lost when application restarts
    """
    
    def __init__(self):
        self._states: Dict[str, Optional[str]] = {}
        self._data: Dict[str, Dict[str, Any]] = {}
    
    def _get_key(self, chat_id: int, user_id: Optional[int] = None) -> str:
        """Generate storage key"""
        if user_id is not None:
            return f"{chat_id}:{user_id}"
        return f"{chat_id}"
    
    async def get_state(self, chat_id: int, user_id: Optional[int] = None) -> Optional[str]:
        """Get current state"""
        key = self._get_key(chat_id, user_id)
        return self._states.get(key)
    
    async def set_state(self, chat_id: int, state: Optional[str], user_id: Optional[int] = None) -> None:
        """Set current state"""
        key = self._get_key(chat_id, user_id)
        self._states[key] = state
    
    async def get_data(self, chat_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get stored data"""
        key = self._get_key(chat_id, user_id)
        return self._data.get(key, {})
    
    async def set_data(self, chat_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> None:
        """Set stored data"""
        key = self._get_key(chat_id, user_id)
        self._data[key] = data
    
    async def update_data(
        self,
        chat_id: int,
        data: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update stored data"""
        key = self._get_key(chat_id, user_id)
        current = self._data.get(key, {})
        current.update(data)
        self._data[key] = current
        return current
    
    async def close(self) -> None:
        """Close storage"""
        self._states.clear()
        self._data.clear()
