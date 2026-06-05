"""
Main Dispatcher
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Dict, List, Optional

from aioscam.bot import Bot
from aioscam.dispatcher.router import Router
from aioscam.dispatcher.event import EventContext
from aioscam.dispatcher.state import StateContext
from aioscam.types.update import Update
from aioscam.fsm.memory import MemoryStorage
from aioscam.fsm.storage import BaseStorage
from aioscam.exceptions import DispatcherError

logger = logging.getLogger(__name__)


class Dispatcher(Router):
    """
    Main dispatcher for bot
    
    Dispatcher is the root router that manages event processing
    
    Usage:
        dp = Dispatcher()
        
        @dp.message_created(Command("start"))
        async def cmd_start(event):
            await event.message.answer("Hello!")
        
        await dp.start_polling(bot)
    """
    
    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        state_guard_commands: Optional[set] = None,
        state_guard_callbacks: Optional[set] = None,
        state_guard_hint_func: Optional[Any] = None,
    ):
        from aioscam.config import get_config

        super().__init__("Dispatcher")
        self.storage = storage or MemoryStorage()
        self._running = False
        self._polling_offset: Optional[int] = None
        self._lock = asyncio.Lock()
        self._webhook_secret: Optional[str] = None
        self._webhook_stop_event: Optional[asyncio.Event] = None

        # StateGuard configuration (customizable)
        self._guard_allowed_commands = state_guard_commands or {'/cancel', '/start'}
        self._guard_allowed_callbacks = state_guard_callbacks or {'action:cancel'}
        self._guard_hint_func = state_guard_hint_func  # callable: state_name -> hint text

        # Setup logging based on environment config
        config = get_config()
        config.setup_logging("aioscam")

    def _get_state_hint(self, state_name: str) -> str:
        """Get hint text for current FSM state."""
        if self._guard_hint_func:
            hint = self._guard_hint_func(state_name)
            if hint:
                return hint
        return "ожидаемые данные"

    def _extract_chat_and_user_ids(self, context):
        """
        Extract chat_id and user_id from EventContext.

        Works for both message and callback events.
        For callbacks, user_id comes from callback.user, not message.sender.
        """
        chat_id = None
        user_id = None

        # Try via chat property
        if hasattr(context, 'chat') and context.chat:
            chat = context.chat
            if hasattr(chat, 'chat_id'):
                chat_id = chat.chat_id
            elif isinstance(chat, dict):
                chat_id = chat.get('chat_id')

        # For callback: extract user_id from callback.user FIRST (priority)
        event = getattr(context, 'event', None)
        if event and hasattr(event, 'callback') and event.callback:
            cb = event.callback
            if isinstance(cb, dict) and 'user' in cb:
                user = cb['user']
                if isinstance(user, dict):
                    user_id = user.get('id') or user.get('user_id')
                elif hasattr(user, 'id') and user.id is not None:
                    user_id = user.id
                elif hasattr(user, 'user_id') and user.user_id is not None:
                    user_id = user.user_id

        # For messages: extract from sender
        if user_id is None and hasattr(context, 'from_user') and context.from_user:
            user = context.from_user
            if hasattr(user, 'id') and user.id is not None:
                user_id = user.id
            elif hasattr(user, 'user_id') and user.user_id is not None:
                user_id = user.user_id
            elif isinstance(user, dict):
                user_id = user.get('id') or user.get('user_id')

        return chat_id, user_id

    async def process_message(self, event, data=None) -> Any:
        """Process message event with state injection"""
        if data is None:
            data = {}

        # Extract chat_id and user_id from event
        chat_id, user_id = self._extract_chat_and_user_ids(event)

        # Create state context and inject into both data dict and event.data
        state_ctx = StateContext(self.storage, chat_id, user_id)
        data['state'] = state_ctx

        # Also inject into event.data if event is EventContext
        if hasattr(event, 'data'):
            event.data['state'] = state_ctx

        # STATE GUARD: block unauthorized commands during active FSM
        text = getattr(event, 'text', '') or ''
        if isinstance(text, str) and text.startswith('/'):
            command = text.split()[0].lower()
            if command not in self._guard_allowed_commands:
                current = await state_ctx.get_state()
                if current:
                    hint = self._get_state_hint(current)
                    bot = getattr(event, 'bot', None)
                    if bot and chat_id:
                        await bot.send_message(chat_id, f"⏳ Сейчас бот ждёт: {hint}\n\nДля отмены: /cancel\nДля перезапуска: /start")
                    return None  # Block handler

        return await super().process_message(event, data)

    async def process_callback(self, event, data=None) -> Any:
        """Process callback event with state injection"""
        if data is None:
            data = {}

        # Extract chat_id and user_id from event
        chat_id, user_id = self._extract_chat_and_user_ids(event)

        # Create state context and inject into both data dict and event.data
        state_ctx = StateContext(self.storage, chat_id, user_id)
        data['state'] = state_ctx

        # Also inject into event.data if event is EventContext
        if hasattr(event, 'data'):
            event.data['state'] = state_ctx

        # STATE GUARD: block callback actions during active FSM
        payload = ''
        if hasattr(event, 'callback_data'):
            payload = event.callback_data or ''
        elif hasattr(event, 'payload'):
            payload = event.payload or ''
        if not isinstance(payload, str):
            payload = str(payload) if payload else ''

        if payload:
            if payload not in self._guard_allowed_callbacks:
                current = await state_ctx.get_state()
                if current:
                    hint = self._get_state_hint(current)
                    bot = getattr(event, 'bot', None)
                    if bot and chat_id:
                        await bot.send_message(chat_id, f"⏳ Сначала завершите текущий процесс!\n\nБот ждёт: {hint}\n\nИли нажмите /cancel для отмены")
                    return None  # Block handler

        return await super().process_callback(event, data)

    async def process_event(self, event_type: str, event, data=None) -> Any:
        """Process generic event with state injection"""
        if data is None:
            data = {}

        # Extract chat_id and user_id from event
        chat_id, user_id = self._extract_chat_and_user_ids(event)

        # Create state context and inject into both data dict and event.data
        state_ctx = StateContext(self.storage, chat_id, user_id)
        data['state'] = state_ctx

        # Also inject into event.data if event is EventContext
        if hasattr(event, 'data'):
            event.data['state'] = state_ctx

        return await super().process_event(event_type, event, data)
    
    async def start_polling(
        self,
        bot: Bot,
        skip_updates: bool = True,
        timeout: int = 30,
        limit: int = 100,
    ) -> None:
        """
        Start polling for updates
        
        Args:
            bot: Bot instance
            skip_updates: Skip pending updates on start
            timeout: Long polling timeout
            limit: Updates limit per request
        """
        async with self._lock:
            if self._running:
                raise DispatcherError("Polling is already running")
            self._running = True

        logger.info("Starting polling...")

        # Auto-branding: append [Powered by AioScam vX.Y.Z] to bot description
        if getattr(bot, 'auto_brand', True):
            try:
                updated = await bot._ensure_branding()
                if updated:
                    logger.info("Bot description branded with AioScam version tag")
            except Exception as e:
                logger.debug(f"Auto-branding skipped: {e}")

        # Delete webhook if active
        try:
            subscriptions = await bot.get_subscriptions()
            if subscriptions:
                # subscriptions can be list of URLs (strings) or list of dicts
                logger.info(f"Found {len(subscriptions)} webhook subscriptions, deleting...")
                for sub in subscriptions:
                    if isinstance(sub, dict):
                        url = sub.get("url")
                    else:
                        url = str(sub)
                    if url:
                        await bot.unsubscribe_webhook(url=url)
                        logger.info(f"Deleted webhook: {url}")
            else:
                logger.info("No active webhook subscriptions found")
        except Exception as e:
            logger.warning(f"Failed to check/delete webhook: {e}")
        
        # Get initial marker if skip_updates
        if skip_updates:
            try:
                marker = await bot.get_last_marker()
                if marker:
                    self._polling_offset = marker
                    logger.info(f"Skipped updates, starting from marker: {marker}")
            except Exception as e:
                logger.warning(f"Failed to skip updates: {e}")
        
        retry_count = 0
        max_retry_delay = 30
        
        try:
            while self._running:
                try:
                    updates_data = await bot.get_updates(
                        marker=self._polling_offset,
                        limit=limit,
                        timeout=timeout,
                    )

                    # Extract updates and marker from response
                    updates_response = updates_data.get("updates", [])
                    api_marker = updates_data.get("marker")

                    # Reset retry count on success
                    retry_count = 0

                    if updates_response:
                        logger.info(f"Received {len(updates_response)} updates")

                        for update_data in updates_response:
                            try:
                                # Handle string updates
                                if isinstance(update_data, str):
                                    update_data = json.loads(update_data)

                                logger.info(f"Raw update data: {update_data}")

                                update = Update(**update_data)
                                # Process updates in parallel to avoid blocking the loop
                                asyncio.create_task(self._process_update(bot, update))
                            except Exception as e:
                                logger.error(f"Error processing single update: {e}", exc_info=True)
                                logger.error(f"Problematic update data: {update_data}")
                                # Continue processing other updates
                                continue

                    # Update marker from API response (not from update body!)
                    if api_marker is not None:
                        self._polling_offset = api_marker
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error in polling loop (retry {retry_count}): {e}")
                    
                    # Exponential backoff
                    delay = min(2 ** retry_count, max_retry_delay)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
        
        except KeyboardInterrupt:
            logger.info("Polling stopped by user")
        finally:
            async with self._lock:
                self._running = False
            await self.storage.close()
    
    async def stop_polling(self) -> None:
        """Stop polling"""
        self._running = False

    def stop_webhook(self) -> None:
        """
        Programmatically stop the webhook server started by handle_webhook().

        Example:
            asyncio.get_event_loop().call_later(60, dp.stop_webhook)
        """
        if hasattr(self, "_webhook_stop_event") and self._webhook_stop_event:
            self._webhook_stop_event.set()

    async def _process_update(self, bot: Bot, update: Update) -> None:
        """
        Process single update

        Args:
            bot: Bot instance
            update: Update object
        """
        try:
            event_type = update.event_type
            event = update.event

            if not event_type or not event:
                logger.warning(f"Unknown update type: {update}")
                return

            # Create event context with shared data dict
            context = EventContext(event, bot, data={
                'raw_update': update.model_dump() if hasattr(update, 'model_dump') else {}
            })

            # Process based on type
            if event_type == "message_created":
                await self.process_message(context)
            elif event_type == "message_edited":
                await self.process_event('message_edited', context)
            elif event_type == "message_callback":
                # process_callback() handles state injection via _extract_chat_and_user_ids
                await self.process_callback(context)
            elif event_type == "message_removed":
                await self.process_event('message_removed', context)
            else:
                # Try to process as a generic event
                try:
                    await self.process_event(event_type, context)
                except Exception as e:
                    logger.warning(f"No handler for event type: {event_type}")
        
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
    
    async def handle_webhook(
        self,
        bot: Bot,
        host: str = "0.0.0.0",
        port: int = 8080,
        path: str = "/webhook",
        secret_token: Optional[str] = None,
    ) -> None:
        """
        Start webhook server (aiohttp).

        Runs until SIGINT (Ctrl+C) or SIGTERM (systemd stop).
        Can also be stopped programmatically via stop_webhook().

        Args:
            bot: Bot instance
            host: Server host
            port: Server port
            path: Webhook path
            secret_token: Secret token — validated via X-Max-Secret-Token header
        """
        import signal
        from aiohttp import web

        # Auto-branding: append [Powered by AioScam vX.Y.Z] to bot description
        if getattr(bot, 'auto_brand', True):
            try:
                updated = await bot._ensure_branding()
                if updated:
                    logger.info("Bot description branded with AioScam version tag")
            except Exception as e:
                logger.debug(f"Auto-branding skipped: {e}")


        self._webhook_secret = secret_token
        self._webhook_stop_event = asyncio.Event()
        app = web.Application()

        async def webhook_handler(request):
            # Validate secret token if provided
            if self._webhook_secret:
                incoming = request.headers.get("X-Max-Secret-Token", "")
                if incoming != self._webhook_secret:
                    logger.warning(
                        f"Webhook rejected: invalid X-Max-Secret-Token (from {request.remote})"
                    )
                    return web.json_response(
                        {"ok": False, "error": "Unauthorized"}, status=401
                    )
            try:
                data = await request.json()
                update = Update(**data)
                # Process update in parallel to avoid blocking the webhook response
                asyncio.create_task(self._process_update(bot, update))
                return web.json_response({"ok": True})
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return web.json_response({"ok": False, "error": "Internal error"}, status=500)

        app.router.add_post(path, webhook_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)

        loop = asyncio.get_running_loop()

        def _signal_handler():
            logger.info("Shutdown signal received, stopping webhook...")
            self._webhook_stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except (NotImplementedError, RuntimeError):
                # Windows doesn't support add_signal_handler
                pass

        try:
            await site.start()
            logger.info(f"Webhook running on http://{host}:{port}{path}")
            await self._webhook_stop_event.wait()
        finally:
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.remove_signal_handler(sig)
                except (NotImplementedError, RuntimeError):
                    pass
            await runner.cleanup()
            logger.info("Webhook server stopped")
    
    async def shutdown(self) -> None:
        """Shutdown dispatcher and close resources"""
        await self.stop_polling()
        await self.storage.close()
