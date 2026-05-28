"""
GetUpdates API method
"""

from typing import Any, Dict, List, Optional

from aioscam.enums import ApiPath, HttpMethod
from aioscam.methods.base import BaseMethod


class GetUpdates(BaseMethod):
    """
    Get updates method (for polling)

    Usage:
        method = GetUpdates(marker=123, limit=100, timeout=30)
        result = await method.execute(bot)
    """

    def __init__(
        self,
        marker: Optional[int] = None,
        limit: int = 100,
        timeout: int = 30,
        types: Optional[List[str]] = None,
    ):
        super().__init__(ApiPath.GET_UPDATES.value, method=HttpMethod.GET)
        self.marker = marker
        self.limit = limit
        self.timeout = timeout
        self.types = types

    @property
    def params(self) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "limit": min(self.limit, 1000),
            "timeout": min(self.timeout, 90),
        }

        if self.marker is not None:
            params["marker"] = self.marker

        if self.types:
            params["types"] = self.types

        return params

    @property
    def body(self) -> Optional[Dict[str, Any]]:
        return None
