"""
ChatRegistry — persistent chat/group registry for Max bots

Max API removed the GET /chats listing in June 2026: a bot can no longer ask
the server "which chats am I in?". The registry rebuilds that knowledge on the
bot side and keeps it in SQLite:

- registry events (bot_added / bot_removed / chat_title_changed / ...) are
  applied to the database as they arrive;
- lazy discovery: any update carrying an unknown chat_id registers the chat;
- the long-polling marker is persisted, so a restart resumes from where the
  bot stopped and downtime events are not lost (within Max queue retention);
- sync() reconciles the registry against the live API via per-chat GET calls
  (those endpoints were not removed).

Usage:
    from aioscam.registry import ChatRegistry

    registry = ChatRegistry()          # ./.aioscam/bot.db (общая база бота)
    dp = Dispatcher(registry=registry)
    await dp.start_polling(bot, backlog="collapse")

    chats = await registry.chats()
    groups = await registry.groups()
    stats = await registry.sync(bot)   # manual reconciliation
"""

import json
import logging
import sqlite3
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from aioscam.db import DEFAULT_DB_PATH, Database

logger = logging.getLogger(__name__)

# Update types that change registry state and are applied silently even when
# the backlog policy drops user-facing events
REGISTRY_UPDATE_TYPES = {
    "bot_added",
    "bot_removed",
    "bot_started",
    "chat_title_changed",
    "dialog_removed",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    type TEXT,
    title TEXT,
    status TEXT,
    is_public INTEGER,
    link TEXT,
    owner_id INTEGER,
    participants_count INTEGER,
    bot_is_admin INTEGER,
    bot_permissions TEXT,
    permissions_checked_at REAL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    removed_at REAL
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

_CHAT_FIELDS = {
    "type", "title", "status", "is_public", "link", "owner_id",
    "participants_count", "bot_is_admin", "bot_permissions",
    "permissions_checked_at",
}


class ChatRegistry:
    """
    SQLite-backed registry of chats the bot participates in.

    All public methods are async; SQLite calls run in a thread executor
    (stdlib sqlite3, no extra dependencies — writes are infrequent).
    """

    def __init__(self, path: Union[str, Path] = DEFAULT_DB_PATH):
        # Shared bot database — PollManager and other components pointing at
        # the same path reuse this connection (see aioscam.db.Database)
        self._db = Database.open(path)
        self._started = False

    # ==================== lifecycle ====================

    async def start(self) -> None:
        """Open the shared database and apply this component's schema."""
        if self._started:
            return
        await self._db.executescript(_SCHEMA)
        self._started = True
        logger.info(f"ChatRegistry started: {self._db.path}")

    async def close(self) -> None:
        await self._db.close()
        self._started = False

    async def _execute(self, sql: str, params: tuple = ()) -> list:
        if not self._started:
            await self.start()
        return await self._db.execute(sql, params)

    # ==================== chats ====================

    async def upsert_chat(self, chat_id: int, **fields: Any) -> None:
        """
        Insert or update a chat. Unknown fields are ignored; a previously
        removed chat is resurrected (removed_at reset to NULL).
        """
        now = time.time()
        clean = {k: v for k, v in fields.items() if k in _CHAT_FIELDS and v is not None}
        if "bot_permissions" in clean and not isinstance(clean["bot_permissions"], str):
            clean["bot_permissions"] = json.dumps(clean["bot_permissions"], ensure_ascii=False)

        columns = ["chat_id", "first_seen", "last_seen", "removed_at"] + list(clean.keys())
        values = [chat_id, now, now, None] + list(clean.values())
        updates = ["last_seen=excluded.last_seen", "removed_at=NULL"] + [
            f"{k}=excluded.{k}" for k in clean.keys()
        ]
        sql = (
            f"INSERT INTO chats ({','.join(columns)}) "
            f"VALUES ({','.join('?' * len(columns))}) "
            f"ON CONFLICT(chat_id) DO UPDATE SET {','.join(updates)}"
        )
        await self._execute(sql, tuple(values))

    async def mark_removed(self, chat_id: int) -> None:
        """Soft-delete: the row stays for history, removed_at is set."""
        await self._execute(
            "UPDATE chats SET removed_at=?, last_seen=? WHERE chat_id=?",
            (time.time(), time.time(), chat_id),
        )

    async def get(self, chat_id: int) -> Optional[Dict[str, Any]]:
        rows = await self._execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,))
        return self._row_to_dict(rows[0]) if rows else None

    async def chats(
        self,
        chat_type: Optional[str] = None,
        include_removed: bool = False,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM chats"
        conditions, params = [], []
        if not include_removed:
            conditions.append("removed_at IS NULL")
        if chat_type:
            conditions.append("type=?")
            params.append(chat_type)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY last_seen DESC"
        rows = await self._execute(sql, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    async def groups(self) -> List[Dict[str, Any]]:
        return await self.chats(chat_type="chat")

    async def dialogs(self) -> List[Dict[str, Any]]:
        return await self.chats(chat_type="dialog")

    async def channels(self) -> List[Dict[str, Any]]:
        return await self.chats(chat_type="channel")

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if d.get("bot_permissions"):
            try:
                d["bot_permissions"] = json.loads(d["bot_permissions"])
            except (ValueError, TypeError):
                pass
        return d

    # ==================== polling marker ====================

    async def get_marker(self) -> Optional[int]:
        rows = await self._execute("SELECT value FROM kv WHERE key='polling_marker'")
        return int(rows[0]["value"]) if rows else None

    async def set_marker(self, marker: int) -> None:
        await self._execute(
            "INSERT INTO kv (key, value) VALUES ('polling_marker', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(marker),),
        )

    # ==================== event ingestion ====================

    async def apply_update(self, update: Any) -> None:
        """
        Apply a single update to the registry: registry events change state,
        anything else with a chat_id performs lazy discovery.
        Never raises — registry failures must not break dispatching.
        """
        try:
            update_type = getattr(update, "update_type", None)
            chat_id, chat_type = self._extract_chat(update)
            if chat_id is None:
                return

            if update_type == "bot_removed" or update_type == "dialog_removed":
                await self.mark_removed(chat_id)
            elif update_type == "chat_title_changed":
                title = getattr(update, "title", None)
                await self.upsert_chat(chat_id, type=chat_type, title=title)
            else:
                # bot_added, bot_started, message_created, callbacks, ... —
                # anything alive in this chat proves the bot is still there
                await self.upsert_chat(chat_id, type=chat_type)
        except Exception as e:
            logger.warning(f"ChatRegistry.apply_update failed: {e}")

    @staticmethod
    def _extract_chat(update: Any) -> tuple:
        """Pull (chat_id, chat_type) out of any update shape."""
        message = getattr(update, "message", None)
        if message is not None:
            recipient = getattr(message, "recipient", None)
            if recipient is not None:
                return (
                    getattr(recipient, "chat_id", None),
                    getattr(recipient, "chat_type", None),
                )
        chat_id = getattr(update, "chat_id", None)
        if chat_id is not None:
            # bot_started and dialog-level events carry a bare chat_id;
            # bot_added/bot_removed refer to group chats
            update_type = getattr(update, "update_type", "") or ""
            chat_type = "dialog" if update_type in ("bot_started", "dialog_removed") else "chat"
            return chat_id, chat_type
        return None, None

    # ==================== reconciliation ====================

    async def sync(
        self,
        bot: Any,
        refresh_permissions: bool = True,
        permissions_ttl: float = 3600.0,
    ) -> Dict[str, int]:
        """
        Reconcile the registry against the live API.

        1. Best-effort bootstrap via the deprecated GET /chats while it lasts.
        2. Per known chat: GET /chats/{id} — 403/404 marks it removed,
           success refreshes title/status/participants.
        3. Optionally refresh bot permissions via /chats/{id}/members/me for
           group chats whose cached permissions are older than permissions_ttl.

        Returns:
            Stats dict: {"bootstrapped", "checked", "updated", "removed"}
        """
        from aioscam.exceptions import ForbiddenError, NotFoundError

        stats = {"bootstrapped": 0, "checked": 0, "updated": 0, "removed": 0}

        # 1. bootstrap — the listing may already be gone, ignore any failure
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                listed = await bot.get_chats()
            for chat in listed or []:
                cid = chat.get("chat_id")
                if cid is None:
                    continue
                await self.upsert_chat(
                    cid,
                    type=chat.get("type"),
                    title=chat.get("title"),
                    status=chat.get("status"),
                    is_public=chat.get("is_public"),
                    link=chat.get("link"),
                    owner_id=chat.get("owner_id"),
                    participants_count=chat.get("participants_count"),
                )
                stats["bootstrapped"] += 1
        except Exception as e:
            logger.info(f"sync bootstrap via GET /chats unavailable: {e}")

        # 2. reconcile every known chat via point lookups
        now = time.time()
        for chat in await self.chats():
            cid = chat["chat_id"]
            stats["checked"] += 1
            try:
                info = await bot.get_chat_by_id(id=cid)
            except (NotFoundError, ForbiddenError):
                await self.mark_removed(cid)
                stats["removed"] += 1
                continue
            except Exception as e:
                logger.warning(f"sync: GET /chats/{cid} failed, keeping as-is: {e}")
                continue

            fields: Dict[str, Any] = {
                "type": info.get("type"),
                "title": info.get("title"),
                "status": info.get("status"),
                "is_public": info.get("is_public"),
                "link": info.get("link"),
                "owner_id": info.get("owner_id"),
                "participants_count": info.get("participants_count"),
            }

            # 3. permissions TTL refresh (group chats only — dialogs have none)
            checked_at = chat.get("permissions_checked_at") or 0
            if (
                refresh_permissions
                and info.get("type") != "dialog"
                and now - checked_at > permissions_ttl
            ):
                try:
                    me = await bot.get_me_from_chat(chat_id=cid)
                    fields["bot_is_admin"] = 1 if me.get("is_admin") else 0
                    fields["bot_permissions"] = me.get("permissions") or []
                    fields["permissions_checked_at"] = now
                except Exception as e:
                    logger.debug(f"sync: members/me for {cid} failed: {e}")

            await self.upsert_chat(cid, **fields)
            stats["updated"] += 1

        logger.info(f"ChatRegistry.sync done: {stats}")
        return stats
