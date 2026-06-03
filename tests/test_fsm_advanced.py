"""
Advanced FSM tests: MemoryStorage edge cases, StateContext operations,
StatesGroup / State behavior.
"""

import pytest
from aioscam.fsm.memory import MemoryStorage
from aioscam.fsm.state import State, StatesGroup
from aioscam.dispatcher.state import StateContext


# ─── MemoryStorage ───────────────────────────────────────────────────────────

class TestMemoryStorageKey:
    @pytest.mark.asyncio
    async def test_key_with_user_id(self):
        storage = MemoryStorage()
        await storage.set_state(1, "active", user_id=2)
        result = await storage.get_state(1, user_id=2)
        assert result == "active"

    @pytest.mark.asyncio
    async def test_key_without_user_id_separate_namespace(self):
        storage = MemoryStorage()
        await storage.set_state(1, "with_user", user_id=2)
        await storage.set_state(1, "without_user")
        assert await storage.get_state(1, user_id=2) == "with_user"
        assert await storage.get_state(1) == "without_user"

    @pytest.mark.asyncio
    async def test_user_id_zero_is_valid(self):
        """user_id=0 must NOT be treated as missing — bug was `if user_id:`"""
        storage = MemoryStorage()
        await storage.set_state(1, "zero_user", user_id=0)
        result = await storage.get_state(1, user_id=0)
        assert result == "zero_user"
        # And it must differ from the no-user-id key
        assert await storage.get_state(1) is None

    @pytest.mark.asyncio
    async def test_different_chats_isolated(self):
        storage = MemoryStorage()
        await storage.set_state(10, "state_a", user_id=1)
        await storage.set_state(20, "state_b", user_id=1)
        assert await storage.get_state(10, user_id=1) == "state_a"
        assert await storage.get_state(20, user_id=1) == "state_b"


class TestMemoryStorageCRUD:
    @pytest.mark.asyncio
    async def test_state_set_get(self):
        storage = MemoryStorage()
        await storage.set_state(1, "step1", user_id=1)
        assert await storage.get_state(1, user_id=1) == "step1"

    @pytest.mark.asyncio
    async def test_state_clear(self):
        storage = MemoryStorage()
        await storage.set_state(1, "step1", user_id=1)
        await storage.set_state(1, None, user_id=1)
        assert await storage.get_state(1, user_id=1) is None

    @pytest.mark.asyncio
    async def test_data_set_get(self):
        storage = MemoryStorage()
        await storage.set_data(1, {"name": "Alice"}, user_id=1)
        data = await storage.get_data(1, user_id=1)
        assert data == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_data_update_merges(self):
        storage = MemoryStorage()
        await storage.set_data(1, {"a": 1}, user_id=1)
        result = await storage.update_data(1, {"b": 2}, user_id=1)
        assert result == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_data_update_overwrites_key(self):
        storage = MemoryStorage()
        await storage.set_data(1, {"a": 1}, user_id=1)
        result = await storage.update_data(1, {"a": 99}, user_id=1)
        assert result["a"] == 99

    @pytest.mark.asyncio
    async def test_get_data_empty_returns_dict(self):
        storage = MemoryStorage()
        data = await storage.get_data(999, user_id=1)
        assert data == {}

    @pytest.mark.asyncio
    async def test_close_clears_all(self):
        storage = MemoryStorage()
        await storage.set_state(1, "s", user_id=1)
        await storage.set_data(1, {"k": "v"}, user_id=1)
        await storage.close()
        assert await storage.get_state(1, user_id=1) is None
        assert await storage.get_data(1, user_id=1) == {}


# ─── StatesGroup / State ─────────────────────────────────────────────────────

class TestStatesGroup:
    def test_states_have_full_name(self):
        class MyState(StatesGroup):
            waiting = State()
            done = State()

        assert MyState.waiting.full_name == "MyState:waiting"
        assert MyState.done.full_name == "MyState:done"

    def test_state_equality_with_string(self):
        class MyState(StatesGroup):
            step = State()

        assert MyState.step == "MyState:step"

    def test_state_inequality(self):
        class MyState(StatesGroup):
            a = State()
            b = State()

        assert MyState.a != MyState.b

    def test_state_hash_unique(self):
        class MyState(StatesGroup):
            s1 = State()
            s2 = State()

        s = {MyState.s1, MyState.s2}
        assert len(s) == 2

    def test_states_across_groups_not_equal(self):
        class GroupA(StatesGroup):
            step = State()

        class GroupB(StatesGroup):
            step = State()

        assert GroupA.step != GroupB.step

    def test_state_repr(self):
        class MyState(StatesGroup):
            active = State()

        assert "MyState:active" in repr(MyState.active)


# ─── StateContext ─────────────────────────────────────────────────────────────

class TestStateContext:
    @pytest.mark.asyncio
    async def test_set_get_state_string(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=1, user_id=1)
        await ctx.set_state("MyGroup:step1")
        assert await ctx.get_state() == "MyGroup:step1"

    @pytest.mark.asyncio
    async def test_set_state_with_state_object(self):
        class MyState(StatesGroup):
            step = State()

        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=1, user_id=1)
        await ctx.set_state(MyState.step)
        assert await ctx.get_state() == "MyState:step"

    @pytest.mark.asyncio
    async def test_clear_state(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=1, user_id=1)
        await ctx.set_state("some_state")
        await ctx.set_state(None)
        assert await ctx.get_state() is None

    @pytest.mark.asyncio
    async def test_data_operations(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=1, user_id=1)
        await ctx.set_data({"name": "Bob"})
        data = await ctx.get_data()
        assert data["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_update_data_kwargs(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=1, user_id=1)
        await ctx.update_data(name="Alice", age=30)
        data = await ctx.get_data()
        assert data["name"] == "Alice"
        assert data["age"] == 30

    @pytest.mark.asyncio
    async def test_no_chat_id_returns_none(self):
        storage = MemoryStorage()
        ctx = StateContext(storage, chat_id=None, user_id=1)
        assert await ctx.get_state() is None
        await ctx.set_state("should_not_crash")  # should not raise

    @pytest.mark.asyncio
    async def test_multiple_users_isolated(self):
        storage = MemoryStorage()
        ctx1 = StateContext(storage, chat_id=1, user_id=1)
        ctx2 = StateContext(storage, chat_id=1, user_id=2)
        await ctx1.set_state("user1_state")
        await ctx2.set_state("user2_state")
        assert await ctx1.get_state() == "user1_state"
        assert await ctx2.get_state() == "user2_state"
