"""
Tests for aioscam.webapp — initData validation and models.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from aioscam.webapp import (
    WebAppChat,
    WebAppDataError,
    WebAppInitData,
    WebAppUser,
    validate_init_data,
)


BOT_TOKEN = "test_bot_token_123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_init_data(
    params: dict,
    bot_token: str = BOT_TOKEN,
    corrupt_hash: bool = False,
) -> str:
    """Build a valid (or deliberately broken) initData string."""
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if corrupt_hash:
        computed_hash = "00" * 32
    return urlencode({**params, "hash": computed_hash})


def _user_json(user_id: int = 42) -> str:
    return json.dumps({"id": user_id, "first_name": "Alex"}, separators=(",", ":"))


def _fresh_params(**extra) -> dict:
    return {"auth_date": str(int(time.time())), "query_id": "qid_1", "user": _user_json(), **extra}


# ---------------------------------------------------------------------------
# WebAppUser model
# ---------------------------------------------------------------------------

class TestWebAppUser:
    def test_required_fields(self):
        u = WebAppUser(id=1, first_name="Alex")
        assert u.id == 1
        assert u.first_name == "Alex"
        assert u.last_name is None
        assert u.username is None

    def test_optional_fields(self):
        u = WebAppUser(id=2, first_name="Bob", username="bob42", language_code="ru")
        assert u.username == "bob42"
        assert u.language_code == "ru"
        assert u.photo_url is None


# ---------------------------------------------------------------------------
# WebAppChat model
# ---------------------------------------------------------------------------

class TestWebAppChat:
    def test_dialog(self):
        c = WebAppChat(id=100, type="DIALOG")
        assert c.id == 100
        assert c.type == "DIALOG"

    def test_channel(self):
        c = WebAppChat(id=200, type="CHANNEL")
        assert c.type == "CHANNEL"


# ---------------------------------------------------------------------------
# WebAppInitData model
# ---------------------------------------------------------------------------

class TestWebAppInitData:
    def test_minimal(self):
        d = WebAppInitData(auth_date=1000000, hash="abc")
        assert d.user is None
        assert d.start_param is None

    def test_full(self):
        user = WebAppUser(id=1, first_name="A")
        chat = WebAppChat(id=5, type="CHAT")
        d = WebAppInitData(
            auth_date=1000000,
            hash="abc",
            user=user,
            chat=chat,
            start_param="ref_123",
            query_id="q1",
        )
        assert d.user.id == 1
        assert d.chat.type == "CHAT"
        assert d.start_param == "ref_123"


# ---------------------------------------------------------------------------
# validate_init_data — happy path
# ---------------------------------------------------------------------------

class TestValidateInitData:
    def test_valid_minimal(self):
        raw = _make_init_data({"auth_date": str(int(time.time())), "query_id": "q1"})
        result = validate_init_data(raw, BOT_TOKEN)
        assert isinstance(result, WebAppInitData)
        assert result.query_id == "q1"
        assert result.user is None

    def test_valid_with_user(self):
        params = _fresh_params()
        raw = _make_init_data(params)
        result = validate_init_data(raw, BOT_TOKEN)
        assert result.user is not None
        assert result.user.id == 42
        assert result.user.first_name == "Alex"

    def test_valid_with_start_param(self):
        params = _fresh_params(start_param="ref_999")
        raw = _make_init_data(params)
        result = validate_init_data(raw, BOT_TOKEN)
        assert result.start_param == "ref_999"

    def test_valid_with_chat(self):
        chat_json = json.dumps({"id": 77, "type": "DIALOG"}, separators=(",", ":"))
        params = _fresh_params(chat=chat_json)
        raw = _make_init_data(params)
        result = validate_init_data(raw, BOT_TOKEN)
        assert result.chat is not None
        assert result.chat.id == 77
        assert result.chat.type == "DIALOG"

    def test_max_age_disabled(self):
        # auth_date far in the past — should still pass when max_age=0
        params = {"auth_date": "1000000", "query_id": "old"}
        raw = _make_init_data(params)
        result = validate_init_data(raw, BOT_TOKEN, max_age=0)
        assert result.auth_date == 1000000

    def test_returns_correct_hash(self):
        params = _fresh_params()
        raw = _make_init_data(params)
        result = validate_init_data(raw, BOT_TOKEN)
        # hash field preserved in the model
        assert len(result.hash) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# validate_init_data — error cases
# ---------------------------------------------------------------------------

class TestValidateInitDataErrors:
    def test_missing_hash(self):
        params = _fresh_params()
        raw = urlencode(params)  # no hash field
        with pytest.raises(WebAppDataError, match="missing the 'hash'"):
            validate_init_data(raw, BOT_TOKEN)

    def test_wrong_hash(self):
        params = _fresh_params()
        raw = _make_init_data(params, corrupt_hash=True)
        with pytest.raises(WebAppDataError, match="invalid"):
            validate_init_data(raw, BOT_TOKEN)

    def test_wrong_token(self):
        params = _fresh_params()
        raw = _make_init_data(params, bot_token="correct_token")
        with pytest.raises(WebAppDataError, match="invalid"):
            validate_init_data(raw, bot_token="wrong_token")

    def test_expired(self):
        old_ts = int(time.time()) - 100000
        params = {"auth_date": str(old_ts), "query_id": "q"}
        raw = _make_init_data(params)
        with pytest.raises(WebAppDataError, match="expired"):
            validate_init_data(raw, BOT_TOKEN, max_age=3600)

    def test_empty_string(self):
        with pytest.raises(WebAppDataError):
            validate_init_data("", BOT_TOKEN)

    def test_garbage_input(self):
        with pytest.raises(WebAppDataError):
            validate_init_data("not_init_data_at_all", BOT_TOKEN)

    def test_hash_only(self):
        # hash present but no auth_date
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, b"", hashlib.sha256).hexdigest()
        raw = f"hash={h}"
        with pytest.raises(WebAppDataError, match="auth_date"):
            validate_init_data(raw, BOT_TOKEN)
