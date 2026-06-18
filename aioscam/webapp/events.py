"""
Server-Sent Events manager for Max WebApp ↔ Bot two-way communication.

Bot pushes events to connected WebApp clients in real-time.
WebApp subscribes via GET /api/events (SSE stream).

Usage::

    manager = EventStreamManager()

    # In bot handler — push event to user's WebApp
    await manager.publish(user_id=123, event="message", data={"text": "Hello!"})

    # In aiohttp handler — stream events to WebApp
    async def handle_events(request):
        user_id = request["webapp_init_data"].user.id
        async for chunk in manager.stream(user_id, request):
            ...
"""

import asyncio
import json
import logging
from typing import List, Optional

from aiohttp import web

logger = logging.getLogger(__name__)


class EventStreamManager:
    """
    Manages SSE connections per user_id.

    Each user can have multiple active WebApp tabs — all receive events.
    """

    def __init__(self):
        self._queues: dict = {}

    def _connect(self, user_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(user_id, []).append(q)
        logger.debug(f"SSE connect user={user_id} total_connections={len(self._queues[user_id])}")
        return q

    def _disconnect(self, user_id: int, q: asyncio.Queue) -> None:
        conns = self._queues.get(user_id, [])
        try:
            conns.remove(q)
        except ValueError:
            pass
        if not conns:
            self._queues.pop(user_id, None)
        logger.debug(f"SSE disconnect user={user_id}")

    async def publish(self, user_id: int, event: str, data: dict) -> int:
        """
        Push an event to all WebApp connections for a user.

        Returns number of connections that received the event.
        """
        conns = self._queues.get(user_id, [])
        for q in conns:
            await q.put({"event": event, "data": data})
        return len(conns)

    async def broadcast(self, event: str, data: dict) -> int:
        """Push event to ALL connected users. Returns total connections notified."""
        total = 0
        for user_id in list(self._queues.keys()):
            total += await self.publish(user_id, event, data)
        return total

    def active_users(self) -> List[int]:
        return list(self._queues.keys())

    def connection_count(self, user_id: Optional[int] = None) -> int:
        if user_id is not None:
            return len(self._queues.get(user_id, []))
        return sum(len(v) for v in self._queues.values())

    async def stream(
        self,
        request: web.Request,
        user_id: int,
        heartbeat_interval: int = 25,
    ) -> web.StreamResponse:
        """
        SSE stream handler. Keeps connection alive until client disconnects.

        Usage in aiohttp handler::

            return await manager.stream(request, user_id=init_data.user.id)
        """
        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)

        q = self._connect(user_id)
        try:
            await _send_sse(response, "connected", {"user_id": user_id})

            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=heartbeat_interval)
                    await _send_sse(response, msg["event"], msg["data"])
                except asyncio.TimeoutError:
                    await response.write(b": heartbeat\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            self._disconnect(user_id, q)

        return response


async def _send_sse(response: web.StreamResponse, event: str, data: dict) -> None:
    payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    await response.write(payload.encode())
