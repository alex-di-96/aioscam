"""
GetMe API method
"""

from typing import Any, Dict

from aioscam.methods.base import BaseMethod
from aioscam.enums import ApiPath


class GetMe(BaseMethod):
    """
    Get bot info method
    
    Usage:
        method = GetMe()
        result = await method.execute(bot)
    """
    
    def __init__(self):
        super().__init__(ApiPath.GET_ME.value)
    
    def build_request(self) -> Dict[str, Any]:
        return {}
