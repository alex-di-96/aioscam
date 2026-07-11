"""
PollManager — polls and quizzes for Max bots

Max Bot API has no native poll support (unlike Telegram): none of the official
SDKs expose a poll attachment or poll methods, and every "poll bot" in the Max
catalog emulates polls with inline keyboards. PollManager gives AioScam users
that emulation out of the box, aiogram-style:

- polls: single- or multiple-choice, live result bars in the message text;
- quizzes: one correct option, per-user "correct/wrong" callback notification
  with optional explanation, correct answer revealed on close;
- votes persisted in SQLite (survives restarts), one shared handler wired
  through a normal callback filter so user handlers are unaffected.

Visibility modes:
    pub  — result bars + full names of voters under each option
    anon — result bars, aggregate numbers only (default)
    priv — the message shows only the total; the creator reads the breakdown
           via the "📊 Результаты" button (callback notifications are private)

Hint strings (notifications, labels, buttons) are localized via bundled
ru/en locales; the clicker's client locale drives notifications, the poll
creator's locale drives the shared message text. Poll content itself
(question/options) is written by the user and never translated.

Usage:
    from aioscam.polls import PollManager

    polls = PollManager()           # ./.aioscam/bot.db — общая база бота,
                                    # та же, что у ChatRegistry
    polls.attach(dp, command="poll")  # vote handler + /poll command
                                      # + StateGuard allowlist entries

    # users create polls right from the chat:
    #   /poll Вопрос? | вариант 1 | вариант 2
    #   /poll pub Вопрос? | да | нет      (priv | anon | pub)
    # the /poll source message is deleted when the bot has permission

    # or programmatically:
    await polls.send_poll(bot, chat_id, "Вопрос?", ["да", "нет"],
                          visibility="pub", creator_id=admin_id)
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from aioscam.db import DEFAULT_DB_PATH, Database
from aioscam.filters import Command, F
from aioscam.i18n import I18n

logger = logging.getLogger(__name__)

VISIBILITIES = ("priv", "anon", "pub")

_LOCALES_DIR = Path(__file__).parent / "locales"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS polls (
    poll_id TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    mid TEXT,
    question TEXT NOT NULL,
    options TEXT NOT NULL,
    multiple INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL DEFAULT 'anon',
    creator_id INTEGER,
    locale TEXT,
    quiz_correct INTEGER,
    explanation TEXT,
    closed INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS votes (
    poll_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    option_idx INTEGER NOT NULL,
    user_name TEXT,
    voted_at REAL NOT NULL,
    PRIMARY KEY (poll_id, user_id, option_idx)
);
"""

_BAR_FULL = "▓"
_BAR_EMPTY = "░"
_BAR_WIDTH = 10


class PollManager:
    """SQLite-backed poll/quiz engine on top of inline keyboards."""

    PREFIX = "apoll"

    def __init__(
        self,
        path: Union[str, Path] = DEFAULT_DB_PATH,
        i18n: Optional[I18n] = None,
        default_locale: str = "ru",
    ):
        """
        Args:
            path: Bot database path (shared with ChatRegistry by default)
            i18n: Custom I18n for hint strings; bundled ru/en locales are used
                  when omitted. Poll content (question/options) is never
                  translated — only system hints and buttons.
            default_locale: Fallback locale for hints (default "ru")
        """
        # Shared bot database — same file as ChatRegistry unless overridden
        self._db = Database.open(path)
        self._started = False
        self._i18n = i18n or I18n(path=str(_LOCALES_DIR), default_locale=default_locale)

    # ==================== lifecycle / db ====================

    async def start(self) -> None:
        if self._started:
            return
        await self._db.executescript(_SCHEMA)
        self._started = True
        logger.info(f"PollManager started: {self._db.path}")

    async def close(self) -> None:
        await self._db.close()
        self._started = False

    async def _execute(self, sql: str, params: tuple = ()) -> list:
        if not self._started:
            await self.start()
        return await self._db.execute(sql, params)

    def _t(self, event_or_locale: Any, key: str, **kwargs: Any) -> str:
        """Hint string: by event (clicker's client locale) or explicit locale."""
        if isinstance(event_or_locale, str) or event_or_locale is None:
            return self._i18n.translate(event_or_locale, key, **kwargs)
        return self._i18n.gettext(event_or_locale, key, **kwargs)

    # ==================== wiring ====================

    def attach(self, router: Any, command: Optional[str] = "poll") -> None:
        """
        Register the vote handler on a Router/Dispatcher, and (optionally)
        the /poll chat command. The callback filter matches only this
        manager's prefix, so other callback handlers are untouched
        (router dispatch is first-match).

        On a Dispatcher, poll callbacks and the command are also added to the
        StateGuard allowlists: a user stuck in an FSM dialog can still vote
        (FSM state is scoped per chat+user, but without this their own clicks
        on poll buttons would be swallowed by the guard).

        Args:
            router: Router or Dispatcher
            command: Chat command name for creating polls ("poll" →
                     "/poll [priv|anon|pub] Вопрос | вар1 | вар2").
                     Pass None to skip command registration.
        """
        router.callback_query(
            F.callback_data.startswith(f"{self.PREFIX}:")
        )(self._on_vote)

        guard_callbacks = getattr(router, "_guard_allowed_callbacks", None)
        if isinstance(guard_callbacks, list):
            guard_callbacks.append(F.startswith(f"{self.PREFIX}:"))

        if command:
            router.message_created(Command(command))(self._make_command_handler(command))
            guard_commands = getattr(router, "_guard_allowed_commands", None)
            if isinstance(guard_commands, list):
                guard_commands.append(f"/{command}")

    # ==================== /poll command ====================

    @staticmethod
    def parse_command(text: str, command: str = "poll") -> Optional[Tuple[str, str, List[str]]]:
        """
        Parse "/poll [priv|anon|pub] Вопрос | вар1 | вар2 [| ...]".

        Returns:
            (visibility, question, options) or None if the syntax is invalid.
        """
        if not text:
            return None
        body = text.strip()
        prefix = f"/{command}"
        if not body.startswith(prefix):
            return None
        body = body[len(prefix):].strip()

        visibility = "anon"
        first_word = body.split(" ", 1)[0].lower() if body else ""
        if first_word in VISIBILITIES:
            visibility = first_word
            body = body[len(first_word):].strip()

        parts = [p.strip() for p in body.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 3:  # question + at least 2 options
            return None
        return visibility, parts[0], parts[1:]

    def _make_command_handler(self, command: str):
        async def _cmd_poll(event: Any) -> None:
            parsed = self.parse_command(event.text or "", command)
            if parsed is None:
                await event.answer(self._t(event, "poll_usage", command=command))
                return
            visibility, question, options = parsed
            if len(options) > 10:
                await event.answer(self._t(event, "poll_max_options"))
                return

            await self.send_poll(
                event.bot,
                event.chat_id,
                question,
                options,
                visibility=visibility,
                creator_id=event.user_id,
                user_id=event.user_id,
                # poll message hints follow the creator's client language
                locale=self._i18n.get_locale(event),
            )

            # Tidy up: drop the /poll source message (needs "delete"
            # permission in groups — silently keep it otherwise)
            mid = self._event_mid(event)
            if mid:
                try:
                    await event.bot.delete_message(message_id=mid)
                except Exception as e:
                    logger.debug(f"/{command} source message not deleted: {e}")

        return _cmd_poll

    @staticmethod
    def _event_mid(event: Any) -> Optional[str]:
        message = getattr(getattr(event, "event", None), "message", None)
        body = getattr(message, "body", None)
        return getattr(body, "mid", None)

    # ==================== sending ====================

    async def send_poll(
        self,
        bot: Any,
        chat_id: Union[int, str],
        question: str,
        options: List[str],
        multiple: bool = False,
        visibility: str = "anon",
        creator_id: Optional[int] = None,
        user_id: Optional[int] = None,
        locale: Optional[str] = None,
    ) -> str:
        """
        Send a poll message. Returns poll_id.

        Args:
            bot: Bot instance
            chat_id: Target chat
            question: Poll question
            options: 2..10 answer options
            multiple: Allow choosing several options (toggle on re-click)
            visibility: "priv" — results via creator-only button;
                        "anon" — aggregate bars (default);
                        "pub" — bars + voter names
            creator_id: Poll owner: sees priv results, can close via button
            user_id: Recipient user id (required by Max for dialogs)
            locale: Language of the poll message's hint strings (labels,
                    buttons) — usually the creator's client locale
        """
        if visibility not in VISIBILITIES:
            raise ValueError(f"visibility must be one of {VISIBILITIES}, got {visibility!r}")
        return await self._send(
            bot, chat_id, question, options,
            multiple=multiple, visibility=visibility, creator_id=creator_id,
            quiz_correct=None, explanation=None, user_id=user_id, locale=locale,
        )

    async def send_quiz(
        self,
        bot: Any,
        chat_id: Union[int, str],
        question: str,
        options: List[str],
        correct_option: int,
        explanation: Optional[str] = None,
        creator_id: Optional[int] = None,
        user_id: Optional[int] = None,
        locale: Optional[str] = None,
    ) -> str:
        """
        Send a quiz: exactly one correct option, single answer per user,
        instant correct/wrong feedback via callback notification.
        Quizzes are always anonymous.
        """
        if not 0 <= correct_option < len(options):
            raise ValueError(f"correct_option {correct_option} out of range for {len(options)} options")
        return await self._send(
            bot, chat_id, question, options,
            multiple=False, visibility="anon", creator_id=creator_id,
            quiz_correct=correct_option, explanation=explanation, user_id=user_id,
            locale=locale,
        )

    async def _send(
        self,
        bot: Any,
        chat_id: Union[int, str],
        question: str,
        options: List[str],
        multiple: bool,
        visibility: str,
        creator_id: Optional[int],
        quiz_correct: Optional[int],
        explanation: Optional[str],
        user_id: Optional[int],
        locale: Optional[str] = None,
    ) -> str:
        if len(options) < 2:
            raise ValueError("Poll needs at least 2 options")
        if len(options) > 10:
            raise ValueError("Poll supports at most 10 options")

        locale = locale or self._i18n.default_locale
        poll_id = uuid.uuid4().hex[:12]
        poll = {
            "poll_id": poll_id,
            "question": question,
            "options": options,
            "multiple": multiple,
            "visibility": visibility,
            "creator_id": creator_id,
            "locale": locale,
            "quiz_correct": quiz_correct,
            "closed": 0,
        }

        text = self._render_text(poll, {})
        keyboard = self._render_keyboard(poll)

        result = await bot.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=text,
            inline_keyboard=keyboard,
        )
        mid = None
        if isinstance(result, dict):
            mid = (result.get("message") or {}).get("body", {}).get("mid")

        await self._execute(
            "INSERT INTO polls (poll_id, chat_id, mid, question, options, multiple, "
            "visibility, creator_id, locale, quiz_correct, explanation, closed, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?)",
            (
                poll_id, chat_id, mid, question,
                json.dumps(options, ensure_ascii=False),
                int(multiple), visibility, creator_id, locale,
                quiz_correct, explanation, time.time(),
            ),
        )
        return poll_id

    # ==================== voting ====================

    async def _on_vote(self, event: Any) -> None:
        """Callback handler for apoll:<poll_id>:<action> buttons."""
        data = event.callback_data or ""
        try:
            _, poll_id, action = data.split(":", 2)
        except (ValueError, AttributeError):
            return

        user_id = event.user_id
        callback_id = getattr(event, "callback_id", None)

        async def notify(text: str) -> None:
            if callback_id:
                try:
                    await event.bot.send_callback(callback_id=callback_id, notification=text)
                except Exception as e:
                    logger.warning(f"Poll vote notification failed: {e}")

        poll = await self._get_poll(poll_id)
        if poll is None or user_id is None:
            await notify(self._t(event, "poll_not_found"))
            return

        # Control buttons work on open AND closed polls
        if action == "res":
            if poll["creator_id"] is not None and user_id == poll["creator_id"]:
                await notify(await self._creator_summary(poll, event))
            else:
                await notify(self._t(event, "poll_results_creator_only"))
            return
        if action == "close":
            if poll["creator_id"] is not None and user_id == poll["creator_id"]:
                await self.close_poll(event.bot, poll_id)
                await notify(self._t(event, "poll_closed"))
            else:
                await notify(self._t(event, "poll_close_creator_only"))
            return

        try:
            option_idx = int(action)
        except ValueError:
            return

        if poll["closed"]:
            await notify(self._t(event, "poll_closed"))
            return
        options = poll["options"]
        if not 0 <= option_idx < len(options):
            await notify(self._t(event, "poll_invalid_option"))
            return
        user_name = self._display_name(getattr(event, "from_user", None))

        existing = await self._execute(
            "SELECT option_idx FROM votes WHERE poll_id=? AND user_id=?",
            (poll_id, user_id),
        )
        chosen = {row["option_idx"] for row in existing}

        if poll["quiz_correct"] is not None:
            # Quiz: one answer, forever
            if chosen:
                await notify(self._t(event, "poll_already_answered"))
                return
            await self._execute(
                "INSERT INTO votes (poll_id, user_id, option_idx, user_name, voted_at) VALUES (?,?,?,?,?)",
                (poll_id, user_id, option_idx, user_name, time.time()),
            )
            correct = poll["quiz_correct"]
            if option_idx == correct:
                await notify(self._t(event, "poll_quiz_correct"))
            else:
                note = self._t(event, "poll_quiz_wrong", answer=options[correct])
                if poll["explanation"]:
                    note += f"\n{poll['explanation']}"
                await notify(note)
        elif poll["multiple"]:
            # Multiple choice: toggle
            if option_idx in chosen:
                await self._execute(
                    "DELETE FROM votes WHERE poll_id=? AND user_id=? AND option_idx=?",
                    (poll_id, user_id, option_idx),
                )
                await notify(self._t(event, "poll_vote_retracted"))
            else:
                await self._execute(
                    "INSERT INTO votes (poll_id, user_id, option_idx, user_name, voted_at) VALUES (?,?,?,?,?)",
                    (poll_id, user_id, option_idx, user_name, time.time()),
                )
                await notify(self._t(event, "poll_vote_counted"))
        else:
            # Single choice: move the vote
            if chosen == {option_idx}:
                await notify(self._t(event, "poll_already_voted_option"))
                return
            await self._execute(
                "DELETE FROM votes WHERE poll_id=? AND user_id=?", (poll_id, user_id),
            )
            await self._execute(
                "INSERT INTO votes (poll_id, user_id, option_idx, user_name, voted_at) VALUES (?,?,?,?,?)",
                (poll_id, user_id, option_idx, user_name, time.time()),
            )
            await notify(self._t(event, "poll_vote_counted"))

        await self._refresh_message(event.bot, poll_id)

    # ==================== results / closing ====================

    async def results(self, poll_id: str) -> Optional[Dict[str, Any]]:
        """Poll state + per-option counts + total unique voters."""
        poll = await self._get_poll(poll_id)
        if poll is None:
            return None
        counts = await self._counts(poll_id)
        voters = await self._execute(
            "SELECT COUNT(DISTINCT user_id) AS n FROM votes WHERE poll_id=?", (poll_id,),
        )
        poll["counts"] = counts
        poll["total_voters"] = voters[0]["n"] if voters else 0
        if poll.get("visibility") == "pub":
            poll["voter_names"] = await self._voter_names(poll_id)
        return poll

    async def close_poll(self, bot: Any, poll_id: str) -> Optional[Dict[str, Any]]:
        """
        Close a poll: no more votes, keyboard removed, final results rendered
        (a quiz reveals its correct answer). Returns final results.
        """
        poll = await self._get_poll(poll_id)
        if poll is None:
            return None
        await self._execute("UPDATE polls SET closed=1 WHERE poll_id=?", (poll_id,))
        await self._refresh_message(bot, poll_id)
        return await self.results(poll_id)

    # ==================== internals ====================

    async def _get_poll(self, poll_id: str) -> Optional[Dict[str, Any]]:
        rows = await self._execute("SELECT * FROM polls WHERE poll_id=?", (poll_id,))
        if not rows:
            return None
        poll = dict(rows[0])
        poll["options"] = json.loads(poll["options"])
        return poll

    async def _counts(self, poll_id: str) -> Dict[int, int]:
        rows = await self._execute(
            "SELECT option_idx, COUNT(*) AS n FROM votes WHERE poll_id=? GROUP BY option_idx",
            (poll_id,),
        )
        return {row["option_idx"]: row["n"] for row in rows}

    async def _refresh_message(self, bot: Any, poll_id: str) -> None:
        poll = await self._get_poll(poll_id)
        if poll is None or not poll.get("mid"):
            return
        counts = await self._counts(poll_id)
        names = await self._voter_names(poll_id) if poll.get("visibility") == "pub" else {}
        text = self._render_text(poll, counts, names)
        keyboard = None if poll["closed"] else self._render_keyboard(poll)
        try:
            await bot.edit_message(
                message_id=poll["mid"],
                text=text,
                keyboard=keyboard,
            )
        except Exception as e:
            logger.warning(f"Poll message refresh failed ({poll_id}): {e}")

    async def _voter_names(self, poll_id: str) -> Dict[int, List[str]]:
        rows = await self._execute(
            "SELECT option_idx, user_name FROM votes WHERE poll_id=? ORDER BY voted_at",
            (poll_id,),
        )
        names: Dict[int, List[str]] = {}
        for row in rows:
            names.setdefault(row["option_idx"], []).append(row["user_name"] or "аноним")
        return names

    async def _creator_summary(self, poll: Dict[str, Any], event: Any = None) -> str:
        """Compact per-option breakdown for the priv results notification."""
        counts = await self._counts(poll["poll_id"])
        total = sum(counts.values())
        lines = [self._t(event or poll.get("locale"), "poll_summary_total", n=total)]
        for idx, opt in enumerate(poll["options"]):
            n = counts.get(idx, 0)
            share = round(n / total * 100) if total else 0
            lines.append(f"{opt}: {n} ({share}%)")
        return "\n".join(lines)

    @staticmethod
    def _display_name(user: Any) -> Optional[str]:
        """Human-readable name from a User object or raw callback.user dict."""
        if user is None:
            return None
        if isinstance(user, dict):
            first = user.get("first_name") or ""
            last = user.get("last_name") or ""
            name = user.get("name") or user.get("display_name")
        else:
            first = getattr(user, "first_name", None) or ""
            last = getattr(user, "last_name", None) or ""
            name = getattr(user, "display_name", None) or getattr(user, "name", None)
        full = f"{first} {last}".strip()
        return full or name or None

    def _render_keyboard(self, poll: Dict[str, Any]) -> Dict[str, Any]:
        poll_id = poll["poll_id"]
        buttons = [
            [{
                "type": "callback",
                "text": opt if len(opt) <= 36 else opt[:35] + "…",
                "payload": f"{self.PREFIX}:{poll_id}:{idx}",
            }]
            for idx, opt in enumerate(poll["options"])
        ]
        locale = poll.get("locale")
        controls = []
        if poll.get("visibility") == "priv" and poll.get("creator_id") is not None:
            controls.append({
                "type": "callback", "text": self._t(locale, "poll_results_btn"),
                "payload": f"{self.PREFIX}:{poll_id}:res",
            })
        if poll.get("creator_id") is not None:
            controls.append({
                "type": "callback", "text": self._t(locale, "poll_close_btn"),
                "payload": f"{self.PREFIX}:{poll_id}:close",
            })
        if controls:
            buttons.append(controls)
        return {"type": "inline_keyboard", "payload": {"buttons": buttons}}

    @staticmethod
    def _bar(share: float) -> str:
        filled = round(share * _BAR_WIDTH)
        return _BAR_FULL * filled + _BAR_EMPTY * (_BAR_WIDTH - filled)

    def _render_text(
        self,
        poll: Dict[str, Any],
        counts: Dict[int, int],
        names: Optional[Dict[int, List[str]]] = None,
    ) -> str:
        is_quiz = poll.get("quiz_correct") is not None
        closed = bool(poll.get("closed"))
        visibility = poll.get("visibility", "anon")
        locale = poll.get("locale")
        options: List[str] = poll["options"]
        total_votes = sum(counts.values())

        header = "🧠 " if is_quiz else "📊 "
        lines = [header + poll["question"], ""]

        hide_distribution = (is_quiz and not closed) or (visibility == "priv" and not is_quiz)
        if hide_distribution:
            # Quizzes hide the answer split while running; priv polls hide it
            # from everyone — the creator reads it via the results button
            key = "poll_answered_count" if is_quiz else "poll_voted_count"
            lines.append(self._t(locale, key, n=total_votes))
            if visibility == "priv" and not is_quiz:
                lines.append(self._t(locale, "poll_priv_note"))
        else:
            for idx, opt in enumerate(options):
                n = counts.get(idx, 0)
                share = (n / total_votes) if total_votes else 0.0
                mark = " ✅" if (is_quiz and closed and idx == poll["quiz_correct"]) else ""
                lines.append(f"{self._bar(share)} {round(share * 100)}% ({n}) {opt}{mark}")
                if visibility == "pub" and names:
                    voters = names.get(idx, [])
                    if voters:
                        shown = ", ".join(voters[:10])
                        if len(voters) > 10:
                            shown += self._t(locale, "poll_more_voters", n=len(voters) - 10)
                        lines.append(f"    👥 {shown}")
            lines.append("")
            lines.append(self._t(locale, "poll_total_votes", n=total_votes))

        if closed:
            lines.append(self._t(locale, "quiz_finished" if is_quiz else "poll_finished"))
            if is_quiz and poll.get("explanation"):
                lines.append(f"💡 {poll['explanation']}")
        elif poll.get("multiple"):
            lines.append(self._t(locale, "poll_multiple_note"))

        return "\n".join(lines)
