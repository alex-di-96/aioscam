"""
Aiohttp webhook handler
"""

import logging
from typing import Optional

from aiohttp import web

from aioscam.bot import Bot
from aioscam.dispatcher import Dispatcher
from aioscam.types.update import Update
from aioscam.webhook.base import BaseWebhookHandler

logger = logging.getLogger(__name__)


class AiohttpWebhookHandler(BaseWebhookHandler):
    """
    Aiohttp-specific webhook handler with optional secret token validation.

    Usage (no auth):
        handler = AiohttpWebhookHandler(bot, dp)
        app = web.Application()
        app.router.add_post('/webhook', handler.handle)

    Usage (with secret token — recommended for production):
        handler = AiohttpWebhookHandler(bot, dp, secret_token="my_secret")
        # Max will send X-Max-Secret-Token: my_secret on each request
    """

    def __init__(
        self,
        bot: Bot,
        dispatcher: Dispatcher,
        path: str = "/webhook",
        secret_token: Optional[str] = None,
    ):
        super().__init__(bot, dispatcher, path)
        self._secret_token = secret_token

    async def handle_request(self, request: web.Request) -> web.Response:
        """
        Handle aiohttp webhook request.

        Validates X-Max-Secret-Token header when secret_token is set.

        Args:
            request: aiohttp Request

        Returns:
            aiohttp Response
        """
        # Validate secret token if configured
        if self._secret_token:
            incoming = request.headers.get("X-Max-Secret-Token", "")
            if incoming != self._secret_token:
                logger.warning(
                    "Webhook rejected: invalid or missing X-Max-Secret-Token "
                    f"(from {request.remote})"
                )
                return web.json_response(
                    {"ok": False, "error": "Unauthorized"}, status=401
                )

        try:
            data = await request.json()
            update = Update(**data)
            await self.dispatcher._process_update(self.bot, update)
            return web.json_response({"ok": True})
        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    async def handle(self, request: web.Request) -> web.Response:
        """Direct handler for aiohttp router"""
        return await self.handle_request(request)
