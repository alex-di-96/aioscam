"""
Unit tests for Bot send methods: send_callback, send_message split,
edit_message truncate, _ensure_branding, _remove_branding.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from aioscam import Bot
from aioscam.bot.bot import MAX_TEXT_LENGTH
from aioscam.exceptions import ApiError


@pytest.fixture
def bot():
    return Bot(token="test_token")


# ─── send_message text split ────────────────────────────────────────────────

class TestSendMessageSplit:

    @pytest.mark.asyncio
    async def test_short_text_sent_once(self, bot):
        bot.execute = AsyncMock(return_value={"id": 1})
        await bot.send_message(chat_id=1, text="hello")
        assert bot.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_long_text_no_split_by_default(self, bot):
        # autosplit=False (default): long text sent as-is in one call
        long_text = "A" * (MAX_TEXT_LENGTH + 500)
        bot.execute = AsyncMock(return_value={"id": 1})
        await bot.send_message(chat_id=1, text=long_text)
        assert bot.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_long_text_split_into_chunks_with_autosplit(self, bot):
        # autosplit=True: text > 4000 chars → split into 2 calls
        long_text = "A" * (MAX_TEXT_LENGTH + 500)
        bot.execute = AsyncMock(return_value={"id": 1})
        await bot.send_message(chat_id=1, text=long_text, autosplit=True)
        assert bot.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_exactly_max_length_not_split(self, bot):
        text = "B" * MAX_TEXT_LENGTH
        bot.execute = AsyncMock(return_value={"id": 1})
        await bot.send_message(chat_id=1, text=text, autosplit=True)
        assert bot.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_three_chunks_for_very_long_text(self, bot):
        long_text = "C" * (MAX_TEXT_LENGTH * 2 + 1)
        bot.execute = AsyncMock(return_value={"id": 1})
        await bot.send_message(chat_id=1, text=long_text, autosplit=True)
        assert bot.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_keyboard_only_sent_in_last_chunk(self, bot):
        long_text = "D" * (MAX_TEXT_LENGTH + 100)
        keyboard = {"type": "inline_keyboard", "payload": {"buttons": []}}
        bot._client.request = AsyncMock(return_value=MagicMock(result={"id": 1}))
        await bot.send_message(chat_id=1, text=long_text, keyboard=keyboard,
                               autosplit=True, notify=True)
        calls = bot._client.request.call_args_list
        assert len(calls) == 2
        first_body = calls[0][1].get("body", {})
        last_body = calls[1][1].get("body", {})
        # Keyboard must be absent from first chunk, present in last
        first_atts = [a for a in first_body.get("attachments", [])
                      if a.get("type") == "inline_keyboard"]
        last_atts = [a for a in last_body.get("attachments", [])
                     if a.get("type") == "inline_keyboard"]
        assert first_atts == []
        assert len(last_atts) == 1


# ─── edit_message truncation ────────────────────────────────────────────────

class TestEditMessageTruncate:

    @pytest.mark.asyncio
    async def test_short_text_not_truncated(self, bot):
        bot._client.request = AsyncMock(return_value=MagicMock(result={"id": 1}))
        await bot.edit_message(message_id="mid.1", text="hello")
        call_args = bot._client.request.call_args
        body = call_args[1].get("body") or {}
        assert body.get("text") == "hello"

    @pytest.mark.asyncio
    async def test_long_text_truncated_with_ellipsis(self, bot):
        long_text = "E" * (MAX_TEXT_LENGTH + 100)
        bot._client.request = AsyncMock(return_value=MagicMock(result={"id": 1}))
        await bot.edit_message(message_id="mid.1", text=long_text)
        call_args = bot._client.request.call_args
        body = call_args[1].get("body") or {}
        sent_text = body.get("text", "")
        assert len(sent_text) == MAX_TEXT_LENGTH
        assert sent_text.endswith("…")

    @pytest.mark.asyncio
    async def test_exactly_max_length_not_truncated(self, bot):
        text = "F" * MAX_TEXT_LENGTH
        bot._client.request = AsyncMock(return_value=MagicMock(result={"id": 1}))
        await bot.edit_message(message_id="mid.1", text=text)
        call_args = bot._client.request.call_args
        body = call_args[1].get("body") or {}
        assert len(body.get("text", "")) == MAX_TEXT_LENGTH
        assert not body.get("text", "").endswith("…")


# ─── send_callback ──────────────────────────────────────────────────────────

class TestSendCallback:
    """
    send_callback() now uses execute(SendCallback(...)) via AioScamClient.request().
    Tests mock bot._client.request directly (not session.post).
    """

    def _ok(self, result=None):
        from aioscam.client.response import Response
        return AsyncMock(return_value=Response(ok=True, result=result or {"success": True}))

    @pytest.mark.asyncio
    async def test_authorization_header_used(self, bot):
        # Authorization is set by RequestBuilder.set_token() inside _do_request.
        # We verify the request goes to the correct absolute URL (botapi.max.ru).
        bot._client.request = self._ok()
        await bot.send_callback(callback_id="cb123", notification="ok")

        path = bot._client.request.call_args.args[0]
        assert "botapi.max.ru" in path
        assert "answers" in path
        # access_token must NOT appear in the call args
        assert "access_token" not in str(bot._client.request.call_args)

    @pytest.mark.asyncio
    async def test_empty_body_fallback_notification(self, bot):
        # No message or notification — body must contain {"notification": ""}
        bot._client.request = self._ok()
        await bot.send_callback(callback_id="cb123")

        body = bot._client.request.call_args.kwargs.get("body", {})
        assert "notification" in body

    @pytest.mark.asyncio
    async def test_message_body_sent_correctly(self, bot):
        bot._client.request = self._ok()
        await bot.send_callback(callback_id="cb123", message="Hello!")

        body = bot._client.request.call_args.kwargs.get("body", {})
        assert body.get("message", {}).get("text") == "Hello!"

    @pytest.mark.asyncio
    async def test_callback_id_in_query_params(self, bot):
        bot._client.request = self._ok()
        await bot.send_callback(callback_id="MY_CB_ID", notification="hi")

        params = bot._client.request.call_args.kwargs.get("params", {})
        assert params.get("callback_id") == "MY_CB_ID"

    @pytest.mark.asyncio
    async def test_http_error_raises_exception(self, bot):
        from aioscam.exceptions import ApiError
        bot._client.request = AsyncMock(side_effect=ApiError("HTTP 401"))
        with pytest.raises(ApiError):
            await bot.send_callback(callback_id="cb123", notification="x")

    @pytest.mark.asyncio
    async def test_notification_in_body(self, bot):
        bot._client.request = self._ok()
        await bot.send_callback(callback_id="cb123", notification="Popup!")

        body = bot._client.request.call_args.kwargs.get("body", {})
        assert body.get("notification") == "Popup!"


# ─── _ensure_branding ────────────────────────────────────────────────────────

class TestEnsureBranding:

    @pytest.mark.asyncio
    async def test_adds_tag_when_absent(self, bot):
        from aioscam import __version__
        bot.get_me = AsyncMock(return_value={"description": "My cool bot"})
        bot.set_bot_info = AsyncMock(return_value={})

        result = await bot._ensure_branding()

        assert result is True
        call_args = bot.set_bot_info.call_args
        desc = call_args.kwargs.get("description", "")
        assert f"[Powered by AioScam v{__version__}]" in desc

    @pytest.mark.asyncio
    async def test_skips_when_already_branded(self, bot):
        from aioscam import __version__
        tag = f"[Powered by AioScam v{__version__}]"
        bot.get_me = AsyncMock(return_value={"description": f"My bot\n\n{tag}"})
        bot.set_bot_info = AsyncMock(return_value={})

        result = await bot._ensure_branding()

        assert result is False
        bot.set_bot_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_replaces_old_version_tag(self, bot):
        from aioscam import __version__
        bot.get_me = AsyncMock(return_value={
            "description": "My bot\n\n[Powered by AioScam v0.0.1]"
        })
        bot.set_bot_info = AsyncMock(return_value={})
        bot._me = None

        result = await bot._ensure_branding()

        assert result is True
        call_args = bot.set_bot_info.call_args
        new_desc = call_args.kwargs.get("description", "")
        assert "v0.0.1" not in new_desc
        assert f"v{__version__}" in new_desc

    @pytest.mark.asyncio
    async def test_empty_description(self, bot):
        from aioscam import __version__
        bot.get_me = AsyncMock(return_value={"description": ""})
        bot.set_bot_info = AsyncMock(return_value={})

        result = await bot._ensure_branding()

        assert result is True
        call_args = bot.set_bot_info.call_args
        new_desc = call_args.kwargs.get("description", "")
        assert new_desc == f"[Powered by AioScam v{__version__}]"

    @pytest.mark.asyncio
    async def test_force_updates_even_if_current(self, bot):
        from aioscam import __version__
        tag = f"[Powered by AioScam v{__version__}]"
        bot.get_me = AsyncMock(return_value={"description": f"My bot\n\n{tag}"})
        bot.set_bot_info = AsyncMock(return_value={})

        result = await bot._ensure_branding(force=True)

        assert result is True
        bot.set_bot_info.assert_called_once()


# ─── _remove_branding ────────────────────────────────────────────────────────

class TestRemoveBranding:

    @pytest.mark.asyncio
    async def test_removes_existing_tag(self, bot):
        bot.get_me = AsyncMock(return_value={
            "description": "My bot\n\n[Powered by AioScam v0.1.5]"
        })
        bot.set_bot_info = AsyncMock(return_value={})

        result = await bot._remove_branding()

        assert result is True
        call_args = bot.set_bot_info.call_args
        new_desc = call_args.kwargs.get("description", "")
        assert "[Powered by AioScam" not in new_desc
        assert "My bot" in new_desc

    @pytest.mark.asyncio
    async def test_returns_false_when_no_tag(self, bot):
        bot.get_me = AsyncMock(return_value={"description": "Clean description"})
        bot.set_bot_info = AsyncMock(return_value={})

        result = await bot._remove_branding()

        assert result is False
        bot.set_bot_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleans_trailing_newlines(self, bot):
        bot.get_me = AsyncMock(return_value={
            "description": "My bot\n\n[Powered by AioScam v0.1.0]\n\n"
        })
        bot.set_bot_info = AsyncMock(return_value={})

        await bot._remove_branding()

        call_args = bot.set_bot_info.call_args
        new_desc = call_args.kwargs.get("description", "")
        assert not new_desc.endswith("\n")
