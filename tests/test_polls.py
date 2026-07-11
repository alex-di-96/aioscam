"""
Tests for PollManager (aioscam.polls) — poll/quiz emulation over inline keyboards
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aioscam import Bot, Dispatcher
from aioscam.polls import PollManager


def _bot(mid="mid.1"):
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock(return_value={"message": {"body": {"mid": mid}}})
    bot.edit_message = AsyncMock(return_value={"success": True})
    bot.send_callback = AsyncMock(return_value={})
    return bot


def _vote_event(bot, poll_id, option_idx, user_id=10, callback_id="cb1", name="User Ten"):
    event = MagicMock()
    event.bot = bot
    event.callback_data = f"apoll:{poll_id}:{option_idx}"
    event.user_id = user_id
    event.callback_id = callback_id
    event.from_user = {"first_name": name.split()[0], "last_name": name.split()[-1]}
    return event


@pytest.fixture
async def polls(tmp_path):
    pm = PollManager(tmp_path / "polls.db")
    await pm.start()
    yield pm
    await pm.close()


# ─── send ────────────────────────────────────────────────────────────────────

class TestSendPoll:
    @pytest.mark.asyncio
    async def test_send_poll_returns_id_and_stores(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        assert len(poll_id) == 12
        results = await polls.results(poll_id)
        assert results["question"] == "Q?"
        assert results["options"] == ["A", "B"]
        assert results["mid"] == "mid.1"
        assert results["total_voters"] == 0

    @pytest.mark.asyncio
    async def test_keyboard_payloads(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        kb = bot.send_message.call_args.kwargs["inline_keyboard"]
        payloads = [row[0]["payload"] for row in kb["payload"]["buttons"]]
        assert payloads == [f"apoll:{poll_id}:0", f"apoll:{poll_id}:1"]

    @pytest.mark.asyncio
    async def test_option_count_validation(self, polls):
        bot = _bot()
        with pytest.raises(ValueError):
            await polls.send_poll(bot, 1, "Q?", ["only one"])
        with pytest.raises(ValueError):
            await polls.send_poll(bot, 1, "Q?", [str(i) for i in range(11)])

    @pytest.mark.asyncio
    async def test_quiz_correct_option_validation(self, polls):
        bot = _bot()
        with pytest.raises(ValueError):
            await polls.send_quiz(bot, 1, "Q?", ["A", "B"], correct_option=5)


# ─── voting: single choice ───────────────────────────────────────────────────

class TestSingleChoice:
    @pytest.mark.asyncio
    async def test_vote_counted(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        results = await polls.results(poll_id)
        assert results["counts"] == {0: 1}
        assert results["total_voters"] == 1
        bot.edit_message.assert_called()  # live message refresh

    @pytest.mark.asyncio
    async def test_revote_moves_vote(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        await polls._on_vote(_vote_event(bot, poll_id, 1))
        results = await polls.results(poll_id)
        assert results["counts"] == {1: 1}
        assert results["total_voters"] == 1

    @pytest.mark.asyncio
    async def test_same_option_reclick_no_duplicate(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        results = await polls.results(poll_id)
        assert results["counts"] == {0: 1}

    @pytest.mark.asyncio
    async def test_two_users(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls._on_vote(_vote_event(bot, poll_id, 0, user_id=10))
        await polls._on_vote(_vote_event(bot, poll_id, 0, user_id=20))
        results = await polls.results(poll_id)
        assert results["counts"] == {0: 2}
        assert results["total_voters"] == 2


# ─── voting: multiple choice ─────────────────────────────────────────────────

class TestMultipleChoice:
    @pytest.mark.asyncio
    async def test_toggle_on_and_off(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"], multiple=True)
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        await polls._on_vote(_vote_event(bot, poll_id, 1))
        assert (await polls.results(poll_id))["counts"] == {0: 1, 1: 1}
        # re-click retracts
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        assert (await polls.results(poll_id))["counts"] == {1: 1}


# ─── quiz ────────────────────────────────────────────────────────────────────

class TestQuiz:
    @pytest.mark.asyncio
    async def test_correct_answer_notification(self, polls):
        bot = _bot()
        poll_id = await polls.send_quiz(bot, 1, "2+2?", ["3", "4"], correct_option=1)
        await polls._on_vote(_vote_event(bot, poll_id, 1))
        note = bot.send_callback.call_args.kwargs["notification"]
        assert "Верно" in note and "Неверно" not in note

    @pytest.mark.asyncio
    async def test_wrong_answer_includes_explanation(self, polls):
        bot = _bot()
        poll_id = await polls.send_quiz(
            bot, 1, "2+2?", ["3", "4"], correct_option=1, explanation="Арифметика",
        )
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        note = bot.send_callback.call_args.kwargs["notification"]
        assert "Неверно" in note
        assert "4" in note
        assert "Арифметика" in note

    @pytest.mark.asyncio
    async def test_answer_is_final(self, polls):
        bot = _bot()
        poll_id = await polls.send_quiz(bot, 1, "2+2?", ["3", "4"], correct_option=1)
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        await polls._on_vote(_vote_event(bot, poll_id, 1))
        assert (await polls.results(poll_id))["counts"] == {0: 1}

    @pytest.mark.asyncio
    async def test_running_quiz_hides_distribution(self, polls):
        bot = _bot()
        poll_id = await polls.send_quiz(bot, 1, "2+2?", ["3", "4"], correct_option=1)
        await polls._on_vote(_vote_event(bot, poll_id, 1))
        text = bot.edit_message.call_args.kwargs["text"]
        assert "Ответили: 1" in text
        assert "%" not in text  # no bars while running

    @pytest.mark.asyncio
    async def test_closed_quiz_reveals_answer(self, polls):
        bot = _bot()
        poll_id = await polls.send_quiz(bot, 1, "2+2?", ["3", "4"], correct_option=1)
        await polls._on_vote(_vote_event(bot, poll_id, 1))
        await polls.close_poll(bot, poll_id)
        text = bot.edit_message.call_args.kwargs["text"]
        assert "✅" in text
        assert "Квиз завершён" in text


# ─── closing ─────────────────────────────────────────────────────────────────

class TestClosePoll:
    @pytest.mark.asyncio
    async def test_no_votes_after_close(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls.close_poll(bot, poll_id)
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        assert (await polls.results(poll_id))["counts"] == {}
        note = bot.send_callback.call_args.kwargs["notification"]
        assert "завершён" in note

    @pytest.mark.asyncio
    async def test_close_removes_keyboard(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls.close_poll(bot, poll_id)
        assert bot.edit_message.call_args.kwargs["keyboard"] is None

    @pytest.mark.asyncio
    async def test_close_unknown_poll(self, polls):
        assert await polls.close_poll(_bot(), "nonexistent") is None


# ─── wiring / robustness ─────────────────────────────────────────────────────

class TestAttach:
    @pytest.mark.asyncio
    async def test_attach_registers_prefixed_handler(self, polls):
        dp = Dispatcher()
        before = len(dp._callback_handlers)
        polls.attach(dp)
        assert len(dp._callback_handlers) == before + 1

    @pytest.mark.asyncio
    async def test_garbage_callback_ignored(self, polls):
        bot = _bot()
        event = _vote_event(bot, "x", "not-an-int")
        await polls._on_vote(event)  # no exception
        event.callback_data = None
        await polls._on_vote(event)  # no exception

    @pytest.mark.asyncio
    async def test_persistence_across_reopen(self, tmp_path):
        bot = _bot()
        path = tmp_path / "p.db"
        pm1 = PollManager(path)
        poll_id = await pm1.send_poll(bot, 1, "Q?", ["A", "B"])
        await pm1._on_vote(_vote_event(bot, poll_id, 0))
        await pm1.close()

        pm2 = PollManager(path)
        results = await pm2.results(poll_id)
        assert results["counts"] == {0: 1}
        await pm2.close()


# ─── visibility modes ────────────────────────────────────────────────────────

class TestVisibility:
    @pytest.mark.asyncio
    async def test_priv_hides_distribution(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(
            bot, 1, "Q?", ["A", "B"], visibility="priv", creator_id=99,
        )
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        text = bot.edit_message.call_args.kwargs["text"]
        assert "Проголосовало: 1" in text
        assert "%" not in text
        assert "только автор" in text

    @pytest.mark.asyncio
    async def test_priv_results_button_creator_only(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(
            bot, 1, "Q?", ["A", "B"], visibility="priv", creator_id=99,
        )
        await polls._on_vote(_vote_event(bot, poll_id, 0, user_id=10))
        # stranger clicks results
        await polls._on_vote(_vote_event(bot, poll_id, "res", user_id=10))
        note = bot.send_callback.call_args.kwargs["notification"]
        assert "только автору" in note
        # creator clicks results
        await polls._on_vote(_vote_event(bot, poll_id, "res", user_id=99))
        note = bot.send_callback.call_args.kwargs["notification"]
        assert "Голосов: 1" in note
        assert "A: 1" in note

    @pytest.mark.asyncio
    async def test_pub_shows_voter_names(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(
            bot, 1, "Q?", ["A", "B"], visibility="pub", creator_id=99,
        )
        await polls._on_vote(_vote_event(bot, poll_id, 0, user_id=10, name="Ivan Petrov"))
        text = bot.edit_message.call_args.kwargs["text"]
        assert "Ivan Petrov" in text
        results = await polls.results(poll_id)
        assert results["voter_names"] == {0: ["Ivan Petrov"]}

    @pytest.mark.asyncio
    async def test_anon_no_names(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"], visibility="anon")
        await polls._on_vote(_vote_event(bot, poll_id, 0, name="Ivan Petrov"))
        text = bot.edit_message.call_args.kwargs["text"]
        assert "Ivan Petrov" not in text
        assert "%" in text

    @pytest.mark.asyncio
    async def test_invalid_visibility_rejected(self, polls):
        with pytest.raises(ValueError):
            await polls.send_poll(_bot(), 1, "Q?", ["A", "B"], visibility="secret")

    @pytest.mark.asyncio
    async def test_close_button_creator_only(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(
            bot, 1, "Q?", ["A", "B"], visibility="anon", creator_id=99,
        )
        await polls._on_vote(_vote_event(bot, poll_id, "close", user_id=10))
        assert not (await polls.results(poll_id))["closed"]
        await polls._on_vote(_vote_event(bot, poll_id, "close", user_id=99))
        assert (await polls.results(poll_id))["closed"]

    @pytest.mark.asyncio
    async def test_control_buttons_in_keyboard(self, polls):
        bot = _bot()
        await polls.send_poll(bot, 1, "Q?", ["A", "B"], visibility="priv", creator_id=99)
        kb = bot.send_message.call_args.kwargs["inline_keyboard"]
        last_row = kb["payload"]["buttons"][-1]
        texts = [b["text"] for b in last_row]
        assert "📊 Результаты" in texts
        assert "⏹ Завершить" in texts

    @pytest.mark.asyncio
    async def test_no_controls_without_creator(self, polls):
        bot = _bot()
        await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        kb = bot.send_message.call_args.kwargs["inline_keyboard"]
        assert len(kb["payload"]["buttons"]) == 2  # only option rows


# ─── /poll command ───────────────────────────────────────────────────────────

class TestPollCommand:
    def test_parse_basic(self):
        parsed = PollManager.parse_command("/poll Вопрос? | да | нет")
        assert parsed == ("anon", "Вопрос?", ["да", "нет"])

    def test_parse_with_visibility(self):
        for vis in ("priv", "anon", "pub"):
            parsed = PollManager.parse_command(f"/poll {vis} В? | а | б")
            assert parsed == (vis, "В?", ["а", "б"])

    def test_parse_extra_spaces_and_empty_parts(self):
        parsed = PollManager.parse_command("/poll  pub  В?  |  а |  | б | ")
        assert parsed == ("pub", "В?", ["а", "б"])

    def test_parse_invalid(self):
        assert PollManager.parse_command("/poll") is None
        assert PollManager.parse_command("/poll Вопрос без вариантов") is None
        assert PollManager.parse_command("/poll В? | один") is None
        assert PollManager.parse_command("/other В? | а | б") is None

    @pytest.mark.asyncio
    async def test_command_handler_creates_poll_and_deletes_source(self, polls):
        bot = _bot()
        handler = polls._make_command_handler("poll")

        event = MagicMock()
        event.bot = bot
        event.text = "/poll pub В? | а | б"
        event.chat_id = 5
        event.user_id = 99
        event.answer = AsyncMock()
        event.event.message.body.mid = "mid.src"

        await handler(event)

        bot.send_message.assert_called_once()
        bot.delete_message.assert_called_once_with(message_id="mid.src")
        event.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_command_handler_usage_on_bad_syntax(self, polls):
        bot = _bot()
        handler = polls._make_command_handler("poll")
        event = MagicMock()
        event.bot = bot
        event.text = "/poll недостаточно"
        event.answer = AsyncMock()
        await handler(event)
        event.answer.assert_called_once()
        assert "Формат" in event.answer.call_args.args[0]
        bot.send_message.assert_not_called()


# ─── StateGuard integration ──────────────────────────────────────────────────

class TestI18n:
    @pytest.mark.asyncio
    async def test_notification_follows_clicker_locale(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        event = _vote_event(bot, poll_id, 0)
        event.event.user_locale = "en"
        await polls._on_vote(event)
        note = bot.send_callback.call_args.kwargs["notification"]
        assert note == "Vote counted"

    @pytest.mark.asyncio
    async def test_default_locale_is_russian(self, polls):
        bot = _bot()
        poll_id = await polls.send_poll(bot, 1, "Q?", ["A", "B"])
        await polls._on_vote(_vote_event(bot, poll_id, 0))
        note = bot.send_callback.call_args.kwargs["notification"]
        assert note == "Голос учтён"

    @pytest.mark.asyncio
    async def test_message_rendered_in_creator_locale(self, polls):
        bot = _bot()
        await polls.send_poll(bot, 1, "Q?", ["A", "B"], locale="en", creator_id=9)
        text = bot.send_message.call_args.kwargs["text"]
        assert "Total votes: 0" in text
        kb = bot.send_message.call_args.kwargs["inline_keyboard"]
        assert kb["payload"]["buttons"][-1][-1]["text"] == "⏹ Close"

    @pytest.mark.asyncio
    async def test_quiz_wrong_answer_localized(self, polls):
        bot = _bot()
        poll_id = await polls.send_quiz(bot, 1, "2+2?", ["3", "4"], correct_option=1)
        event = _vote_event(bot, poll_id, 0)
        event.event.user_locale = "en"
        await polls._on_vote(event)
        note = bot.send_callback.call_args.kwargs["notification"]
        assert "Wrong. Correct answer: 4" in note


class TestSharedDatabase:
    @pytest.mark.asyncio
    async def test_registry_and_polls_share_one_file(self, tmp_path):
        import sqlite3
        from aioscam.registry import ChatRegistry

        path = tmp_path / "bot.db"
        registry = ChatRegistry(path)
        polls = PollManager(path)
        # same underlying Database instance (path-cached)
        assert registry._db is polls._db

        await registry.upsert_chat(1, type="chat")
        await polls.send_poll(_bot(), 1, "Q?", ["A", "B"])
        await registry.close()
        await polls.close()

        conn = sqlite3.connect(path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        conn.close()
        assert {"chats", "kv", "polls", "votes"} <= tables

    @pytest.mark.asyncio
    async def test_refcounted_close(self, tmp_path):
        from aioscam.registry import ChatRegistry

        path = tmp_path / "bot.db"
        registry = ChatRegistry(path)
        polls = PollManager(path)
        await registry.upsert_chat(1, type="chat")
        await registry.close()  # polls still holds a reference
        poll_id = await polls.send_poll(_bot(), 1, "Q?", ["A", "B"])
        assert await polls.results(poll_id) is not None
        await polls.close()


class TestStateGuardIntegration:
    @pytest.mark.asyncio
    async def test_attach_extends_guard_allowlists(self, polls):
        dp = Dispatcher()
        n_cb = len(dp._guard_allowed_callbacks)
        n_cmd = len(dp._guard_allowed_commands)
        polls.attach(dp, command="poll")
        assert len(dp._guard_allowed_callbacks) == n_cb + 1
        assert "/poll" in dp._guard_allowed_commands
        # the F-filter actually matches poll payloads
        assert Dispatcher._callback_guard_allowed(
            "apoll:abc123:0", dp._guard_allowed_callbacks,
        ) is True
        assert Dispatcher._callback_guard_allowed(
            "other:payload", dp._guard_allowed_callbacks,
        ) is False

    @pytest.mark.asyncio
    async def test_attach_without_command(self, polls):
        dp = Dispatcher()
        n_cmd = len(dp._guard_allowed_commands)
        polls.attach(dp, command=None)
        assert len(dp._guard_allowed_commands) == n_cmd
