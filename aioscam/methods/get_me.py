"""
GetMe API method
"""

from typing import Any, Dict, Optional

from aioscam.enums import ApiPath, HttpMethod
from aioscam.methods.base import BaseMethod


class GetMe(BaseMethod):
    """
    Get bot info method

    Usage:
        method = GetMe()
        result = await method.execute(bot)
    """

    def __init__(self):
        super().__init__(ApiPath.GET_ME.value, method=HttpMethod.GET)

    @property
    def params(self) -> Optional[Dict[str, Any]]:
        return None

    @property
    def body(self) -> Optional[Dict[str, Any]]:
        return None
