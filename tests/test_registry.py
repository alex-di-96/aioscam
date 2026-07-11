"""
Tests for ChatRegistry (aioscam.registry) and Dispatcher backlog policies
"""

import asyncio
import time

import pytest
from unittest.mock import AsyncMock

from aioscam import Bot, Dispatcher
from aioscam.registry import ChatRegistry
from aioscam.types.update import Update


@pytest.fixture
async def registry(tmp_path):
    reg = ChatRegistry(tmp_path / "registry.db")
    await reg.start()
    yield reg
    await reg.close()


# ─── CRUD / soft-delete ──────────────────────────────────────────────────────

class TestRegistryCrud:
    @pytest.mark.asyncio
    async def test_upsert_and_get(self, registry):
        await registry.upsert_chat(100, type="chat", title="Test Group")
        chat = await registry.get(100)
        assert chat["title"] == "Test Group"
        assert chat["type"] == "chat"
        assert chat["removed_at"] is None

    @pytest.mark.asyncio
    async def test_upsert_updates_fields(self, registry):
        await registry.upsert_chat(100, type="chat", title="Old")
        await registry.upsert_chat(100, title="New")
        chat = await registry.get(100)
        assert chat["title"] == "New"
        assert chat["type"] == "chat"  # untouched field preserved

    @pytest.mark.asyncio
    async def test_soft_delete_and_resurrect(self, registry):
        await registry.upsert_chat(100, type="chat")
        await registry.mark_removed(100)
        assert (await registry.get(100))["removed_at"] is not None
        assert await registry.chats() == []
        assert len(await registry.chats(include_removed=True)) == 1
        # bot re-added → row comes back to life
        await registry.upsert_chat(100, type="chat")
        assert (await registry.get(100))["removed_at"] is None

    @pytest.mark.asyncio
    async def test_type_filters(self, registry):
        await registry.upsert_chat(1, type="dialog")
        await registry.upsert_chat(2, type="chat")
        await registry.upsert_chat(3, type="channel")
        assert [c["chat_id"] for c in await registry.dialogs()] == [1]
        assert [c["chat_id"] for c in await registry.groups()] == [2]
        assert [c["chat_id"] for c in await registry.channels()] == [3]

    @pytest.mark.asyncio
    async def test_permissions_stored_as_json(self, registry):
        await registry.upsert_chat(100, type="chat", bot_permissions=["write", "pin_message"])
        chat = await registry.get(100)
        assert chat["bot_permissions"] == ["write", "pin_message"]

    @pytest.mark.asyncio
    async def test_persistence_across_reopen(self, tmp_path):
        path = tmp_path / "persist.db"
        reg1 = ChatRegistry(path)
        await reg1.upsert_chat(100, type="chat", title="Survives")
        await reg1.set_marker(555)
        await reg1.close()

        reg2 = ChatRegistry(path)
        assert (await reg2.get(100))["title"] == "Survives"
        assert await reg2.get_marker() == 555
        await reg2.close()


# ─── Marker ──────────────────────────────────────────────────────────────────

class TestMarker:
    @pytest.mark.asyncio
    async def test_marker_roundtrip(self, registry):
        assert await registry.get_marker() is None
        await registry.set_marker(123)
        assert await registry.get_marker() == 123
        await registry.set_marker(456)
        assert await registry.get_marker() == 456


# ─── apply_update ────────────────────────────────────────────────────────────

class TestApplyUpdate:
    @pytest.mark.asyncio
    async def test_bot_added_registers_group(self, registry):
        update = Update(update_type="bot_added", chat_id=-500, timestamp=1)
        await registry.apply_update(update)
        chat = await registry.get(-500)
        assert chat is not None
        assert chat["type"] == "chat"

    @pytest.mark.asyncio
    async def test_bot_removed_marks_removed(self, registry):
        await registry.apply_update(Update(update_type="bot_added", chat_id=-500, timestamp=1))
        await registry.apply_update(Update(update_type="bot_removed", chat_id=-500, timestamp=2))
        assert (await registry.get(-500))["removed_at"] is not None

    @pytest.mark.asyncio
    async def test_add_remove_add_sequence(self, registry):
        """Ordered application: final state must be 'present'."""
        for t, utype in enumerate(["bot_added", "bot_removed", "bot_added"]):
            await registry.apply_update(Update(update_type=utype, chat_id=-500, timestamp=t))
        assert (await registry.get(-500))["removed_at"] is None

    @pytest.mark.asyncio
    async def test_bot_started_registers_dialog(self, registry):
        update = Update(update_type="bot_started", chat_id=777, user_id=1, timestamp=1)
        await registry.apply_update(update)
        assert (await registry.get(777))["type"] == "dialog"

    @pytest.mark.asyncio
    async def test_lazy_discovery_from_message(self, registry):
        update = Update(**{
            "update_type": "message_created",
            "timestamp": 1,
            "message": {
                "recipient": {"chat_id": -900, "chat_type": "chat"},
                "body": {"mid": "m1", "seq": 1, "text": "hi"},
            },
        })
        await registry.apply_update(update)
        assert (await registry.get(-900))["type"] == "chat"

    @pytest.mark.asyncio
    async def test_update_without_chat_is_ignored(self, registry):
        await registry.apply_update(Update(update_type="message_removed", timestamp=1))
        assert await registry.chats() == []

    @pytest.mark.asyncio
    async def test_never_raises(self, registry):
        await registry.apply_update(object())  # garbage in — no exception out


# ─── sync() ──────────────────────────────────────────────────────────────────

def _bot_mock(**overrides):
    bot = AsyncMock(spec=Bot)
    bot.get_chats = AsyncMock(return_value=overrides.get("chats", []))
    bot.get_chat_by_id = AsyncMock(side_effect=overrides.get("chat_by_id"))
    bot.get_me_from_chat = AsyncMock(return_value=overrides.get("me", {}))
    return bot


class TestSync:
    @pytest.mark.asyncio
    async def test_bootstrap_from_get_chats(self, registry):
        bot = _bot_mock(
            chats=[{"chat_id": -1, "type": "chat", "title": "G1", "participants_count": 3}],
            chat_by_id=lambda **kw: {"chat_id": -1, "type": "chat", "title": "G1"},
        )
        stats = await registry.sync(bot, refresh_permissions=False)
        assert stats["bootstrapped"] == 1
        assert (await registry.get(-1))["title"] == "G1"

    @pytest.mark.asyncio
    async def test_dead_chat_marked_removed(self, registry):
        from aioscam.exceptions import NotFoundError
        await registry.upsert_chat(-1, type="chat")
        bot = _bot_mock(chat_by_id=NotFoundError("gone"))
        bot.get_chats = AsyncMock(side_effect=Exception("listing removed"))
        stats = await registry.sync(bot, refresh_permissions=False)
        assert stats["removed"] == 1
        assert (await registry.get(-1))["removed_at"] is not None

    @pytest.mark.asyncio
    async def test_permissions_refreshed_with_ttl(self, registry):
        await registry.upsert_chat(-1, type="chat")
        bot = _bot_mock(
            chat_by_id=lambda **kw: {"chat_id": -1, "type": "chat"},
            me={"is_admin": True, "permissions": ["write", "pin_message"]},
        )
        bot.get_chats = AsyncMock(return_value=[])
        await registry.sync(bot, refresh_permissions=True, permissions_ttl=0)
        chat = await registry.get(-1)
        assert chat["bot_is_admin"] == 1
        assert chat["bot_permissions"] == ["write", "pin_message"]
        assert chat["permissions_checked_at"] == pytest.approx(time.time(), abs=10)

    @pytest.mark.asyncio
    async def test_fresh_permissions_not_refetched(self, registry):
        await registry.upsert_chat(
            -1, type="chat", permissions_checked_at=time.time(),
        )
        bot = _bot_mock(chat_by_id=lambda **kw: {"chat_id": -1, "type": "chat"})
        bot.get_chats = AsyncMock(return_value=[])
        await registry.sync(bot, refresh_permissions=True, permissions_ttl=3600)
        bot.get_me_from_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_dialogs_skip_permission_refresh(self, registry):
        await registry.upsert_chat(7, type="dialog")
        bot = _bot_mock(chat_by_id=lambda **kw: {"chat_id": 7, "type": "dialog"})
        bot.get_chats = AsyncMock(return_value=[])
        await registry.sync(bot, refresh_permissions=True, permissions_ttl=0)
        bot.get_me_from_chat.assert_not_called()


# ─── Dispatcher: collapse / drain ────────────────────────────────────────────

def _msg_update(chat_id, user_id, text, ts):
    return Update(**{
        "update_type": "message_created",
        "timestamp": ts,
        "message": {
            "sender": {"user_id": user_id, "first_name": "U"},
            "recipient": {"chat_id": chat_id, "chat_type": "dialog"},
            "body": {"mid": f"m{ts}", "seq": ts, "text": text},
        },
    })


class TestCollapseBacklog:
    def test_50_starts_become_one(self):
        updates = [_msg_update(1, 10, "/start", ts) for ts in range(50)]
        result = Dispatcher._collapse_backlog(updates)
        assert len(result) == 1
        assert result[0].timestamp == 49  # last one wins

    def test_different_users_kept(self):
        updates = [
            _msg_update(1, 10, "/start", 1),
            _msg_update(1, 20, "/start", 2),
            _msg_update(2, 10, "/start", 3),
        ]
        assert len(Dispatcher._collapse_backlog(updates)) == 3

    def test_different_types_kept(self):
        updates = [
            _msg_update(1, 10, "hello", 1),
            Update(update_type="bot_started", chat_id=1, user_id=10, timestamp=2),
        ]
        assert len(Dispatcher._collapse_backlog(updates)) == 2

    def test_order_preserved(self):
        updates = [
            _msg_update(1, 10, "a", 1),
            _msg_update(2, 20, "b", 2),
            _msg_update(1, 10, "c", 3),
        ]
        result = Dispatcher._collapse_backlog(updates)
        assert [u.timestamp for u in result] == [2, 3]


class TestDrainBacklog:
    @pytest.mark.asyncio
    async def test_drains_until_empty(self):
        dp = Dispatcher()
        bot = AsyncMock(spec=Bot)
        batches = [
            {"updates": [{"update_type": "bot_started", "chat_id": 1, "user_id": 1, "timestamp": 1}], "marker": 10},
            {"updates": [{"update_type": "bot_started", "chat_id": 2, "user_id": 2, "timestamp": 2}], "marker": 20},
            {"updates": [], "marker": 20},
        ]
        bot.get_updates = AsyncMock(side_effect=batches)
        backlog = await dp._drain_backlog(bot, limit=100)
        assert len(backlog) == 2
        assert dp._polling_offset == 20
        # timeout=0 on every drain call — this is the fixed skip semantics
        for call in bot.get_updates.call_args_list:
            assert call.kwargs["timeout"] == 0

    @pytest.mark.asyncio
    async def test_empty_queue(self):
        dp = Dispatcher()
        bot = AsyncMock(spec=Bot)
        bot.get_updates = AsyncMock(return_value={"updates": [], "marker": 5})
        backlog = await dp._drain_backlog(bot, limit=100)
        assert backlog == []
        assert dp._polling_offset == 5
