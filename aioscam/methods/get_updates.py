"""
GetUpdates API method
"""

from typing import Any, Dict, Optional

from aioscam.methods.base import BaseMethod
from aioscam.enums import ApiPath


class GetUpdates(BaseMethod):
    """
    Get updates method (for polling)
    
    Usage:
        method = GetUpdates(offset=123, limit=100, timeout=30)
        result = await method.execute(bot)
    """
    
    def __init__(
        self,
        offset: Optional[int] = None,
        limit: int = 100,
        timeout: int = 30,
    ):
        super().__init__(ApiPath.GET_UPDATES.value)
        self.offset = offset
        self.limit = limit
        self.timeout = timeout
    
    def build_request(self) -> Dict[str, Any]:
        body = {
            "limit": self.limit,
            "timeout": self.timeout,
        }
        
        if self.offset is not None:
            body["offset"] = self.offset
        
        return body
