"""
Unit tests for all previously uncovered Bot API methods:
chat management, members, admins, pin, webhooks, media upload/download,
get_last_marker, get_me_from_chat, get_upload_url.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aioscam import Bot
from aioscam.client.response import Response
from aioscam.enums import HttpMethod


def _bot(result=None, ok=True):
    """Return a Bot with mocked client.request."""
    bot = Bot(token="test_token")
    bot._client.request = AsyncMock(
        return_value=Response(ok=ok, result=result or {})
    )
    return bot


def _last_call(bot):
    return bot._client.request.call_args


# ─── get_me_from_chat ────────────────────────────────────────────────────────

class TestGetMeFromChat:
    @pytest.mark.asyncio
    async def test_returns_result(self):
        bot = _bot(result={"name": "MyBot"})
        result = await bot.get_me_from_chat(chat_id=42)
        assert result == {"name": "MyBot"}

    @pytest.mark.asyncio
    async def test_passes_chat_id(self):
        bot = _bot()
        await bot.get_me_from_chat(chat_id=99)
        params = _last_call(bot).kwargs.get("params", {})
        assert params["chat_id"] == 99

    @pytest.mark.asyncio
    async def test_uses_get_method(self):
        bot = _bot()
        await bot.get_me_from_chat(chat_id=1)
        method = _last_call(bot).kwargs.get("method")
        assert method == HttpMethod.GET


# ─── Chat methods ─────────────────────────────────────────────────────────────

class TestGetChats:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        bot = _bot(result=[{"id": 1}, {"id": 2}])
        result = await bot.get_chats()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_none_result_returns_empty(self):
        bot = _bot(result=None)
        result = await bot.get_chats()
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_get_method(self):
        bot = _bot()
        await bot.get_chats()
        assert _last_call(bot).kwargs.get("method") == HttpMethod.GET


class TestGetChatById:
    @pytest.mark.asyncio
    async def test_passes_id(self):
        bot = _bot(result={"chat_id": 7})
        await bot.get_chat_by_id(id=7)
        params = _last_call(bot).kwargs.get("params", {})
        assert params["id"] == 7

    @pytest.mark.asyncio
    async def test_uses_get_method(self):
        bot = _bot()
        await bot.get_chat_by_id(id=1)
        assert _last_call(bot).kwargs.get("method") == HttpMethod.GET


class TestGetChatByLink:
    @pytest.mark.asyncio
    async def test_passes_link(self):
        bot = _bot(result={"chat_id": 5})
        await bot.get_chat_by_link(link="https://max.ru/group/abc")
        params = _last_call(bot).kwargs.get("params", {})
        assert params["link"] == "https://max.ru/group/abc"


class TestEditChat:
    @pytest.mark.asyncio
    async def test_sends_title(self):
        bot = _bot(result={"chat_id": 1})
        await bot.edit_chat(chat_id=1, title="New Title")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_sends_description(self):
        bot = _bot()
        await bot.edit_chat(chat_id=1, description="desc")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["description"] == "desc"

    @pytest.mark.asyncio
    async def test_empty_title_not_sent(self):
        bot = _bot()
        await bot.edit_chat(chat_id=1)
        body = _last_call(bot).kwargs.get("body", {})
        assert "title" not in body

    @pytest.mark.asyncio
    async def test_kwargs_forwarded(self):
        bot = _bot()
        await bot.edit_chat(chat_id=1, icon={"type": "emoji"})
        body = _last_call(bot).kwargs.get("body", {})
        assert body["icon"] == {"type": "emoji"}


class TestDeleteChat:
    @pytest.mark.asyncio
    async def test_returns_ok(self):
        bot = _bot()
        result = await bot.delete_chat(chat_id=10)
        assert result is True

    @pytest.mark.asyncio
    async def test_passes_chat_id_in_body(self):
        bot = _bot()
        await bot.delete_chat(chat_id=42)
        body = _last_call(bot).kwargs.get("body", {})
        assert body["chat_id"] == 42


# ─── Chat members ─────────────────────────────────────────────────────────────

class TestGetChatMembers:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        bot = _bot(result=[{"id": 1}])
        result = await bot.get_chat_members(chat_id=5)
        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_none_result_returns_empty(self):
        bot = _bot(result=None)
        result = await bot.get_chat_members(chat_id=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_chat_id(self):
        bot = _bot()
        await bot.get_chat_members(chat_id=7)
        params = _last_call(bot).kwargs.get("params", {})
        assert params["chat_id"] == 7

    @pytest.mark.asyncio
    async def test_alias_get_members_chat(self):
        bot = _bot(result=[])
        result = await bot.get_members_chat(chat_id=1)
        assert result == []


class TestGetChatMember:
    @pytest.mark.asyncio
    async def test_passes_chat_and_user_id(self):
        bot = _bot(result={"id": 99})
        await bot.get_chat_member(chat_id=1, user_id=99)
        params = _last_call(bot).kwargs.get("params", {})
        assert params["chat_id"] == 1
        assert params["user_id"] == 99

    @pytest.mark.asyncio
    async def test_returns_result(self):
        bot = _bot(result={"id": 99, "role": "admin"})
        result = await bot.get_chat_member(chat_id=1, user_id=99)
        assert result["role"] == "admin"


class TestAddChatMembers:
    @pytest.mark.asyncio
    async def test_passes_user_ids(self):
        bot = _bot(result={"added": 2})
        await bot.add_chat_members(chat_id=1, user_ids=[10, 20])
        body = _last_call(bot).kwargs.get("body", {})
        assert body["user_ids"] == [10, 20]
        assert body["chat_id"] == 1

    @pytest.mark.asyncio
    async def test_alias_add_members_chat(self):
        bot = _bot(result={})
        await bot.add_members_chat(chat_id=1, user_ids=[5])
        body = _last_call(bot).kwargs.get("body", {})
        assert body["chat_id"] == 1


class TestRemoveMemberChat:
    @pytest.mark.asyncio
    async def test_returns_ok(self):
        bot = _bot()
        result = await bot.remove_member_chat(chat_id=1, user_id=99)
        assert result is True

    @pytest.mark.asyncio
    async def test_alias_kick(self):
        bot = _bot()
        result = await bot.kick_chat_member(chat_id=1, user_id=99)
        assert result is True


# ─── Admins ───────────────────────────────────────────────────────────────────

class TestGetListAdminChat:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        bot = _bot(result=[{"id": 1}])
        result = await bot.get_list_admin_chat(chat_id=5)
        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_none_returns_empty(self):
        bot = _bot(result=None)
        result = await bot.get_list_admin_chat(chat_id=5)
        assert result == []


class TestAddListAdminChat:
    @pytest.mark.asyncio
    async def test_passes_permissions(self):
        bot = _bot(result={})
        await bot.add_list_admin_chat(
            chat_id=1, user_id=99,
            can_change_info=True, can_invite=False
        )
        body = _last_call(bot).kwargs.get("body", {})
        assert body["can_change_info"] is True
        assert body["can_invite"] is False

    @pytest.mark.asyncio
    async def test_skips_none_permissions(self):
        bot = _bot(result={})
        await bot.add_list_admin_chat(chat_id=1, user_id=99)
        body = _last_call(bot).kwargs.get("body", {})
        assert "can_change_info" not in body
        assert "can_invite" not in body


class TestRemoveAdmin:
    @pytest.mark.asyncio
    async def test_returns_ok(self):
        bot = _bot()
        result = await bot.remove_admin(chat_id=1, user_id=99)
        assert result is True

    @pytest.mark.asyncio
    async def test_passes_ids_in_body(self):
        bot = _bot()
        await bot.remove_admin(chat_id=5, user_id=7)
        body = _last_call(bot).kwargs.get("body", {})
        assert body["chat_id"] == 5
        assert body["user_id"] == 7


# ─── change_info ──────────────────────────────────────────────────────────────

class TestChangeInfo:
    @pytest.mark.asyncio
    async def test_passes_title(self):
        bot = _bot(result={})
        await bot.change_info(chat_id=1, title="New")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["title"] == "New"

    @pytest.mark.asyncio
    async def test_empty_fields_not_included(self):
        bot = _bot(result={})
        await bot.change_info(chat_id=1)
        body = _last_call(bot).kwargs.get("body", {})
        assert "title" not in body
        assert "description" not in body


# ─── Pin / Unpin ──────────────────────────────────────────────────────────────

class TestPinMessage:
    @pytest.mark.asyncio
    async def test_passes_ids(self):
        bot = _bot(result={"pinned": True})
        await bot.pin_message(chat_id=1, message_id="mid.1")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["chat_id"] == 1
        assert body["message_id"] == "mid.1"

    @pytest.mark.asyncio
    async def test_notify_included_when_set(self):
        bot = _bot(result={})
        await bot.pin_message(chat_id=1, message_id="mid.2", notify=True)
        body = _last_call(bot).kwargs.get("body", {})
        assert body["notify"] is True

    @pytest.mark.asyncio
    async def test_notify_absent_when_none(self):
        bot = _bot(result={})
        await bot.pin_message(chat_id=1, message_id="mid.3")
        body = _last_call(bot).kwargs.get("body", {})
        assert "notify" not in body


class TestGetPinMessage:
    @pytest.mark.asyncio
    async def test_returns_result(self):
        bot = _bot(result={"id": "mid.pin"})
        result = await bot.get_pin_message(chat_id=5)
        assert result == {"id": "mid.pin"}

    @pytest.mark.asyncio
    async def test_passes_chat_id(self):
        bot = _bot()
        await bot.get_pin_message(chat_id=77)
        params = _last_call(bot).kwargs.get("params", {})
        assert params["chat_id"] == 77

    @pytest.mark.asyncio
    async def test_alias_get_pinned_message(self):
        bot = _bot(result={"ok": True})
        result = await bot.get_pinned_message(chat_id=1)
        assert result == {"ok": True}


# ─── Webhook subscriptions ────────────────────────────────────────────────────

class TestSubscribeWebhook:
    @pytest.mark.asyncio
    async def test_passes_url(self):
        bot = _bot(result={"subscribed": True})
        await bot.subscribe_webhook(url="https://example.com/webhook")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_kwargs_forwarded(self):
        bot = _bot(result={})
        await bot.subscribe_webhook(url="https://example.com/wh", version="1.0")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["version"] == "1.0"


class TestUnsubscribeWebhook:
    @pytest.mark.asyncio
    async def test_passes_url_in_body(self):
        bot = _bot()
        await bot.unsubscribe_webhook(url="https://example.com/webhook")
        body = _last_call(bot).kwargs.get("body", {})
        assert body["url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_returns_ok(self):
        bot = _bot()
        result = await bot.unsubscribe_webhook(url="https://example.com/wh")
        assert result is True


class TestGetSubscriptions:
    @pytest.mark.asyncio
    async def test_extracts_subscriptions_list(self):
        bot = _bot(result={"subscriptions": ["https://a.com", "https://b.com"]})
        result = await bot.get_subscriptions()
        assert result == ["https://a.com", "https://b.com"]

    @pytest.mark.asyncio
    async def test_empty_subscriptions(self):
        bot = _bot(result={})
        result = await bot.get_subscriptions()
        assert result == []

    @pytest.mark.asyncio
    async def test_none_result_returns_empty(self):
        bot = _bot(result=None)
        result = await bot.get_subscriptions()
        assert result == []


# ─── Media: get_upload_url / get_video ───────────────────────────────────────

class TestGetUploadUrl:
    @pytest.mark.asyncio
    async def test_returns_url_dict(self):
        from aioscam.types.attachment import UploadType
        bot = _bot(result={"url": "https://upload.max.ru/...", "token": "tok123"})
        result = await bot.get_upload_url(UploadType.IMAGE)
        assert result["url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_passes_type_as_query_param(self):
        from aioscam.types.attachment import UploadType
        bot = _bot(result={"url": "https://upload.max.ru/..."})
        await bot.get_upload_url(UploadType.VIDEO)
        params = _last_call(bot).kwargs.get("params", {})
        assert params["type"] == "video"

    @pytest.mark.asyncio
    async def test_accepts_string_type(self):
        bot = _bot(result={"url": "https://upload.max.ru/..."})
        await bot.get_upload_url("image")
        params = _last_call(bot).kwargs.get("params", {})
        assert params["type"] == "image"

    @pytest.mark.asyncio
    async def test_none_result_returns_empty(self):
        bot = _bot(result=None)
        result = await bot.get_upload_url("file")
        assert result == {}


class TestGetVideo:
    @pytest.mark.asyncio
    async def test_returns_result(self):
        bot = _bot(result={"url": "https://video.max.ru/...", "duration": 120})
        result = await bot.get_video(video_token="vtok_abc")
        assert result["duration"] == 120

    @pytest.mark.asyncio
    async def test_passes_token_as_param(self):
        bot = _bot(result={"url": "..."})
        await bot.get_video(video_token="vtok_xyz")
        params = _last_call(bot).kwargs.get("params", {})
        assert params["video_token"] == "vtok_xyz"


# ─── get_last_marker ─────────────────────────────────────────────────────────

class TestGetLastMarker:
    @pytest.mark.asyncio
    async def test_returns_marker(self):
        bot = _bot(result={"marker": 12345})
        result = await bot.get_last_marker()
        assert result == 12345

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        bot = _bot(result={})
        result = await bot.get_last_marker()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_none_result(self):
        bot = _bot(result=None)
        result = await bot.get_last_marker()
        assert result is None

    @pytest.mark.asyncio
    async def test_passes_limit_and_timeout(self):
        bot = _bot(result={})
        await bot.get_last_marker()
        params = _last_call(bot).kwargs.get("params", {})
        assert params["limit"] == 1
        assert params["timeout"] == 0


# ─── Media send helpers (send_photo, send_video, etc.) ───────────────────────

class TestSendMediaHelpers:
    """Test send_photo / send_document / send_audio / send_video / send_media.
    process_input_media is imported lazily inside each method, so patch at source."""

    @pytest.mark.asyncio
    async def test_send_photo_calls_send_with_media(self):
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}

        with patch("aioscam.utils.media.process_input_media", new=AsyncMock(return_value=att)) as mock_pim, \
             patch.object(bot, "_send_with_media", new=AsyncMock(return_value={"id": 1})) as mock_swm:
            result = await bot.send_photo(chat_id=1, photo="/tmp/test.jpg", caption="hi")
            mock_pim.assert_called_once()
            mock_swm.assert_called_once()
            call_kwargs = mock_swm.call_args
            assert call_kwargs.args[0] == att
            assert call_kwargs.kwargs.get("text") == "hi"

    @pytest.mark.asyncio
    async def test_send_document_calls_send_with_media(self):
        bot = Bot(token="test_token")
        att = {"type": "file", "payload": {"token": "tok"}}

        with patch("aioscam.utils.media.process_input_media", new=AsyncMock(return_value=att)), \
             patch.object(bot, "_send_with_media", new=AsyncMock(return_value={"id": 1})) as mock_swm:
            await bot.send_document(chat_id=1, document="/tmp/doc.pdf")
            mock_swm.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_audio_calls_send_with_media(self):
        bot = Bot(token="test_token")
        att = {"type": "audio", "payload": {"token": "tok"}}

        with patch("aioscam.utils.media.process_input_media", new=AsyncMock(return_value=att)), \
             patch.object(bot, "_send_with_media", new=AsyncMock(return_value={"id": 1})) as mock_swm:
            await bot.send_audio(chat_id=1, audio=b"\x00\x01")
            mock_swm.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_video_calls_send_with_media(self):
        bot = Bot(token="test_token")
        att = {"type": "video", "payload": {"token": "tok"}}

        with patch("aioscam.utils.media.process_input_media", new=AsyncMock(return_value=att)), \
             patch.object(bot, "_send_with_media", new=AsyncMock(return_value={"id": 1})) as mock_swm:
            await bot.send_video(chat_id=1, video="/tmp/vid.mp4")
            mock_swm.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_media_auto_type(self):
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}

        with patch("aioscam.utils.media.process_input_media", new=AsyncMock(return_value=att)), \
             patch.object(bot, "_send_with_media", new=AsyncMock(return_value={"id": 1})) as mock_swm:
            await bot.send_media(chat_id=1, media="/tmp/img.png")
            mock_swm.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_photo_bytes_input(self):
        bot = Bot(token="test_token")
        att = {"type": "image", "payload": {"token": "tok"}}

        with patch("aioscam.utils.media.process_input_media", new=AsyncMock(return_value=att)) as mock_pim, \
             patch.object(bot, "_send_with_media", new=AsyncMock(return_value={"id": 1})):
            await bot.send_photo(chat_id=1, photo=b"\xff\xd8\xff")
            call_arg = mock_pim.call_args.args[1]
            from aioscam.types.attachment import InputMediaBuffer
            assert isinstance(call_arg, InputMediaBuffer)
