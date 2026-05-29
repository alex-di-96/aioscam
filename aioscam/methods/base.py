"""
Base API method class
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

from aioscam.client.response import Response
from aioscam.enums import HttpMethod

if TYPE_CHECKING:
    from aioscam.bot import Bot


class BaseMethod(ABC):
    """
    Base class for API methods

    Provides a structured way to call API methods with
    proper separation of path, method, params, and body.

    Usage:
        method = SendMessage(chat_id=123, text="Hello!")
        result = await method.execute(bot)
    """

    def __init__(
        self,
        path: str,
        method: HttpMethod = HttpMethod.POST,
    ):
        self.path = path
        self.http_method = method

    @property
    @abstractmethod
    def params(self) -> Optional[Dict[str, Any]]:
        """Query parameters (for GET requests)"""
        ...

    @property
    @abstractmethod
    def body(self) -> Optional[Dict[str, Any]]:
        """Request body (for POST/PUT/PATCH requests)"""
        ...

    async def execute(self, bot: Bot) -> Any:
        """
        Execute API method

        Args:
            bot: Bot instance

        Returns:
            API response result
        """
        # For long polling (GET /updates with timeout param), aiohttp timeout
        # must exceed the server-side timeout to avoid race condition
        timeout = None
        if self.params and "timeout" in self.params:
            # Server-side timeout + 10 seconds buffer for network latency
            timeout = self.params["timeout"] + 10

        response = await bot.client.request(
            self.path,
            method=self.http_method,
            params=self.params,
            body=self.body if self.body else None,
            timeout=timeout,
        )
        return response.result
