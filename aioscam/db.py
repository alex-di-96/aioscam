"""
Shared SQLite database for framework components

ChatRegistry, PollManager (and future components) keep their tables in ONE
bot-local database file — ``.aioscam/bot.db`` by default. ``Database.open()``
returns a cached instance per resolved path, so components pointing at the
same file share a single connection and asyncio lock instead of competing
writers.

Usage:
    registry = ChatRegistry()          # both land in .aioscam/bot.db
    polls = PollManager()              # same Database instance under the hood

    # custom path — still shared when the path matches:
    registry = ChatRegistry("data/mybot.db")
    polls = PollManager("data/mybot.db")
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = ".aioscam/bot.db"


class Database:
    """
    Thin async wrapper over stdlib sqlite3 (executor-based, no dependencies).

    Instances are cached per absolute path — every component opening the same
    file gets the same object. ``:memory:`` databases are never cached (each
    caller gets a private one). Reference counting makes ``close()`` safe to
    call from every component: the connection actually closes when the last
    user releases it.
    """

    _instances: Dict[str, "Database"] = {}

    def __init__(self, path: Union[str, Path] = DEFAULT_DB_PATH):
        self._path = Path(path)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
        self._refs = 0

    @classmethod
    def open(cls, path: Union[str, Path] = DEFAULT_DB_PATH) -> "Database":
        """Get the shared Database for a path (acquires one reference)."""
        if str(path) == ":memory:":
            db = cls(path)
        else:
            key = str(Path(path).resolve())
            db = cls._instances.get(key)
            if db is None:
                db = cls(path)
                cls._instances[key] = db
        db._refs += 1
        return db

    @property
    def path(self) -> Path:
        return self._path

    async def start(self) -> None:
        """Open the connection (idempotent, creates parent dirs)."""
        if self._conn is not None:
            return
        await asyncio.to_thread(self._open)
        logger.info(f"Database opened: {self._path}")

    def _open(self) -> None:
        if str(self._path) != ":memory:":
            self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        self._conn = conn

    async def close(self) -> None:
        """Release one reference; the connection closes with the last one."""
        if self._refs > 0:
            self._refs -= 1
        if self._refs > 0 or self._conn is None:
            return
        await asyncio.to_thread(self._conn.close)
        self._conn = None
        key = str(self._path.resolve()) if str(self._path) != ":memory:" else None
        if key and self._instances.get(key) is self:
            del self._instances[key]

    async def executescript(self, script: str) -> None:
        """Run a DDL script (component schema setup)."""
        if self._conn is None:
            await self.start()

        def _run():
            self._conn.executescript(script)
            self._conn.commit()

        async with self._lock:
            await asyncio.to_thread(_run)

    async def execute(self, sql: str, params: tuple = ()) -> list:
        """Run one statement, commit, return fetched rows."""
        if self._conn is None:
            await self.start()

        def _run():
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            self._conn.commit()
            return rows

        async with self._lock:
            return await asyncio.to_thread(_run)
