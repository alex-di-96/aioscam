"""
Storage base class for FSM
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseStorage(ABC):
    """
    Base class for FSM data storage
    
    Storage backends persist state data between events
    """
    
    @abstractmethod
    async def get_state(self, chat_id: int, user_id: Optional[int] = None) -> Optional[str]:
        """
        Get current state
        
        Args:
            chat_id: Chat ID
            user_id: User ID (optional)
        
        Returns:
            Current state or None
        """
        ...
    
    @abstractmethod
    async def set_state(self, chat_id: int, state: Optional[str], user_id: Optional[int] = None) -> None:
        """
        Set current state
        
        Args:
            chat_id: Chat ID
            state: State name
            user_id: User ID (optional)
        """
        ...
    
    @abstractmethod
    async def get_data(self, chat_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get stored data
        
        Args:
            chat_id: Chat ID
            user_id: User ID (optional)
        
        Returns:
            Stored data dictionary
        """
        ...
    
    @abstractmethod
    async def set_data(self, chat_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> None:
        """
        Set stored data
        
        Args:
            chat_id: Chat ID
            data: Data to store
            user_id: User ID (optional)
        """
        ...
    
    @abstractmethod
    async def update_data(
        self,
        chat_id: int,
        data: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update stored data (merge)
        
        Args:
            chat_id: Chat ID
            data: Data to merge
            user_id: User ID (optional)
        
        Returns:
            Updated data
        """
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close storage connection"""
        ...
