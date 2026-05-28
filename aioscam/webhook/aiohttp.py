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
    Aiohttp-specific webhook handler
    
    Usage:
        handler = AiohttpWebhookHandler(bot, dp)
        app = web.Application()
        app.router.add_post('/webhook', handler.handle)
    """
    
    async def handle_request(self, request: web.Request) -> web.Response:
        """
        Handle aiohttp webhook request
        
        Args:
            request: aiohttp Request
        
        Returns:
            aiohttp Response
        """
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
