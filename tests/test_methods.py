"""
Tests for methods module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam.methods import BaseMethod, SendMessage, GetMe, GetUpdates
from aioscam.enums import HttpMethod, ApiPath, ParseMode


# ============================================================
# GetMe tests
# ============================================================

class TestGetMe:
    def test_getme_path(self):
        method = GetMe()
        assert method.path == ApiPath.GET_ME.value
        assert method.http_method == HttpMethod.GET

    def test_getme_no_params(self):
        method = GetMe()
        assert method.params is None

    def test_getme_no_body(self):
        method = GetMe()
        assert method.body is None


# ============================================================
# SendMessage tests
# ============================================================

class TestSendMessage:
    def test_sendmessage_path(self):
        method = SendMessage(chat_id=123, text="Hello")
        assert method.path == ApiPath.SEND_MESSAGE.value
        assert method.http_method == HttpMethod.POST

    def test_sendmessage_params_with_chat_id(self):
        method = SendMessage(chat_id=123, text="Hello")
        assert method.params == {"chat_id": 123}

    def test_sendmessage_params_with_user_id(self):
        method = SendMessage(user_id=456, text="Hello")
        assert method.params == {"user_id": 456}

    def test_sendmessage_params_with_both(self):
        method = SendMessage(chat_id=123, user_id=456, text="Hello")
        assert method.params == {"chat_id": 123, "user_id": 456}

    def test_sendmessage_params_none(self):
        method = SendMessage(text="Hello")
        assert method.params is None

    def test_sendmessage_body_basic(self):
        method = SendMessage(text="Hello")
        body = method.body
        assert body["text"] == "Hello"
        assert body["attachments"] == []

    def test_sendmessage_body_with_format(self):
        method = SendMessage(text="Hello", format="markdown")
        assert method.body["format"] == "markdown"

    def test_sendmessage_body_with_parse_mode(self):
        method = SendMessage(text="Hello", parse_mode=ParseMode.HTML)
        assert method.body["format"] == "html"

    def test_sendmessage_body_with_keyboard(self):
        kb = {"type": "inline_keyboard", "buttons": []}
        method = SendMessage(text="Hello", keyboard=kb)
        assert len(method.body["attachments"]) == 1
        assert method.body["attachments"][0]["type"] == "inline_keyboard"

    def test_sendmessage_body_with_regular_keyboard(self):
        kb = {"buttons": [{"text": "OK"}]}
        method = SendMessage(text="Hello", keyboard=kb)
        assert len(method.body["attachments"]) == 1
        assert method.body["attachments"][0]["type"] == "inline_keyboard"

    def test_sendmessage_body_with_reply_to(self):
        method = SendMessage(text="Hello", reply_to_mid="mid.123")
        assert method.body["link"] == {"mid": "mid.123", "type": "reply"}

    def test_sendmessage_body_with_attachments(self):
        method = SendMessage(text="Hello", attachments=[{"type": "image"}])
        assert len(method.body["attachments"]) == 1


# ============================================================
# GetUpdates tests
# ============================================================

class TestGetUpdates:
    def test_getupdates_path(self):
        method = GetUpdates()
        assert method.path == ApiPath.GET_UPDATES.value
        assert method.http_method == HttpMethod.GET

    def test_getupdates_params_default(self):
        method = GetUpdates()
        params = method.params
        assert params["limit"] == 100
        assert params["timeout"] == 30

    def test_getupdates_params_with_marker(self):
        method = GetUpdates(marker=123)
        assert method.params["marker"] == 123

    def test_getupdates_params_with_types(self):
        method = GetUpdates(types=["message_created"])
        assert method.params["types"] == ["message_created"]

    def test_getupdates_limit_capped(self):
        method = GetUpdates(limit=2000)
        assert method.params["limit"] == 1000

    def test_getupdates_timeout_capped(self):
        method = GetUpdates(timeout=120)
        assert method.params["timeout"] == 90

    def test_getupdates_no_body(self):
        method = GetUpdates()
        assert method.body is None


# ============================================================
# BaseMethod execute integration tests
# ============================================================

class TestBaseMethodExecute:
    @pytest.mark.asyncio
    async def test_getme_execute(self):
        bot = MagicMock()
        bot.client.request = AsyncMock(return_value=MagicMock(
            result={"id": 123, "username": "test_bot"}
        ))

        method = GetMe()
        result = await method.execute(bot)

        assert result == {"id": 123, "username": "test_bot"}
        bot.client.request.assert_called_once_with(
            ApiPath.GET_ME.value,
            method=HttpMethod.GET,
            params=None,
            body=None,
            timeout=None,
        )

    @pytest.mark.asyncio
    async def test_sendmessage_execute(self):
        bot = MagicMock()
        bot.client.request = AsyncMock(return_value=MagicMock(
            result={"id": 1}
        ))

        method = SendMessage(chat_id=123, text="Hello")
        result = await method.execute(bot)

        assert result == {"id": 1}
        call_kwargs = bot.client.request.call_args.kwargs
        assert call_kwargs["method"] == HttpMethod.POST
        assert call_kwargs["params"] == {"chat_id": 123}
        assert call_kwargs["body"]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_bot_execute_method(self):
        """Test Bot.execute() delegates to method.execute()"""
        from aioscam import Bot
        bot = Bot(token="test")

        mock_result = {"id": 1, "username": "test_bot"}
        bot._client.request = AsyncMock(
            return_value=MagicMock(result=mock_result)
        )

        result = await bot.execute(GetMe())

        assert result == mock_result
        await bot.close()
